import base64
import json
import logging
from html import escape
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from ..services.cfdi_parser import CFDIParser
from ..services.supplier_matcher import SupplierMatcher
from ..services.product_matcher import ProductMatcher
from ..services.pdf_lot_provider import get_provider
from ..services.zip_extractor import ZipExtractor
from ..services.lot_stock_resolver import LotStockResolver
from ..services.purchase_order_builder import PurchaseOrderBuilder
from ..services.known_rfcs import KnownRFC

_logger = logging.getLogger(__name__)

_MAX_FILE_MB = 15
_MAX_FILE_BYTES = _MAX_FILE_MB * 1024 * 1024


class PurchaseInvoiceImportWizard(models.TransientModel):
    _name = 'purchase.invoice.import.wizard'
    _description = 'Importar Orden de Compra desde CFDI XML'

    # --- Paso 1: carga ---
    upload_mode = fields.Selection([
        ('individual', 'Archivos individuales'),
        ('zip', 'ZIP del proveedor'),
    ], default='individual', required=True)
    xml_file = fields.Binary(string='CFDI XML del proveedor')
    xml_filename = fields.Char()
    pdf_file = fields.Binary(string='PDF de la factura (opcional, para lotes)')
    pdf_filename = fields.Char()
    pdf_parsed = fields.Boolean(readonly=True)
    lots_summary = fields.Html(readonly=True)
    zip_file = fields.Binary(string='ZIP del proveedor')
    zip_filename = fields.Char()
    zip_pair_summary = fields.Html(readonly=True)
    zip_remaining_pairs_json = fields.Text(readonly=True)
    zip_total_pairs = fields.Integer(readonly=True, default=0)
    zip_current_pair_index = fields.Integer(readonly=True, default=0)
    zip_created_po_ids_json = fields.Text(readonly=True)

    # --- Datos extraídos del CFDI (informativos) ---
    cfdi_uuid = fields.Char(string='UUID CFDI', readonly=True)
    cfdi_version = fields.Char(string='Versión CFDI', readonly=True)
    cfdi_folio = fields.Char(string='Folio', readonly=True)
    cfdi_fecha = fields.Date(string='Fecha CFDI', readonly=True)
    cfdi_subtotal = fields.Float(string='Subtotal', readonly=True, digits=(16, 2))
    cfdi_total = fields.Float(string='Total', readonly=True, digits=(16, 2))
    cfdi_moneda = fields.Char(string='Moneda', readonly=True)
    cfdi_condiciones = fields.Char(string='Condiciones de pago', readonly=True)
    emisor_rfc = fields.Char(string='RFC Emisor', readonly=True)
    emisor_nombre = fields.Char(string='Nombre Emisor', readonly=True)
    parse_warnings = fields.Text(string='Avisos del parser', readonly=True)
    has_retenciones = fields.Boolean(string='CFDI con Retenciones', readonly=True)
    ieps_warning = fields.Char(string='Aviso IEPS', readonly=True)
    pdf_provider_key = fields.Char(string='Parser PDF activo', readonly=True)

    # --- Resolución de proveedor ---
    partner_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        domain="[('cfdi_supplier_format', 'in', ['brudifarma', 'quifamesa']), ('supplier_rank', '>', 0)]",
    )
    supplier_format = fields.Selection(
        [
            ('brudifarma', 'BRUDIFARMA'),
            ('quifamesa', 'QUIFAMESA'),
        ],
        string='Formato de Proveedor',
        required=True,
        default='quifamesa',
    )
    target_company_id = fields.Many2one(
        'res.company',
        string='Compañía destino',
        required=True,
        default=lambda self: self.env.company,
    )
    partner_confidence = fields.Float(string='Confianza', readonly=True)
    partner_match_method = fields.Char(string='Método de match', readonly=True)

    # --- Líneas de conceptos ---
    line_ids = fields.One2many(
        'purchase.invoice.import.wizard.line',
        'wizard_id',
        string='Conceptos CFDI',
    )

    state = fields.Selection([
        ('upload', 'Cargar'),
        ('review', 'Revisar'),
        ('done', 'Listo'),
    ], default='upload')

    def _get_target_company(self):
        self.ensure_one()
        company = self.target_company_id or self.env.company
        if not company:
            raise UserError(_(
                "No se pudo determinar la compañía destino para la importación."
            ))
        return company

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and self.partner_id.cfdi_supplier_format:
            self.supplier_format = self.partner_id.cfdi_supplier_format

    @api.onchange('xml_filename')
    def _onchange_xml_filename(self):
        """Pre-detecta el formato del proveedor desde el nombre del archivo XML."""
        hint = self._hint_format_from_filename(self.xml_filename)
        if not hint:
            return
        # Solo aplica si el partner aún no ha fijado el formato.
        if not (self.partner_id and self.partner_id.cfdi_supplier_format):
            self.supplier_format = hint
        # Auto-asignar partner si no hay uno seleccionado y el hint permite buscarlo.
        if not self.partner_id:
            match = self.env['res.partner'].search([
                ('cfdi_supplier_format', '=', hint),
                ('supplier_rank', '>', 0),
            ], limit=1)
            if match:
                self.partner_id = match

    @api.onchange('target_company_id')
    def _onchange_target_company_id(self):
        if self.state == 'review' and self.target_company_id:
            return {
                'warning': {
                    'title': _('Compañía destino modificada'),
                    'message': _(
                        "Cambiar la compañía destino después del parseo puede invalidar "
                        "la resolución de impuestos. Verifica las tasas IVA antes de "
                        "crear la orden de compra."
                    ),
                }
            }

    @staticmethod
    def _validate_file_size(data_bytes, label):
        if data_bytes and len(data_bytes) > _MAX_FILE_BYTES:
            raise UserError(_(
                "El archivo %(label)s es demasiado grande (%(size)d KB). "
                "El límite es %(limit)d MB."
            ) % {
                'label': label,
                'size': len(data_bytes) // 1024,
                'limit': _MAX_FILE_MB,
            })

    def action_parse_xml(self):
        self.ensure_one()
        if not self.xml_file:
            raise UserError(_("Por favor carga un archivo XML CFDI."))

        # Pre-validación temprana: solo cuando el formato Quifamesa está CONFIRMADO
        # por el perfil del partner o por el nombre del archivo, nunca por el default.
        _quifamesa_confirmed = (
            (self.partner_id and self.partner_id.cfdi_supplier_format == 'quifamesa')
            or self._hint_format_from_filename(self.xml_filename) == 'quifamesa'
        )
        if _quifamesa_confirmed and not self.pdf_file:
            raise UserError(_(
                "Para QUIFAMESA el PDF de la factura es obligatorio: "
                "contiene los lotes y caducidades que no están en el XML."
            ))

        try:
            xml_bytes = base64.b64decode(self.xml_file)
            pdf_bytes = base64.b64decode(self.pdf_file) if self.pdf_file else None
        except Exception as exc:
            raise UserError(_("No se pudieron leer los archivos cargados: %s") % exc)

        self._validate_file_size(xml_bytes, 'XML')
        if pdf_bytes:
            self._validate_file_size(pdf_bytes, 'PDF')

        self.write({
            'upload_mode': 'individual',
            'zip_pair_summary': False,
            'zip_remaining_pairs_json': False,
            'zip_total_pairs': 0,
            'zip_current_pair_index': 0,
            'zip_created_po_ids_json': False,
        })
        return self._load_pair(
            xml_bytes=xml_bytes,
            xml_filename=self.xml_filename,
            pdf_bytes=pdf_bytes,
            pdf_filename=self.pdf_filename,
        )

    def action_parse_zip(self):
        self.ensure_one()
        if not self.zip_file:
            raise UserError(_("Por favor carga un archivo ZIP."))

        try:
            zip_bytes = base64.b64decode(self.zip_file)
        except Exception as exc:
            raise UserError(_("No se pudo leer el ZIP cargado: %s") % exc)

        self._validate_file_size(zip_bytes, 'ZIP')

        contents = ZipExtractor().extract(zip_bytes)
        if contents.errors and not contents.xml_files:
            raise UserError("\n".join(contents.errors))

        parser = CFDIParser()
        valid_xml_files = []
        cfdi_docs = []
        parse_errors = []
        for xml_filename, xml_bytes in contents.xml_files:
            doc = parser.parse_bytes(xml_bytes)
            if doc.parse_errors and not doc.lines:
                parse_errors.append(
                    "%s: %s" % (xml_filename, "; ".join(doc.parse_errors))
                )
                continue
            valid_xml_files.append((xml_filename, xml_bytes))
            cfdi_docs.append(doc)

        if not cfdi_docs:
            errors = contents.errors + parse_errors
            raise UserError(
                _("No se encontro ningun XML CFDI valido en el ZIP:\n%s")
                % "\n".join(errors)
            )

        contents.xml_files = valid_xml_files
        contents.errors.extend(parse_errors)
        pairs = contents.pair_xml_pdf(cfdi_docs)
        if not pairs:
            raise UserError(_("No se pudieron preparar pares XML/PDF desde el ZIP."))

        first_pair = pairs[0]
        remaining_pairs = [self._zip_pair_to_payload(pair) for pair in pairs[1:]]
        self.write({
            'upload_mode': 'zip',
            'zip_remaining_pairs_json': json.dumps(remaining_pairs),
            'zip_total_pairs': len(pairs),
            'zip_current_pair_index': 1,
            'zip_created_po_ids_json': '[]',
            'zip_pair_summary': self._build_zip_pair_summary(contents, pairs),
        })
        return self._load_pair(
            xml_bytes=first_pair.xml_bytes,
            xml_filename=first_pair.xml_filename,
            pdf_bytes=first_pair.pdf_bytes,
            pdf_filename=first_pair.pdf_filename,
            doc=first_pair.cfdi_doc,
        )

    def _load_pair(
        self,
        xml_bytes,
        xml_filename=None,
        pdf_bytes=None,
        pdf_filename=None,
        doc=None,
    ):
        self.ensure_one()
        doc = doc or CFDIParser().parse_bytes(xml_bytes)

        if doc.parse_errors and not doc.lines:
            raise UserError(
                _("Error al procesar el CFDI:\n%s") % "\n".join(doc.parse_errors)
            )

        supplier_format = self._resolve_supplier_format(doc)
        cfdi_lines = self._extract_lines_by_supplier_format(doc, supplier_format)

        company = self._get_target_company()
        matcher = SupplierMatcher(self.env)
        partner, confidence, method = matcher.find_partner(
            rfc=doc.emisor_rfc,
            nombre=doc.emisor_nombre,
            company_id=company.id,
        )

        # Si el partner fue auto-detectado por RFC y tiene un formato configurado,
        # usarlo para mantener coherencia entre partner_id y supplier_format en la vista.
        if partner and partner.cfdi_supplier_format:
            supplier_format = partner.cfdi_supplier_format

        prod_matcher = ProductMatcher(self.env)
        is_brudifarma = supplier_format == 'brudifarma'
        Product = self.env['product.product']
        addenda_lots_by_code = {}
        addenda_lots_by_compact_code = {}
        for lot in doc.addenda_lots or []:
            code = self._normalize_article_code(getattr(lot, 'codigo_sap', ''))
            if not code:
                continue
            addenda_lots_by_code.setdefault(code, []).append(lot)
            compact = self._compact_article_code(code)
            if compact:
                addenda_lots_by_compact_code.setdefault(compact, []).append(lot)

        ieps_lines_count = 0
        lines_vals = []
        for cfdi_line in cfdi_lines:
            product = False
            prod_conf = 0.0
            prod_method = 'unresolved'
            if supplier_format == 'quifamesa' and cfdi_line.no_identificacion:
                barcode = self._normalize_article_code(cfdi_line.no_identificacion)
                if barcode:
                    product = Product.search([('barcode', '=', barcode)], limit=1)
                    if product:
                        prod_conf = 0.98
                        prod_method = 'quifamesa_noidentificacion_barcode'

            if not product:
                product, prod_conf, prod_method = prod_matcher.find_product(
                    no_identificacion=cfdi_line.no_identificacion,
                    descripcion=cfdi_line.descripcion,
                    partner_id=partner.id if partner else None,
                    supplier_rfc=doc.emisor_rfc,
                )
            if not product and is_brudifarma and cfdi_line.no_identificacion:
                line_code = self._normalize_article_code(cfdi_line.no_identificacion)
                addenda_candidates = addenda_lots_by_code.get(line_code, [])
                if not addenda_candidates:
                    compact = self._compact_article_code(line_code)
                    if compact:
                        addenda_candidates = addenda_lots_by_compact_code.get(compact, [])
                for addenda_lot in addenda_candidates:
                    cbarra = self._normalize_article_code(getattr(addenda_lot, 'cbarra', ''))
                    if not cbarra:
                        continue
                    barcode_match = Product.search([('barcode', '=', cbarra)], limit=1)
                    if barcode_match:
                        product = barcode_match
                        prod_conf = 0.97
                        prod_method = 'brudifarma_addenda_cbarra'
                        break
            if cfdi_line.ieps_presente:
                ieps_lines_count += 1
            lines_vals.append({
                'wizard_id': self.id,
                'no_identificacion': cfdi_line.no_identificacion,
                'descripcion': cfdi_line.descripcion_clean or cfdi_line.descripcion,
                'product_id': product.id if product else False,
                'cantidad': cfdi_line.cantidad,
                'valor_unitario': cfdi_line.valor_unitario,
                'importe': cfdi_line.importe,
                'tasa_iva': cfdi_line.tasa_iva,
                'importe_iva': cfdi_line.importe_iva,
                'factor_iva': cfdi_line.factor_iva or '',
                'iva_presente': cfdi_line.iva_presente,
                'clave_unidad': cfdi_line.clave_unidad,
                'product_confidence': prod_conf,
                'product_match_method': prod_method,
                'needs_review': not product or prod_conf < 0.9,
            })

        ieps_warning = False
        if ieps_lines_count:
            ieps_warning = _(
                "⚠ %d línea(s) con IEPS detectadas. "
                "El IEPS no se traslada a la OC automáticamente — revisa la contabilidad."
            ) % ieps_lines_count

        self.write({
            'xml_file': base64.b64encode(xml_bytes),
            'xml_filename': xml_filename or False,
            'pdf_file': base64.b64encode(pdf_bytes) if pdf_bytes else False,
            'pdf_filename': pdf_filename or False,
            'pdf_parsed': False,
            'lots_summary': False,
            'cfdi_uuid': doc.uuid,
            'cfdi_version': doc.version or False,
            'cfdi_folio': doc.folio_completo or False,
            'cfdi_fecha': doc.fecha or False,
            'cfdi_subtotal': doc.subtotal,
            'cfdi_total': doc.total,
            'cfdi_moneda': doc.moneda,
            'cfdi_condiciones': doc.condiciones_pago,
            'emisor_rfc': doc.emisor_rfc,
            'emisor_nombre': doc.emisor_nombre,
            'partner_id': partner.id if partner else False,
            'supplier_format': supplier_format,
            'partner_confidence': confidence,
            'partner_match_method': method,
            'parse_warnings': "\n".join(doc.parse_errors) or False,
            'has_retenciones': doc.has_retenciones,
            'ieps_warning': ieps_warning,
            'state': 'review',
            'line_ids': [(5, 0, 0)] + [(0, 0, v) for v in lines_vals],
        })

        self.env.flush_all()
        self.invalidate_recordset()

        if is_brudifarma:
            self._postprocess_brudifarma(doc, cfdi_lines)
        elif supplier_format == 'quifamesa':
            self._postprocess_quifamesa()
        else:
            self._postprocess_generic(doc)

        return self._wizard_action()

    # ------------------------------------------------------------------
    # Estrategias de postproceso por proveedor
    # ------------------------------------------------------------------

    def _postprocess_brudifarma(self, doc, cfdi_lines):
        """
        BRUDIFARMA: toda la información de lotes está en el XML.
        Prioridad: Addenda/MATERIAL → Descripcion embebida. El PDF no se usa.
        """
        if doc.addenda_lots:
            try:
                self._do_populate_addenda_lots(doc.addenda_lots)
            except Exception as e:
                _logger.exception("BRUDIFARMA: error extrayendo lotes de Addenda")
                self.lots_summary = (
                    '<p class="text-danger"><b>⚠ Error extrayendo lotes de la Addenda XML:</b> '
                    f'{escape(str(e))}</p>'
                )
            return

        has_descripcion_lots = any(cl.descripcion_lot for cl in cfdi_lines)
        if has_descripcion_lots:
            try:
                self._do_populate_descripcion_lots(cfdi_lines)
            except Exception as e:
                _logger.exception("BRUDIFARMA: error extrayendo lotes de Descripcion")
                self.lots_summary = (
                    '<p class="text-danger"><b>⚠ Error extrayendo lotes de la Descripción XML:</b> '
                    f'{escape(str(e))}</p>'
                )
            return

        _logger.warning("BRUDIFARMA: XML sin Addenda ni lotes en Descripcion — ningún lote extraído")
        self.lots_summary = (
            '<p class="text-warning"><b>⚠ Sin lotes en el XML de BRUDIFARMA.</b> '
            'No se encontró Addenda/MATERIAL ni "Lote:" en la descripción de los conceptos.</p>'
        )

    def _postprocess_quifamesa(self):
        """
        QUIFAMESA: el XML solo tiene datos fiscales. El PDF es obligatorio para lotes.
        """
        if not self.pdf_file:
            # Puede llegar aquí si el formato fue detectado por RFC sin partner pre-seleccionado
            # y el usuario no cargó PDF.
            self.lots_summary = (
                '<p class="text-danger"><b>⚠ PDF obligatorio para QUIFAMESA.</b> '
                'Carga el PDF de la factura y usa el botón "Extraer lotes del PDF" '
                'para completar los lotes y caducidades.</p>'
            )
            return
        try:
            self._do_parse_pdf()
        except UserError:
            raise
        except Exception as e:
            _logger.exception("QUIFAMESA: error auto-extrayendo lotes del PDF")
            self.lots_summary = (
                '<p class="text-danger"><b>⚠ Error al extraer lotes del PDF:</b> '
                f'{escape(str(e))}</p>'
                '<p>Puedes reintentar con el botón "Extraer lotes del PDF".</p>'
            )

    def _postprocess_generic(self, doc):
        """Proveedores sin estrategia explícita: PDF si disponible, Addenda como fallback."""
        if self.pdf_file:
            try:
                self._do_parse_pdf()
            except UserError:
                raise
            except Exception as e:
                _logger.exception("Postproceso genérico: error en PDF")
                self.lots_summary = (
                    '<p class="text-danger"><b>⚠ Error auto-extrayendo lotes:</b> '
                    f'{escape(str(e))}</p>'
                    '<p>Puedes reintentar con el botón "Extraer lotes del PDF".</p>'
                )
            return

        if doc.addenda_lots:
            try:
                self._do_populate_addenda_lots(doc.addenda_lots)
            except Exception as e:
                _logger.exception("Postproceso genérico: error en Addenda")
                self.lots_summary = (
                    '<p class="text-danger"><b>⚠ Error extrayendo lotes de la Addenda XML:</b> '
                    f'{escape(str(e))}</p>'
                )

    def _resolve_supplier_format(self, doc):
        self.ensure_one()
        # 1. Perfil del partner (mayor prioridad).
        if self.partner_id and self.partner_id.cfdi_supplier_format:
            return self.partner_id.cfdi_supplier_format
        # 2. RFC del emisor en el CFDI — ambos proveedores explícitos.
        rfc = (doc.emisor_rfc or '').upper()
        if rfc == KnownRFC.BRUDIFARMA:
            return 'brudifarma'
        if rfc == KnownRFC.QUIFAMESA:
            return 'quifamesa'
        # 3. Patrón del nombre de archivo (pre-detección al momento de carga).
        hint = self._hint_format_from_filename(self.xml_filename)
        if hint:
            return hint
        # 4. Valor actual del campo (onchange previo) o default.
        current = (self.supplier_format or '').strip()
        return current if current in ('brudifarma', 'quifamesa') else 'quifamesa'

    @staticmethod
    def _hint_format_from_filename(filename):
        """
        Infiere el formato del proveedor desde el nombre del archivo XML.
        Brudifarma: archivos que empiezan con '2000_' (ej. 2000_2000201962_…).
        Quifamesa:  archivos que empiezan con 'QFM'  (ej. QFM861010BL0_Factura_…).
        Retorna 'brudifarma', 'quifamesa' o None si el patrón no es reconocido.
        """
        if not filename:
            return None
        name = filename.strip().upper()
        if name.startswith('2000_'):
            return 'brudifarma'
        if name.startswith('QFM'):
            return 'quifamesa'
        return None

    def _extract_lines_by_supplier_format(self, doc, supplier_format):
        lines = list(doc.lines or [])
        if supplier_format == 'brudifarma':
            return self._extract_brudifarma_lines(lines, doc.addenda_lots or [])
        return self._extract_quifamesa_lines(lines)

    def _extract_brudifarma_lines(self, lines, addenda_lots):
        by_code = {}
        by_barcode = {}
        for lot in addenda_lots:
            code = self._normalize_article_code(getattr(lot, 'codigo_sap', ''))
            if code:
                by_code.setdefault(code, []).append(lot)
            cbarra = self._normalize_article_code(getattr(lot, 'cbarra', ''))
            if cbarra:
                by_barcode.setdefault(cbarra, []).append(lot)

        for line in lines:
            key = self._normalize_article_code(line.no_identificacion)
            candidates = by_code.get(key) or by_barcode.get(key) or []
            if not candidates:
                continue
            addenda_lot = candidates[0]
            if addenda_lot.lote:
                line.descripcion_lot = addenda_lot.lote
            if addenda_lot.caducidad:
                line.descripcion_caducidad = addenda_lot.caducidad
            cbarra = self._normalize_article_code(getattr(addenda_lot, 'cbarra', ''))
            if cbarra:
                line.barcode_hint = cbarra
        return lines

    def _extract_quifamesa_lines(self, lines):
        for line in lines:
            barcode = self._normalize_article_code(
                line.no_identificacion or getattr(line, 'barcode_hint', '')
            )
            if not barcode:
                continue
            line.no_identificacion = barcode
            line.barcode_hint = barcode
        return lines

    # ------------------------------------------------------------------
    # Hard Stops: IVA y Lotes ("A la Mano") antes de crear la OC
    # ------------------------------------------------------------------

    _IVA_TOLERANCE_PCT = 0.01  # tolerancia de redondeo en puntos porcentuales

    def _validate_before_create(self, target_company):
        """Bloquea la creación de la OC ante discrepancias de IVA o lotes faltantes.

        Args:
            target_company: res.company destino de la OC. Se usa para acotar
                por compañía la comparación de impuestos (ver _validate_line_iva).

        Raises:
            ValidationError: consolidado con todas las líneas afectadas, si
                hay discrepancias de IVA respecto al impuesto de proveedor
                configurado en el producto, o falta un lote válido para
                productos con seguimiento por lote ('A la Mano').
        """
        self.ensure_one()
        errors = []
        for idx, line in enumerate(self.line_ids, start=1):
            product = line.product_id
            if not product:
                continue
            errors.extend(self._validate_line_iva(idx, line, target_company))
            errors.extend(self._validate_line_lot(idx, line))

        if errors:
            raise ValidationError(
                _(
                    "No se puede crear la Orden de Compra: se encontraron "
                    "discrepancias en el CFDI que requieren revisión manual.\n\n%s"
                ) % "\n".join(f"• {err}" for err in errors)
            )

    def _validate_line_iva(self, idx, line, target_company):
        """Compara la TasaOCuota del CFDI contra el IVA de compra del producto.

        Solo considera impuestos de supplier_taxes_id configurados para
        target_company (o sin compañía asignada) — igual criterio de scoping
        que TaxResolver (services/tax_resolver.py), para no comparar contra
        el impuesto de una sucursal distinta a la que se está importando.

        Excepción intencional: un CFDI que declara explícitamente 0%/Exento
        NO se bloquea aunque el producto tenga configurada una tasa distinta
        de cero — una factura puntual puede llegar legítimamente sin IVA
        (ej. venta exenta específica) y el CFDI manda sobre el default del
        producto en ese caso. Solo se bloquea cuando el CFDI trae una tasa
        NO-CERO que no coincide con ninguna tasa configurada del producto
        para esta compañía.

        Args:
            idx: número de línea (1-based) para el mensaje de error.
            line: purchase.invoice.import.wizard.line con los datos del CFDI.
            target_company: res.company destino de la OC.

        Returns:
            list[str]: mensajes de error (vacío si no hay discrepancia).
        """
        product = line.product_id
        configured_taxes = product.supplier_taxes_id.filtered(
            lambda t: t.type_tax_use == 'purchase'
            and t.amount_type == 'percent'
            and t.company_id.id in (False, target_company.id)
        )
        if not configured_taxes:
            # Sin impuesto de proveedor configurado en el producto para esta
            # compañía: nada que comparar.
            return []

        factor = (line.factor_iva or '').strip().lower()
        if factor == 'exento' or not line.iva_presente:
            received_pct = 0.0
        else:
            received_pct = round((line.tasa_iva or 0.0) * 100, 4)

        if abs(received_pct) < self._IVA_TOLERANCE_PCT:
            # CFDI explícitamente sin IVA/Exento: se permite como excepción.
            return []

        configured_pcts = configured_taxes.mapped('amount')
        if any(abs(received_pct - pct) < self._IVA_TOLERANCE_PCT for pct in configured_pcts):
            return []

        expected_str = ', '.join(f'{p:g}%' for p in configured_pcts)
        return [_(
            "Línea %(idx)d: %(name)s — Discrepancia de IVA. "
            "Esperado %(expected)s (config. producto), Recibido %(received)s (CFDI)."
        ) % {
            'idx': idx,
            'name': product.display_name,
            'expected': expected_str,
            'received': f'{received_pct:g}%',
        }]

    def _validate_line_lot(self, idx, line):
        """Exige un lote válido para productos con seguimiento por lote.

        Si el producto tiene tracking == 'lot', exige que el CFDI/PDF haya
        resuelto al menos un lote válido para la línea antes de colocarlo
        'A la Mano' (On Hand) mediante la Orden de Compra.

        Args:
            idx: número de línea (1-based) para el mensaje de error.
            line: purchase.invoice.import.wizard.line con los lotes extraídos.

        Returns:
            list[str]: mensajes de error (vacío si no aplica o ya tiene lote).
        """
        product = line.product_id
        if product.tracking != 'lot':
            return []

        if line._valid_lots():
            return []

        return [_(
            "Línea %(idx)d: %(name)s — Producto con seguimiento por Lote pero el "
            "CFDI/PDF no incluye un lote válido. No se puede colocar 'A la Mano' "
            "(On Hand) sin lote/caducidad."
        ) % {'idx': idx, 'name': product.display_name}]

    def _wizard_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _zip_pair_to_payload(self, pair):
        return {
            'xml_filename': pair.xml_filename,
            'xml_file': base64.b64encode(pair.xml_bytes).decode('ascii'),
            'pdf_filename': pair.pdf_filename,
            'pdf_file': (
                base64.b64encode(pair.pdf_bytes).decode('ascii')
                if pair.pdf_bytes else None
            ),
        }

    def _zip_payload_to_pair_args(self, payload):
        return {
            'xml_bytes': base64.b64decode(payload['xml_file']),
            'xml_filename': payload.get('xml_filename'),
            'pdf_bytes': (
                base64.b64decode(payload['pdf_file'])
                if payload.get('pdf_file') else None
            ),
            'pdf_filename': payload.get('pdf_filename'),
        }

    def _zip_remaining_pairs(self):
        if not self.zip_remaining_pairs_json:
            return []
        try:
            return json.loads(self.zip_remaining_pairs_json) or []
        except json.JSONDecodeError:
            return []

    def _zip_created_po_ids(self):
        if not self.zip_created_po_ids_json:
            return []
        try:
            return json.loads(self.zip_created_po_ids_json) or []
        except json.JSONDecodeError:
            return []

    def _build_zip_pair_summary(self, contents, pairs):
        matched = sum(1 for pair in pairs if pair.pdf_filename)
        unpaired = [pair.xml_filename for pair in pairs if not pair.pdf_filename]
        parts = [
            f"<p><b>XML detectados:</b> {len(contents.xml_files)}</p>",
            f"<p><b>PDF detectados:</b> {len(contents.pdf_files)}</p>",
            f"<p><b>Pares con PDF:</b> {matched}</p>",
        ]
        if unpaired:
            items = ''.join(f"<li>{escape(name)}</li>" for name in unpaired)
            parts.append(
                '<p class="text-warning"><b>XML sin PDF asociado:</b></p>'
                f'<ul>{items}</ul>'
            )
        if contents.errors:
            items = ''.join(f"<li>{escape(error)}</li>" for error in contents.errors)
            parts.append(f'<ul class="text-warning">{items}</ul>')
        return ''.join(parts)

    def action_create_purchase_order(self):
        self.ensure_one()
        target_company = self._get_target_company()

        if not self.partner_id:
            raise UserError(_(
                "Debes seleccionar un proveedor antes de crear la orden de compra."
            ))

        sin_producto = self.line_ids.filtered(
            lambda l: l.needs_review and not l.product_id
        )
        if sin_producto:
            raise UserError(_(
                "Hay %d línea(s) sin producto asignado. "
                "Asigna un producto o elimina la línea antes de continuar."
            ) % len(sin_producto))

        self._validate_before_create(target_company)

        po = PurchaseOrderBuilder(self.env, self, target_company).build()

        if self.upload_mode == 'zip':
            created_ids = self._zip_created_po_ids() + [po.id]
            remaining_pairs = self._zip_remaining_pairs()
            if remaining_pairs:
                next_payload = remaining_pairs[0]
                self.write({
                    'zip_created_po_ids_json': json.dumps(created_ids),
                    'zip_remaining_pairs_json': json.dumps(remaining_pairs[1:]),
                    'zip_current_pair_index': self.zip_current_pair_index + 1,
                })
                return self._load_pair(**self._zip_payload_to_pair_args(next_payload))

            self.write({
                'state': 'done',
                'zip_created_po_ids_json': json.dumps(created_ids),
                'zip_pair_summary': (
                    self.zip_pair_summary or ''
                ) + _(
                    '<p class="text-success"><b>✓ Se crearon %d orden(es) de compra.</b></p>'
                ) % len(created_ids),
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'list,form',
                'target': 'current',
                'domain': [('id', 'in', created_ids)],
            }

        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Lotes desde PDF
    # ------------------------------------------------------------------

    def action_parse_pdf(self):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_("Carga primero el PDF de la factura."))
        return self._do_parse_pdf()

    def _do_parse_pdf(self):
        self.ensure_one()
        provider_key = (
            self.partner_id.pdf_lot_provider_key
            if self.partner_id else None
        )
        if not provider_key and (self.emisor_rfc or '').upper() == KnownRFC.BRUDIFARMA:
            provider_key = 'brudifarma'
        if not provider_key and (self.emisor_rfc or '').upper() == KnownRFC.QUIFAMESA:
            provider_key = 'quifamesa'

        provider = get_provider(provider_key)
        active_key = provider.key

        try:
            pdf_bytes = base64.b64decode(self.pdf_file)
            lots_by_article = provider.parse(pdf_bytes)
        except Exception as e:
            _logger.exception("Error parseando PDF de lotes")
            raise UserError(_("No se pudo procesar el PDF: %s") % e)

        if not lots_by_article:
            sample = provider.diagnose(pdf_bytes, max_chars=1500) or "(vacío)"
            _logger.warning("PDF sin lotes parseados. Muestra:\n%s", sample)
            self.write({
                'pdf_parsed': True,
                'pdf_provider_key': active_key,
                'lots_summary': (
                    '<p class="text-danger"><b>⚠ No se detectaron lotes en el PDF.</b></p>'
                    '<p>El parser no reconoció el formato. Texto extraído (primeros 1500 chars):</p>'
                    f'<pre style="white-space:pre-wrap;font-size:11px;max-height:300px;overflow:auto;">'
                    f'{escape(sample)}</pre>'
                    '<p>Comparte este extracto para ajustar las expresiones regulares al formato del proveedor.</p>'
                ),
            })
            return self._wizard_action()

        company_id = self._get_target_company().id
        lot_resolver = LotStockResolver(self.env, company_id)

        product_ids = {line.product_id.id for line in self.line_ids if line.product_id}
        lot_names = [lv['name'] for lv_list in lots_by_article.values() for lv in lv_list if lv.get('name')]
        if product_ids and lot_names:
            lot_resolver.preload(product_ids)

        self.line_ids.mapped('lot_ids').unlink()

        total_lots = 0
        missing = 0
        discounted_lots = 0
        multi_lot_lines = 0
        lines_without_code = 0
        wizard_lot_vals = []

        for line in self.line_ids:
            key = self._normalize_article_code(line.no_identificacion)
            if not key:
                lines_without_code += 1
                continue
            lots = lots_by_article.get(key, [])
            if not lots and key:
                compact = self._compact_article_code(key)
                for k, v in lots_by_article.items():
                    if self._compact_article_code(k) == compact:
                        lots = v
                        break
            if len(lots) > 1:
                multi_lot_lines += 1
            for lot_vals in lots:
                existing = False
                if line.product_id:
                    existing = lot_resolver.find(line.product_id, lot_vals['name'])
                state = 'found' if existing else 'missing'
                if state == 'missing':
                    missing += 1
                if lot_vals.get('discount'):
                    discounted_lots += 1
                total_lots += 1
                wizard_lot_vals.append({
                    'line_id': line.id,
                    'name': lot_vals['name'],
                    'expiration_date': lot_vals['expiration_date'] or False,
                    'quantity': lot_vals['quantity'],
                    'discount': lot_vals.get('discount') or 0.0,
                    'existing_lot_id': existing.id if existing else False,
                    'state': state,
                })

        if wizard_lot_vals:
            self.env['purchase.invoice.import.wizard.lot'].create(wizard_lot_vals)

        summary_parts = [
            f"<p><b>Lotes detectados:</b> {total_lots}</p>",
            f"<p><b>A la mano en sistema:</b> {total_lots - missing}</p>",
        ]
        if missing:
            summary_parts.append(
                f'<p class="text-warning"><b>Lotes no encontrados en sistema:</b> {missing}</p>'
                '<p>Revisa lote, caducidad y cantidad antes de crear la orden de compra.</p>'
            )
        else:
            summary_parts.append('<p class="text-success"><b>✓ Todos los lotes están a la mano.</b></p>')
        if discounted_lots:
            summary_parts.append(
                f'<p class="text-warning"><b>Descuentos detectados en PDF:</b> {discounted_lots}. '
                'Revísalos manualmente antes de crear la orden de compra.</p>'
            )
        if multi_lot_lines:
            summary_parts.append(
                f'<p class="text-warning"><b>Productos con más de un lote:</b> {multi_lot_lines}. '
                'La orden de compra conservará una línea por concepto CFDI para evitar duplicados; '
                'asigna o divide lotes manualmente solo si el flujo operativo lo requiere.</p>'
            )
        if lines_without_code:
            summary_parts.append(
                f'<p class="text-warning"><b>Líneas CFDI sin NoIdentificación:</b> {lines_without_code}. '
                'No se intentó asignación automática de lotes para esas líneas.</p>'
            )

        self.write({
            'pdf_parsed': True,
            'pdf_provider_key': active_key,
            'lots_summary': ''.join(summary_parts),
        })
        return self._wizard_action()

    # ------------------------------------------------------------------
    # Lotes desde Addenda XML
    # ------------------------------------------------------------------

    def _do_populate_addenda_lots(self, addenda_lots):
        """Popula lot_ids en las líneas del wizard con los lotes de la Addenda CFDI."""
        self.ensure_one()
        company_id = self._get_target_company().id

        lots_by_code = {}
        lots_by_compact_code = {}
        lots_by_barcode = {}
        skipped_without_code = 0
        for lot in addenda_lots:
            code = self._normalize_article_code(lot.codigo_sap)
            if not code:
                skipped_without_code += 1
            else:
                lots_by_code.setdefault(code, []).append(lot)
                compact = self._compact_article_code(code)
                if compact:
                    lots_by_compact_code.setdefault(compact, []).append(lot)
            cbarra = self._normalize_article_code(getattr(lot, 'cbarra', ''))
            if cbarra:
                lots_by_barcode.setdefault(cbarra, []).append(lot)

        # Pre-carga en batch para evitar N+1
        lot_resolver = LotStockResolver(self.env, company_id)
        product_ids = {line.product_id.id for line in self.line_ids if line.product_id}
        lot_names = [lot.lote for lot in addenda_lots if lot.lote]
        if product_ids and lot_names:
            lot_resolver.preload(product_ids)

        self.line_ids.mapped('lot_ids').unlink()

        total_lots = 0
        missing = 0
        unmatched_lines = 0
        lines_without_code = 0
        duplicated_code_lines = 0
        deduplicated_addenda_rows = 0
        matched_line_keys = set()
        wizard_lot_vals = []

        for line in self.line_ids:
            key = self._normalize_article_code(line.no_identificacion)
            if not key:
                lines_without_code += 1
                continue

            line_lots = lots_by_code.get(key, [])
            match_key = ('exact', key) if line_lots else None
            if not line_lots:
                compact = self._compact_article_code(key)
                if compact:
                    line_lots = lots_by_compact_code.get(compact, [])
                    if line_lots:
                        match_key = ('compact', compact)

            if not line_lots:
                unmatched_lines += 1
                product_barcode = self._normalize_article_code(
                    line.product_id.barcode if line.product_id else ''
                )
                if product_barcode:
                    line_lots = lots_by_barcode.get(product_barcode, [])
                    if line_lots:
                        match_key = ('barcode', product_barcode)
                        unmatched_lines = max(unmatched_lines - 1, 0)
                if not line_lots:
                    continue

            if match_key in matched_line_keys:
                duplicated_code_lines += 1
                continue
            matched_line_keys.add(match_key)

            aggregated_line_lots = self._aggregate_addenda_lots(line_lots)
            deduplicated_addenda_rows += max(len(line_lots) - len(aggregated_line_lots), 0)

            for addenda_lot, lot_qty in aggregated_line_lots:
                existing = False
                if line.product_id:
                    existing = lot_resolver.find(line.product_id, addenda_lot.lote)
                state = 'found' if existing else 'missing'
                if state == 'missing':
                    missing += 1
                total_lots += 1
                wizard_lot_vals.append({
                    'line_id': line.id,
                    'name': addenda_lot.lote,
                    'expiration_date': addenda_lot.caducidad or False,
                    'quantity': lot_qty,
                    'discount': 0.0,
                    'cbarra': self._normalize_article_code(getattr(addenda_lot, 'cbarra', '')),
                    'existing_lot_id': existing.id if existing else False,
                    'state': state,
                })

        if wizard_lot_vals:
            self.env['purchase.invoice.import.wizard.lot'].create(wizard_lot_vals)

        summary_parts = [
            '<p class="text-info"><b>Lotes extraídos de Addenda XML (BRUDIFARMA)</b></p>',
            f"<p><b>Lotes en Addenda:</b> {total_lots}</p>",
            f"<p><b>A la mano en sistema:</b> {total_lots - missing}</p>",
        ]
        if skipped_without_code:
            summary_parts.append(
                f'<p class="text-warning"><b>Registros Addenda omitidos (sin CodigoSAP):</b> '
                f'{skipped_without_code}. Se omitieron para proteger integridad de datos.</p>'
            )
        if lines_without_code:
            summary_parts.append(
                f'<p class="text-warning"><b>Líneas CFDI sin NoIdentificación:</b> {lines_without_code}. '
                'No se intentó asignación automática de lotes.</p>'
            )
        if unmatched_lines:
            summary_parts.append(
                f'<p class="text-warning"><b>Líneas sin match por CodigoSAP:</b> {unmatched_lines}. '
                'Revisa la homologación de códigos proveedor/producto.</p>'
            )
        if duplicated_code_lines:
            summary_parts.append(
                f'<p class="text-warning"><b>Líneas con código repetido sin auto-distribución:</b> '
                f'{duplicated_code_lines}. Se evitó duplicar lotes automáticamente.</p>'
            )
        if deduplicated_addenda_rows:
            summary_parts.append(
                f'<p class="text-warning"><b>Filas Addenda desduplicadas:</b> '
                f'{deduplicated_addenda_rows}. Se consolidaron lotes repetidos por lote/caducidad.</p>'
            )
        if missing:
            summary_parts.append(
                f'<p class="text-warning"><b>Lotes por crear:</b> {missing}. '
                'Revisa lote y caducidad antes de confirmar la orden de compra.</p>'
            )
        else:
            summary_parts.append(
                '<p class="text-success"><b>✓ Todos los lotes ya están a la mano.</b></p>'
            )

        self.write({
            'pdf_parsed': False,
            'lots_summary': ''.join(summary_parts),
        })

    def _do_populate_descripcion_lots(self, cfdi_lines):
        """
        Popula lot_ids desde el campo Descripcion de cada concepto CFDI.
        Usado para BRUDIFARMA cuando el XML embebe 'Lote: X Fecha de caducidad: Y'
        en la descripción de cada producto. Es la fuente más fidedigna porque es
        parte del comprobante timbrado por el SAT y preserva los ceros a la izquierda.
        """
        self.ensure_one()
        company_id = self._get_target_company().id

        # Construir mapa no_identificacion → CFDILine con datos de lote
        cfdi_line_map = {
            cl.no_identificacion: cl
            for cl in cfdi_lines
            if cl.descripcion_lot
        }
        if not cfdi_line_map:
            return

        lot_resolver = LotStockResolver(self.env, company_id)
        product_ids = {line.product_id.id for line in self.line_ids if line.product_id}
        if product_ids:
            lot_resolver.preload(product_ids)

        self.line_ids.mapped('lot_ids').unlink()

        total_lots = 0
        missing = 0
        lines_without_lot = 0
        wizard_lot_vals = []

        for wiz_line in self.line_ids:
            cfdi_line = cfdi_line_map.get(wiz_line.no_identificacion)
            if not cfdi_line:
                lines_without_lot += 1
                continue

            existing = False
            if wiz_line.product_id:
                existing = lot_resolver.find(wiz_line.product_id, cfdi_line.descripcion_lot)
            state = 'found' if existing else 'missing'
            if state == 'missing':
                missing += 1
            total_lots += 1
            wizard_lot_vals.append({
                'line_id': wiz_line.id,
                'name': cfdi_line.descripcion_lot,
                'expiration_date': cfdi_line.descripcion_caducidad or False,
                'quantity': wiz_line.cantidad,
                'discount': 0.0,
                'existing_lot_id': existing.id if existing else False,
                'state': state,
            })

        if wizard_lot_vals:
            self.env['purchase.invoice.import.wizard.lot'].create(wizard_lot_vals)

        summary_parts = [
            '<p class="text-info"><b>Lotes extraídos del XML (Descripción BRUDIFARMA)</b></p>',
            f"<p><b>Lotes en XML:</b> {total_lots}</p>",
            f"<p><b>A la mano en sistema:</b> {total_lots - missing}</p>",
        ]
        if lines_without_lot:
            summary_parts.append(
                f'<p class="text-muted">Líneas sin lote en Descripción: {lines_without_lot}.</p>'
            )
        if missing:
            summary_parts.append(
                f'<p class="text-warning"><b>Lotes por crear:</b> {missing}. '
                'Revisa lote y caducidad antes de confirmar la orden de compra.</p>'
            )
        else:
            summary_parts.append(
                '<p class="text-success"><b>✓ Todos los lotes ya están a la mano.</b></p>'
            )

        self.write({
            'pdf_parsed': False,
            'lots_summary': ''.join(summary_parts),
        })

    # ------------------------------------------------------------------
    # Notificación de cambios de precio
    # ------------------------------------------------------------------

    def _snapshot_supplier_prices(self):
        """Lee los precios actuales de supplierinfo ANTES de crear la OC.

        Devuelve {product_tmpl_id: price} para todos los productos del wizard
        que ya tienen un registro de supplierinfo para el proveedor seleccionado.
        Llamar antes de build() para capturar el estado previo.
        """
        if not self.partner_id:
            return {}
        product_tmpl_ids = self.line_ids.filtered(
            lambda l: l.product_id
        ).mapped('product_id.product_tmpl_id').ids
        if not product_tmpl_ids:
            return {}
        infos = self.env['product.supplierinfo'].search([
            ('partner_id', '=', self.partner_id.id),
            ('product_tmpl_id', 'in', product_tmpl_ids),
        ])
        return {info.product_tmpl_id.id: info.price for info in infos}

    def _notify_price_changes(self, po, company, old_prices=None, lines=None):
        """Detecta cambios de precio respecto a un snapshot y genera notificaciones.

        Método compartido: lo usa tanto el flujo del parser (snapshot tomado
        antes de `button_confirm`, ver `PurchaseOrder.button_confirm`) como el
        override de edición manual de precio en `PurchaseOrderLine.write`
        (ver `models/purchase_order.py`). ``lines`` permite acotar la
        evaluación a un subconjunto de líneas (p. ej. solo la línea que el
        usuario acaba de editar) en vez de recorrer toda la orden — necesario
        porque ``old_prices`` puede no traer entradas para las líneas no
        tocadas, y sin este filtro se generarían notificaciones falsas para
        ellas (old_price ausente == 0.0 == "sin dato", no "sin cambio").
        """
        if old_prices is None:
            old_prices = {}
        if lines is None:
            lines = po.order_line

        Notification = self.env['purchase.price.notification']
        bus = self.env['bus.bus']

        managers = self.env.ref('stock.group_stock_manager').user_ids.sudo().filtered(
            lambda u: not u.share and company in u.company_ids
        )
        if not managers:
            return

        notifications_to_create = []
        bus_payloads = []

        for po_line in lines:
            product = po_line.product_id
            if not product:
                continue

            new_price = po_line.price_unit
            if not new_price:
                continue

            tmpl_id = product.product_tmpl_id.id
            old_price = old_prices.get(tmpl_id, 0.0)

            # Omitir si la diferencia es ruido de redondeo (< 0.1%) — solo si old_price existe
            if old_price and abs(new_price - old_price) / old_price < 0.001:
                continue

            currency = po.currency_id
            currency_symbol = currency.symbol if currency else '$'
            old_fmt = f"{currency_symbol} {old_price:,.2f}" if old_price else "—"
            new_fmt = f"{currency_symbol} {new_price:,.2f}"

            notifications_to_create.append({
                'product_id': product.id,
                'product_tmpl_id': tmpl_id,
                'product_name': product.display_name,
                'partner_id': po.partner_id.id,
                'partner_name': po.partner_id.display_name,
                'old_price': old_price,
                'new_price': new_price,
                'currency_id': currency.id if currency else False,
                'purchase_order_id': po.id,
                'company_id': company.id,
                'state': 'unread',
            })

            bus_payloads.append({
                'product_name': product.display_name,
                'product_tmpl_id': tmpl_id,
                'partner_name': po.partner_id.display_name,
                'old_price_fmt': old_fmt,
                'new_price_fmt': new_fmt,
                'purchase_order_name': po.name,
                'state': 'unread',
                'company_id': company.id,
            })

        if not notifications_to_create:
            return

        created = Notification.create(notifications_to_create)

        channel = f'purchase.price.notification.{company.id}'
        for rec, payload in zip(created, bus_payloads):
            payload['id'] = rec.id
            bus._sendone(channel, 'purchase_invoice_parser/price_update', payload)

            # Inyectar mensaje en el chatter del producto
            if rec.product_tmpl_id:
                old_price_val = rec.old_price
                new_price_val = rec.new_price
                old_price_str = payload.get('old_price_fmt', '—')
                new_price_str = payload.get('new_price_fmt', '—')
                chatter_partner = payload.get('partner_name', 'Proveedor desconocido')
                chatter_po = payload.get('purchase_order_name', 'OC')

                # Calcular variación porcentual
                if old_price_val and old_price_val > 0:
                    pct = (new_price_val - old_price_val) / old_price_val * 100
                    arrow = '↑' if pct >= 0 else '↓'
                    pct_sign = '+' if pct >= 0 else ''
                    pct_color = '#dc3545' if pct >= 0 else '#28a745'
                    pct_badge = Markup(
                        '<span style="font-size:11px;color:{c};">{a} {s}{p:.1f}%</span>'
                    ).format(c=pct_color, a=arrow, s=pct_sign, p=pct)
                else:
                    pct_badge = Markup('')

                new_color = '#dc3545' if new_price_val > (old_price_val or 0) else '#28a745'

                body = Markup(
                    '<div style="border-left:3px solid #0d6efd;padding:6px 10px;'
                    'border-radius:2px;margin:2px 0;font-size:13px;line-height:1.7;">'
                    '<span style="font-size:11px;color:#888;">'
                    'Actualización de costo · Factura <b>{po}</b>'
                    '</span><br>'
                    '<b>{partner}</b><br>'
                    '<span style="color:#888;text-decoration:line-through;">{old}</span>'
                    '&nbsp;<span style="color:#888;">→</span>&nbsp;'
                    '<strong style="color:{nc};">{new}</strong>'
                    '&nbsp;{pct}'
                    '</div>'
                ).format(
                    po=chatter_po,
                    partner=chatter_partner,
                    old=old_price_str,
                    new=new_price_str,
                    nc=new_color,
                    pct=pct_badge,
                )

                rec.product_tmpl_id.message_post(
                    body=body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )

    # ------------------------------------------------------------------
    # Helpers estáticos
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_article_code(value):
        return (value or '').strip()

    @staticmethod
    def _compact_article_code(value):
        normalized = (value or '').strip()
        return normalized.lstrip('0') if normalized else ''

    @staticmethod
    def _compact_lot_code(value):
        normalized = (value or '').strip()
        if not normalized:
            return ''
        if normalized.isdigit():
            compact = normalized.lstrip('0')
            return compact or '0'
        return normalized.upper()

    @staticmethod
    def _to_float(value):
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _aggregate_addenda_lots(self, addenda_lots):
        aggregated = {}
        for addenda_lot in addenda_lots:
            lot_name = (getattr(addenda_lot, 'lote', '') or '').strip()
            if not lot_name:
                continue
            key = (
                self._compact_lot_code(lot_name),
                getattr(addenda_lot, 'caducidad', None) or False,
            )
            if key in aggregated:
                aggregated[key][1] += self._to_float(
                    getattr(addenda_lot, 'cantidad', 0.0)
                )
            else:
                aggregated[key] = [
                    addenda_lot,
                    self._to_float(getattr(addenda_lot, 'cantidad', 0.0)),
                ]
        return [(values[0], values[1]) for values in aggregated.values()]


