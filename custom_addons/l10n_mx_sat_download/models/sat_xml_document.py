# -*- coding: utf-8 -*-
"""
Modelo intermedio: sat.xml.document

Almacena los XML descargados del SAT antes de decidir si:
- Se crea una nueva factura de proveedor (account.move)
- Se concilia con una factura existente
- Se descarta por duplicado o irrelevante
"""

import base64
import logging
import re
from datetime import datetime

from lxml import etree

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

# Namespace del CFDI 4.0 (vigente)
CFDI_NS = {
    "cfdi": "http://www.sat.gob.mx/cfd/4",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
}


class SatXmlDocument(models.Model):
    _name = "sat.xml.document"
    _description = "Documento XML descargado del SAT"
    _order = "cfdi_date desc, id desc"
    _inherit = ["mail.thread"]
    _rec_name = "cfdi_uuid"

    # =========================================================================
    # Campos
    # =========================================================================
    download_request_id = fields.Many2one(
        "sat.download.request",
        string="Solicitud de Descarga",
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    # --- Archivo XML ---
    xml_file = fields.Binary(
        string="Archivo XML",
        attachment=True,
        required=True,
    )
    xml_filename = fields.Char(
        string="Nombre del Archivo",
    )

    # --- Estado de procesamiento ---
    state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("matched", "Conciliado"),
            ("created", "Factura Creada"),
            ("ignored", "Ignorado"),
            ("error", "Error"),
        ],
        string="Estado",
        default="pending",
        tracking=True,
        index=True,
    )
    processing_notes = fields.Text(
        string="Notas de Procesamiento",
    )

    # --- Datos extraídos del CFDI ---
    cfdi_uuid = fields.Char(
        string="UUID (Folio Fiscal)",
        index=True,
        copy=False,
    )
    cfdi_type = fields.Selection(
        selection=[
            ("I", "Ingreso"),
            ("E", "Egreso"),
            ("T", "Traslado"),
            ("N", "Nómina"),
            ("P", "Pago"),
        ],
        string="Tipo de Comprobante",
    )
    cfdi_date = fields.Datetime(
        string="Fecha Emisión",
    )
    cfdi_stamp_date = fields.Datetime(
        string="Fecha Timbrado",
    )
    cfdi_total = fields.Float(
        string="Total",
        digits=(16, 2),
    )
    cfdi_subtotal = fields.Float(
        string="Subtotal",
        digits=(16, 2),
    )
    cfdi_currency = fields.Char(
        string="Moneda",
    )

    # --- Datos del emisor ---
    emisor_rfc = fields.Char(
        string="RFC Emisor",
        index=True,
    )
    emisor_name = fields.Char(
        string="Nombre Emisor",
    )
    emisor_regimen = fields.Char(
        string="Régimen Fiscal Emisor",
    )

    # --- Datos del receptor ---
    receptor_rfc = fields.Char(
        string="RFC Receptor",
        index=True,
    )
    receptor_name = fields.Char(
        string="Nombre Receptor",
    )

    # --- Relación con account.move ---
    move_id = fields.Many2one(
        "account.move",
        string="Factura Vinculada",
        ondelete="set null",
        copy=False,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contacto",
        compute="_compute_partner_id",
        store=True,
    )

    # --- Duplicados ---
    is_duplicate = fields.Boolean(
        string="Duplicado",
        compute="_compute_is_duplicate",
        store=True,
    )

    # =========================================================================
    # SQL Constraints
    # =========================================================================
    _uuid_company_uniq = models.Constraint(
        "UNIQUE(cfdi_uuid, company_id)",
        "Ya existe un XML con este UUID para esta empresa.",
    )

    # =========================================================================
    # Compute
    # =========================================================================
    @api.depends("emisor_rfc", "receptor_rfc", "company_id")
    def _compute_partner_id(self):
        """Busca el contacto correspondiente al RFC del proveedor/cliente."""
        rfcs = set()
        for doc in self:
            rfc = doc.emisor_rfc
            if doc.company_id.vat and doc.emisor_rfc == doc.company_id.vat:
                rfc = doc.receptor_rfc
            if rfc:
                rfcs.add(rfc)

        partners = self.env["res.partner"].search([("vat", "in", list(rfcs))])
        partner_by_rfc = {}
        for partner in partners:
            partner_by_rfc.setdefault(partner.vat, partner)

        for doc in self:
            rfc = doc.emisor_rfc
            # Si nosotros somos el emisor, el partner es el receptor.
            if doc.company_id.vat and doc.emisor_rfc == doc.company_id.vat:
                rfc = doc.receptor_rfc
            doc.partner_id = partner_by_rfc.get(rfc, False)

    @api.depends("cfdi_uuid", "company_id")
    def _compute_is_duplicate(self):
        uuids = list({doc.cfdi_uuid for doc in self if doc.cfdi_uuid})
        company_ids = list({doc.company_id.id for doc in self if doc.company_id})

        existing_by_key = {}
        if uuids and company_ids:
            existing = self.search(
                [
                    ("cfdi_uuid", "in", uuids),
                    ("company_id", "in", company_ids),
                ]
            )
            for record in existing:
                key = (record.cfdi_uuid, record.company_id.id)
                existing_by_key.setdefault(key, set()).add(record.id)

        current_count_by_key = {}
        for doc in self:
            if doc.cfdi_uuid and doc.company_id:
                key = (doc.cfdi_uuid, doc.company_id.id)
                current_count_by_key[key] = current_count_by_key.get(key, 0) + 1

        for doc in self:
            if not doc.cfdi_uuid:
                doc.is_duplicate = False
                continue

            key = (doc.cfdi_uuid, doc.company_id.id)
            existing_ids = set(existing_by_key.get(key, set()))
            if isinstance(doc.id, int):
                existing_ids.discard(doc.id)
            doc.is_duplicate = bool(existing_ids) or current_count_by_key.get(key, 0) > 1

    # =========================================================================
    # Método de creación desde XML raw
    # =========================================================================
    @api.model
    def _create_from_xml(
        self,
        xml_content: bytes,
        filename: str,
        download_request_id: int,
        company_id: int,
    ):
        """
        Parsea un XML de CFDI y crea el registro sat.xml.document.

        Args:
            xml_content: bytes del archivo XML.
            filename: nombre del archivo.
            download_request_id: ID de la solicitud de descarga.
            company_id: ID de la empresa.

        Returns:
            Recordset del documento creado.
        """
        vals = {
            "xml_file": base64.b64encode(xml_content),
            "xml_filename": filename,
            "download_request_id": download_request_id,
            "company_id": company_id,
        }

        try:
            root = etree.fromstring(xml_content)

            # Detectar versión del CFDI
            version = root.get("Version", root.get("version", ""))
            ns = (
                CFDI_NS
                if version == "4.0"
                else {
                    "cfdi": "http://www.sat.gob.mx/cfd/3",
                    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
                }
            )

            # --- Datos del comprobante ---
            vals["cfdi_type"] = root.get("TipoDeComprobante", "")
            vals["cfdi_total"] = float(root.get("Total", 0))
            vals["cfdi_subtotal"] = float(root.get("SubTotal", 0))
            vals["cfdi_currency"] = root.get("Moneda", "")

            fecha_str = root.get("Fecha", "")
            if fecha_str:
                vals["cfdi_date"] = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))

            # --- Emisor ---
            emisor = root.find("cfdi:Emisor", ns)
            if emisor is not None:
                vals["emisor_rfc"] = emisor.get("Rfc", "")
                vals["emisor_name"] = emisor.get("Nombre", "")
                vals["emisor_regimen"] = emisor.get("RegimenFiscal", "")

            # --- Receptor ---
            receptor = root.find("cfdi:Receptor", ns)
            if receptor is not None:
                vals["receptor_rfc"] = receptor.get("Rfc", "")
                vals["receptor_name"] = receptor.get("Nombre", "")

            # --- TimbreFiscalDigital (UUID) ---
            complemento = root.find("cfdi:Complemento", ns)
            if complemento is not None:
                tfd = complemento.find("tfd:TimbreFiscalDigital", ns)
                if tfd is not None:
                    vals["cfdi_uuid"] = tfd.get("UUID", "").upper()
                    fecha_timbrado = tfd.get("FechaTimbrado", "")
                    if fecha_timbrado:
                        vals["cfdi_stamp_date"] = datetime.fromisoformat(
                            fecha_timbrado.replace("Z", "+00:00")
                        )

        except etree.XMLSyntaxError as e:
            _logger.warning("XML malformado (%s): %s", filename, e)
            vals["state"] = "error"
            vals["processing_notes"] = f"Error de sintaxis XML: {e}"
        except Exception as e:
            _logger.warning("Error parseando %s: %s", filename, e)
            vals["state"] = "error"
            vals["processing_notes"] = f"Error al parsear: {e}"

        # Verificar duplicados antes de crear
        if vals.get("cfdi_uuid"):
            existing = self.search(
                [
                    ("cfdi_uuid", "=", vals["cfdi_uuid"]),
                    ("company_id", "=", company_id),
                ],
                limit=1,
            )
            if existing:
                _logger.info(
                    "UUID duplicado %s, omitiendo.",
                    vals["cfdi_uuid"],
                )
                return existing

        return self.create(vals)

    # =========================================================================
    # Acciones
    # =========================================================================
    def action_match_invoice(self):
        """Intenta conciliar el XML con una factura existente por UUID."""
        self.ensure_one()
        if not self.cfdi_uuid:
            raise UserError(_("Este documento no tiene UUID."))

        uuid_field = self._first_existing_move_field("l10n_mx_edi_cfdi_uuid")
        move = self.env["account.move"].search(
            [
                (uuid_field or "ref", "=", self.cfdi_uuid),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        if move:
            self.write(
                {
                    "state": "matched",
                    "move_id": move.id,
                    "processing_notes": _(
                        "Conciliado con factura %(move)s",
                        move=move.name,
                    ),
                }
            )
        else:
            self.write(
                {
                    "processing_notes": _(
                        "No se encontró factura con UUID %(uuid)s",
                        uuid=self.cfdi_uuid,
                    ),
                }
            )

    def action_create_invoice(self):
        """
        Crea una factura de proveedor (account.move) a partir del XML,
        incluyendo líneas de concepto con sus impuestos mapeados.

        Flujo:
        1. Parsea el XML completo con cfdi_parser.
        2. Determina el tipo de factura (in_invoice / in_refund).
        3. Construye las líneas con Command.create().
        4. Intenta mapear los impuestos SAT a impuestos de Odoo.
        5. Adjunta el XML original al account.move.
        """
        self.ensure_one()
        if self.state not in ("pending", "error"):
            raise UserError(_("Solo se pueden crear facturas desde documentos pendientes."))
        if not self.partner_id:
            raise UserError(
                _(
                    "No se encontró un contacto con RFC %(rfc)s. "
                    "Créelo primero antes de generar la factura.",
                    rfc=self.emisor_rfc,
                )
            )

        # Parsear el XML completo
        from ..lib.cfdi_parser import parse_cfdi

        xml_bytes = base64.b64decode(self.xml_file)
        cfdi = parse_cfdi(xml_bytes)

        # Determinar tipo de movimiento
        move_type = "in_invoice"
        if cfdi.tipo_comprobante == "E":
            move_type = "in_refund"

        # Construir líneas de factura
        invoice_lines = []
        notes = []
        for idx, concepto in enumerate(cfdi.conceptos, 1):
            line_vals = {
                "name": concepto.descripcion or f"Concepto {idx}",
                "quantity": concepto.cantidad,
                "price_unit": concepto.valor_unitario,
                "discount": self._compute_discount_percent(
                    concepto.descuento,
                    concepto.importe,
                ),
            }

            # Mapear impuestos
            tax_ids = []
            for tax in concepto.taxes:
                odoo_tax, tax_note = self._match_cfdi_tax(tax)
                if odoo_tax:
                    tax_ids.append(odoo_tax.id)
                if tax_note:
                    notes.append(
                        _(
                            "Línea %(idx)d: %(note)s",
                            idx=idx,
                            note=tax_note,
                        )
                    )

            if tax_ids:
                line_vals["tax_ids"] = [Command.set(tax_ids)]

            invoice_lines.append(Command.create(line_vals))

        # Si no hay conceptos (ej: complemento de pagos), crear línea genérica
        if not invoice_lines and cfdi.tipo_comprobante != "P":
            invoice_lines.append(
                Command.create(
                    {
                        "name": _("Importe total del CFDI"),
                        "quantity": 1,
                        "price_unit": cfdi.total,
                    }
                )
            )

        # Construir vals del move
        move_vals = {
            "move_type": move_type,
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "invoice_date": cfdi.fecha.date() if cfdi.fecha else False,
            "currency_id": self._get_currency_id(),
            "ref": cfdi.timbre.uuid if cfdi.timbre else self.cfdi_uuid,
            "invoice_line_ids": invoice_lines,
            "narration": self._build_narration(cfdi, notes),
        }

        # l10n_mx_edi es opcional: si está instalado, enriquecer el move con
        # su UUID y método de pago nativos; si no, 'ref' ya guarda el UUID.
        uuid_field = self._first_existing_move_field("l10n_mx_edi_cfdi_uuid")
        if uuid_field:
            move_vals[uuid_field] = cfdi.timbre.uuid if cfdi.timbre else self.cfdi_uuid

        if cfdi.metodo_pago and "l10n_mx_edi.payment.method" in self.env:
            payment_method = self.env["l10n_mx_edi.payment.method"].search(
                [("code", "=", cfdi.metodo_pago)],
                limit=1,
            )
            if payment_method:
                move_vals["l10n_mx_edi_payment_method_id"] = payment_method.id

        move = self.env["account.move"].create(move_vals)

        # Adjuntar el XML al move como attachment
        self.env["ir.attachment"].create(
            {
                "name": self.xml_filename or f"{self.cfdi_uuid}.xml",
                "type": "binary",
                "datas": self.xml_file,
                "res_model": "account.move",
                "res_id": move.id,
                "mimetype": "application/xml",
            }
        )

        self.write(
            {
                "state": "created",
                "move_id": move.id,
                "processing_notes": _(
                    "Factura %(move)s creada con %(lines)d líneas.",
                    move=move.name,
                    lines=len(cfdi.conceptos),
                )
                + ("\n" + "\n".join(notes) if notes else ""),
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
        }

    def _find_matching_tax(self, cfdi_tax) -> "AccountTax | None":
        tax, _note = self._match_cfdi_tax(cfdi_tax)
        return tax or None

    def _match_cfdi_tax(self, cfdi_tax):
        """
        Busca un impuesto de compra usando clave SAT, tipo factor, tasa y empresa.

        Devuelve `(tax, note)`, donde `note` documenta asignaciones por fallback
        o ausencia de configuracion suficiente.
        """
        Tax = self.env["account.tax"].with_company(self.company_id)
        tax_amount, amount_type = self._get_cfdi_tax_amount(cfdi_tax)
        base_domain = [
            ("company_id", "=", self.company_id.id),
            ("type_tax_use", "=", "purchase"),
            ("amount_type", "=", amount_type),
        ]

        sat_tax_field = self._first_existing_tax_field(
            "l10n_mx_tax_type",
            "l10n_mx_edi_tax_type",
        )
        factor_field = self._first_existing_tax_field(
            "l10n_mx_factor_type",
            "l10n_mx_edi_factor_type",
        )

        exact_domain = list(base_domain)
        if sat_tax_field and cfdi_tax.impuesto:
            exact_domain.append((sat_tax_field, "=", cfdi_tax.impuesto))
        if factor_field and cfdi_tax.tipo_factor:
            exact_domain.append((factor_field, "=", cfdi_tax.tipo_factor))

        if len(exact_domain) > len(base_domain):
            exact_tax = self._search_tax_by_amount(Tax, exact_domain, tax_amount)
            if exact_tax:
                return exact_tax, False

        fallback_tax = self._search_tax_by_amount(Tax, base_domain, tax_amount)
        if not fallback_tax:
            return Tax.browse(), _(
                "No se encontro impuesto Odoo para %(type)s %(name)s " "%(factor)s %(rate)s.",
                type=cfdi_tax.tax_type,
                name=cfdi_tax.impuesto_name,
                factor=cfdi_tax.tipo_factor,
                rate=self._format_cfdi_tax_rate(cfdi_tax),
            )

        return fallback_tax, _(
            "Impuesto %(name)s %(factor)s %(rate)s asignado por tasa; "
            "configure clave SAT y tipo factor en el impuesto Odoo para "
            "evitar ambiguedad.",
            name=cfdi_tax.impuesto_name,
            factor=cfdi_tax.tipo_factor,
            rate=self._format_cfdi_tax_rate(cfdi_tax),
        )

    def _search_tax_by_amount(self, Tax, domain, amount):
        candidates = Tax.search(domain, order="sequence, id")
        candidates = candidates.filtered(
            lambda tax: float_compare(
                tax.amount,
                amount,
                precision_digits=6,
            )
            == 0
        )
        if len(candidates) > 1:
            _logger.warning(
                "SAT XML tax match returned multiple candidates: %s",
                candidates.ids,
            )
        return candidates[:1]

    def _first_existing_tax_field(self, *field_names):
        tax_fields = self.env["account.tax"]._fields
        for field_name in field_names:
            if field_name in tax_fields:
                return field_name
        return False

    def _first_existing_move_field(self, *field_names):
        move_fields = self.env["account.move"]._fields
        for field_name in field_names:
            if field_name in move_fields:
                return field_name
        return False

    @staticmethod
    def _get_cfdi_tax_amount(cfdi_tax):
        if cfdi_tax.tipo_factor == "Exento":
            return 0.0, "percent"

        amount_type = "fixed" if cfdi_tax.tipo_factor == "Cuota" else "percent"
        amount = (
            cfdi_tax.tasa_o_cuota
            if amount_type == "fixed"
            else round(cfdi_tax.tasa_o_cuota * 100, 6)
        )
        if cfdi_tax.tax_type == "retencion":
            amount = -abs(amount)
        return amount, amount_type

    @staticmethod
    def _format_cfdi_tax_rate(cfdi_tax):
        if cfdi_tax.tipo_factor == "Cuota":
            return str(cfdi_tax.tasa_o_cuota)
        if cfdi_tax.tipo_factor == "Exento":
            return "0%"
        return f"{round(cfdi_tax.tasa_o_cuota * 100, 4)}%"

    @staticmethod
    def _compute_discount_percent(
        descuento: float,
        importe: float,
    ) -> float:
        """Calcula el porcentaje de descuento a partir de montos absolutos."""
        if not importe or not descuento:
            return 0.0
        return round((descuento / importe) * 100, 2)

    def _build_narration(self, cfdi, notes: list) -> str:
        """Construye la nota interna de la factura."""
        parts = [
            _("Creada automáticamente desde descarga masiva SAT."),
            _("UUID: %(uuid)s", uuid=cfdi.timbre.uuid if cfdi.timbre else "N/A"),
        ]
        if cfdi.emisor:
            parts.append(
                _(
                    "Emisor: %(name)s (%(rfc)s) — Régimen: %(regimen)s",
                    name=cfdi.emisor.nombre,
                    rfc=cfdi.emisor.rfc,
                    regimen=cfdi.emisor.regimen_fiscal,
                )
            )
        if cfdi.metodo_pago:
            parts.append(
                _(
                    "Método de pago: %(mp)s — Forma de pago: %(fp)s",
                    mp=cfdi.metodo_pago,
                    fp=cfdi.forma_pago,
                )
            )
        if cfdi.condiciones_pago:
            parts.append(
                _(
                    "Condiciones: %(cond)s",
                    cond=cfdi.condiciones_pago,
                )
            )
        if notes:
            parts.append("")
            parts.append(_("⚠ Advertencias:"))
            parts.extend(notes)

        return "\n".join(parts)

    def action_view_invoice(self):
        """Abre la factura vinculada."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
        }

    def action_ignore(self):
        """Marca el documento como ignorado."""
        self.write({"state": "ignored"})

    def action_reset_pending(self):
        """Regresa a estado pendiente."""
        self.write(
            {
                "state": "pending",
                "processing_notes": False,
            }
        )

    def action_batch_match(self):
        """Concilia en lote todos los documentos pendientes seleccionados."""
        pending = self.filtered(lambda d: d.state == "pending" and d.cfdi_uuid)
        for doc in pending:
            try:
                doc.action_match_invoice()
            except Exception as e:
                _logger.warning("Error conciliando %s: %s", doc.cfdi_uuid, e)
                continue

    # =========================================================================
    # Helpers
    # =========================================================================
    def _get_currency_id(self):
        """Obtiene el ID de la moneda a partir del código ISO del CFDI."""
        if not self.cfdi_currency:
            return self.company_id.currency_id.id

        currency = self.env["res.currency"].search(
            [("name", "=", self.cfdi_currency)],
            limit=1,
        )
        return currency.id if currency else self.company_id.currency_id.id
