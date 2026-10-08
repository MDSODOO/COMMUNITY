import logging
from html import escape

from odoo import fields

from .tax_resolver import TaxResolver
from .lot_stock_resolver import LotStockResolver

_logger = logging.getLogger(__name__)


class PurchaseOrderBuilder:
    """
    Crea un purchase.order a partir del estado actual del wizard de importación CFDI.
    Separa la lógica de construcción de la OC del wizard (SRP).
    """

    def __init__(self, env, wizard, company):
        self.env = env
        self.wizard = wizard
        self.company = company
        self._tax_resolver = TaxResolver(env, company)
        self._lot_resolver = LotStockResolver(env, company.id)
        self._has_lot_fields = 'lot_id' in env['purchase.order.line']._fields
        self._has_lot_expiration_field = (
            'lot_expiration_date' in env['purchase.order.line']._fields
        )
        self._attachments = env['ir.attachment']

    def build(self):
        """Construye y retorna el purchase.order creado."""
        self._preload_lots()
        po = self._create_order()
        self._rewrite_line_taxes(po)
        self._attach_documents(po)
        self._post_chatter(po)
        return po

    # ------------------------------------------------------------------
    # Privados
    # ------------------------------------------------------------------

    def _find_duplicate_in_other_companies(self):
        """
        Detecta si existe una OC con el mismo folio del mismo proveedor en otra empresa.
        """
        if not self.wizard.cfdi_folio or not self.wizard.partner_id:
            return []
        return self.env['purchase.order'].sudo().search([
            ('partner_ref', '=', self.wizard.cfdi_folio),
            ('partner_id', '=', self.wizard.partner_id.id),
            ('company_id', '!=', self.company.id),
        ])

    def _preload_lots(self):
        """Un solo query para traer todos los stock.lot relevantes a memoria."""
        product_ids = {
            line.product_id.id
            for line in self.wizard.line_ids
            if line.product_id
        }
        has_lots = any(
            lot.name
            for line in self.wizard.line_ids
            for lot in line.lot_ids
        )
        if product_ids and has_lots:
            self._lot_resolver.preload(product_ids)

    def _resolve_wizard_lot(self, wlot, product):
        """
        Obtiene o crea el stock.lot para un wizard lot.
        Si el wizard lot ya tiene existing_lot_id resuelto, lo usa directamente.
        """
        if not product or not wlot.name:
            return False
        if wlot.existing_lot_id:
            if (
                wlot.expiration_date
                and 'expiration_date' in self.env['stock.lot']._fields
                and not wlot.existing_lot_id.expiration_date
            ):
                wlot.existing_lot_id.sudo().expiration_date = wlot.expiration_date
            return wlot.existing_lot_id
        return self._lot_resolver.ensure(product, wlot.name, wlot.expiration_date)

    def _build_order_lines(self):
        default_uom = self.env.ref('uom.product_uom_unit')
        order_lines = []
        for line in self.wizard.line_ids:
            product = line.product_id
            tax = self._tax_resolver.resolve(
                line.tasa_iva,
                factor=line.factor_iva,
                iva_presente=line.iva_presente,
            )
            base_vals = {
                'product_id': product.id if product else False,
                'name': line.descripcion,
                'price_unit': line.valor_unitario,
                'product_uom_id': (
                    product.uom_id.id if product else default_uom.id
                ),
                'date_planned': self.wizard.cfdi_fecha or fields.Date.today(),
            }
            if tax:
                base_vals['tax_ids'] = [(6, 0, tax.ids)]
            elif not line.iva_presente:
                # Línea explícitamente exenta según CFDI — limpiar cualquier tax del producto
                base_vals['tax_ids'] = [(5, 0, 0)]
            # Si iva_presente=True pero tax no resuelto: omitir tax_ids para que Odoo
            # use supplier_taxes_id del producto como fallback natural.

            vals = dict(base_vals)
            vals['product_qty'] = line.cantidad

            valid_lots = line._valid_lots()
            if self._has_lot_fields and len(valid_lots) == 1 and product:
                wlot = valid_lots
                stock_lot = self._resolve_wizard_lot(wlot, product)
                if stock_lot:
                    vals['lot_id'] = stock_lot.id
                if wlot.expiration_date and self._has_lot_expiration_field:
                    vals['lot_expiration_date'] = fields.Datetime.to_datetime(
                        wlot.expiration_date
                    )
            order_lines.append((0, 0, vals))
        return order_lines

    def _create_order(self):
        wizard = self.wizard
        order_lines = self._build_order_lines()
        vals = {
            'company_id': self.company.id,
            'partner_id': wizard.partner_id.id,
            'partner_ref': wizard.cfdi_folio,
            'date_order': wizard.cfdi_fecha or fields.Date.today(),
            'order_line': order_lines,
        }
        if wizard.supplier_format == 'brudifarma':
            if wizard.cfdi_moneda and wizard.cfdi_moneda.upper() != 'MXN':
                currency = self.env['res.currency'].search(
                    [('name', '=', wizard.cfdi_moneda.upper()), ('active', 'in', [True, False])],
                    limit=1,
                )
                if currency:
                    vals['currency_id'] = currency.id
        return self.env['purchase.order'].with_company(self.company).create(vals)

    def _rewrite_line_taxes(self, po):
        """
        Odoo puede recalcular tax_ids durante create() desde supplier_taxes_id del producto.
        Reescribimos línea a línea para garantizar el IVA extraído del CFDI.
        """
        for po_line, wiz_line in zip(po.order_line, self.wizard.line_ids):
            tax = self._tax_resolver.resolve(
                wiz_line.tasa_iva,
                factor=wiz_line.factor_iva,
                iva_presente=wiz_line.iva_presente,
            )
            if tax and set(po_line.tax_ids.ids) != set(tax.ids):
                po_line.tax_ids = [(6, 0, tax.ids)]
            elif not tax and not wiz_line.iva_presente and po_line.tax_ids:
                # Solo limpiar si la línea CFDI es explícitamente exenta
                po_line.tax_ids = [(5, 0, 0)]

    def _attach_documents(self, po):
        wizard = self.wizard
        Attachment = self.env['ir.attachment']
        attachments = self.env['ir.attachment']
        if wizard.xml_file:
            attachments |= Attachment.create({
                'name': (
                    wizard.xml_filename
                    or f'CFDI_{wizard.cfdi_folio or po.name}.xml'
                ),
                'datas': wizard.xml_file,
                'res_model': 'purchase.order',
                'res_id': po.id,
                'mimetype': 'application/xml',
            })
        if wizard.pdf_file:
            attachments |= Attachment.create({
                'name': (
                    wizard.pdf_filename
                    or f'Factura_{wizard.cfdi_folio or po.name}.pdf'
                ),
                'datas': wizard.pdf_file,
                'res_model': 'purchase.order',
                'res_id': po.id,
                'mimetype': 'application/pdf',
            })
        self._attachments = attachments

    def _post_chatter(self, po):
        wizard = self.wizard
        uuid_str = escape(wizard.cfdi_uuid or '—')
        rfc_str = escape(wizard.emisor_rfc or '')
        body = f"CFDI UUID: {uuid_str}<br/>Emisor: {rfc_str}"

        if wizard.cfdi_version:
            body += f"<br/>Versión CFDI: {escape(wizard.cfdi_version)}"
        if wizard.cfdi_folio:
            body += f"<br/>Folio: {escape(wizard.cfdi_folio)}"
        if wizard.cfdi_condiciones:
            body += f"<br/>Condiciones de pago: {escape(wizard.cfdi_condiciones)}"

        # Aviso de folio duplicado en la MISMA empresa (mismo proveedor)
        if wizard.cfdi_folio and wizard.partner_id:
            dup_same = self.env['purchase.order'].search([
                ('partner_ref', '=', wizard.cfdi_folio),
                ('partner_id', '=', wizard.partner_id.id),
                ('company_id', '=', self.company.id),
                ('id', '!=', po.id),
            ], limit=1)
            if dup_same:
                body += (
                    f'<br/><span class="text-warning">'
                    f'⚠ Folio duplicado en esta empresa: ya existe la OC '
                    f'<a href="/web#model=purchase.order&amp;id={dup_same.id}">'
                    f'{escape(dup_same.name)}</a> con el mismo folio para este proveedor.'
                    f'</span>'
                )

        # Aviso de OC duplicada en OTRA empresa (con lotes compartidos)
        dup_other = self._find_duplicate_in_other_companies()
        if dup_other:
            companies_str = ', '.join([
                f'<b>{escape(dup.company_id.name)}</b> '
                f'(<a href="/web#model=purchase.order&amp;id={dup.id}">'
                f'{escape(dup.name)}</a>)'
                for dup in dup_other
            ])
            body += (
                f'<br/><span class="text-info">'
                f'ℹ️ Esta OC ya existe en otra(s) empresa(s): {companies_str}<br/>'
                f'Los lotes usados son globales y compartidos con esa(s) empresa(s). '
                f'El stock se gestiona por ubicación/almacén.'
                f'</span>'
            )

        if wizard.has_retenciones:
            body += (
                '<br/><span class="text-warning">'
                '⚠ El CFDI contiene Retenciones. Revisa la contabilidad manualmente.'
                '</span>'
            )

        if wizard.ieps_warning:
            body += f'<br/><span class="text-warning">{escape(wizard.ieps_warning)}</span>'

        for tax_warn in self._tax_resolver.warnings:
            body += f'<br/><span class="text-warning">{escape(tax_warn)}</span>'

        clean_context = dict(po.env.context)
        clean_context.pop('force_company', None)

        po.with_context(clean_context).message_post(
            body=body,
            attachment_ids=self._attachments.ids,
        )