class PurchaseInvoiceImportWizardLine(models.TransientModel):
    _name = 'purchase.invoice.import.wizard.line'
    _description = 'Línea de Concepto CFDI para Importación'

    wizard_id = fields.Many2one(
        'purchase.invoice.import.wizard', required=True, ondelete='cascade'
    )
    no_identificacion = fields.Char(string='Cód. Proveedor')
    descripcion = fields.Char(string='Descripción', required=True)
    product_id = fields.Many2one(
        'product.product', string='Producto',
        domain=[('purchase_ok', '=', True)],
    )
    cantidad = fields.Float(string='Cantidad', default=1.0, digits=(16, 4))
    valor_unitario = fields.Float(string='Precio Unitario', digits=(16, 4))
    importe = fields.Float(string='Importe', readonly=True, digits=(16, 2))
    tasa_iva = fields.Float(string='Tasa IVA', digits=(16, 6))
    importe_iva = fields.Float(string='IVA', readonly=True, digits=(16, 2))
    factor_iva = fields.Char(string='Factor IVA', readonly=True)
    iva_presente = fields.Boolean(string='IVA en XML', readonly=True)
    clave_unidad = fields.Char(string='U/M SAT', readonly=True)
    product_confidence = fields.Float(string='Confianza', readonly=True)
    product_match_method = fields.Char(string='Método match', readonly=True)
    needs_review = fields.Boolean(string='Requiere revisión')
    lot_ids = fields.One2many(
        'purchase.invoice.import.wizard.lot', 'line_id', string='Lotes (PDF)'
    )
    lots_display = fields.Char(
        string='Lotes', compute='_compute_lots_display', store=False,
    )

    @api.depends(
        'lot_ids', 'lot_ids.name', 'lot_ids.quantity',
        'lot_ids.expiration_date', 'lot_ids.discount',
    )
    def _compute_lots_display(self):
        for line in self:
            parts = []
            for lot in line.lot_ids:
                exp = lot.expiration_date.strftime('%d/%m/%Y') if lot.expiration_date else '?'
                discount = f", desc. {lot.discount:g}" if lot.discount else ""
                parts.append(f"{lot.name} ({lot.quantity:g} • {exp}{discount})")
            line.lots_display = ' | '.join(parts) if parts else ''

    def _valid_lots(self):
        """Lotes del wizard con nombre asignado (listos para usarse en la OC).

        Returns:
            purchase.invoice.import.wizard.lot: subconjunto de lot_ids con
                name truthy. Único criterio compartido de "lote válido" entre
                el Hard Stop de validación y la construcción de la OC.
        """
        self.ensure_one()
        return self.lot_ids.filtered(lambda l: l.name)


class PurchaseInvoiceImportWizardLot(models.TransientModel):
    _name = 'purchase.invoice.import.wizard.lot'
    _description = 'Lote extraído del PDF de factura'

    line_id = fields.Many2one(
        'purchase.invoice.import.wizard.line',
        required=True, ondelete='cascade',
    )
    product_id = fields.Many2one(
        related='line_id.product_id', store=False, readonly=True,
    )
    name = fields.Char(string='Lote', required=True)
    expiration_date = fields.Date(string='Caducidad')
    quantity = fields.Float(string='Cantidad', digits=(16, 4))
    discount = fields.Float(string='Descuento PDF', digits=(16, 4))
    cbarra = fields.Char(string='Cód. barras (Addenda)', readonly=True)
    existing_lot_id = fields.Many2one('stock.lot', string='Lote en sistema')
    state = fields.Selection([
        ('found', 'Existente'),
        ('missing', 'Por crear'),
    ], default='missing', required=True)
