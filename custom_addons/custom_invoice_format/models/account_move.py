# -*- coding: utf-8 -*-

import base64
import logging
from collections import defaultdict, deque
from urllib.parse import quote_plus

from lxml import etree

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Campo eliminado en Odoo 19 pero aún referenciado en la plantilla QWeb
    # nativa de l10n_mx_edi (report_invoice_document). Se redefine aquí como
    # campo dummy con default=False para silenciar el AttributeError sin tocar
    # el template nativo.
    l10n_mx_cfdi_to_public = fields.Boolean(
        string='CFDI al público en general',
        default=False,
        store=True,
    )

    def md_get_invoice_line_lot_values(self):
        """Map Odoo's invoice lot values back to the main invoice lines.

        POS/global invoices do not always keep sale_line_ids on account.move.line,
        but Odoo's native report still exposes the real lot table through
        _get_invoiced_lot_values(). This helper consumes those values per product
        and quantity so our custom columns can replace the native secondary table.
        """
        self.ensure_one()
        result = {line.id: [] for line in self.invoice_line_ids}
        if not hasattr(self, '_get_invoiced_lot_values'):
            return result

        lot_values = self._md_prepare_invoice_lot_values()
        lots_by_product = defaultdict(deque)
        lots_by_name = defaultdict(deque)
        for lot_value in lot_values:
            product_id = lot_value.get('product_id')
            if hasattr(product_id, 'id'):
                product_id = product_id.id
                lot_value['product_id'] = product_id
            product_name = self._md_normalize_lot_text(lot_value.get('product_name'))
            if product_id:
                lots_by_product[product_id].append(lot_value)
            elif product_name:
                lots_by_name[product_name].append(lot_value)

        for line in self.invoice_line_ids.sorted(lambda aml: (aml.sequence, aml.id)):
            if line.display_type != 'product' or not line.product_id:
                continue

            bucket = lots_by_product.get(line.product_id.id)
            if not bucket:
                product_names = {
                    self._md_normalize_lot_text(line.product_id.display_name),
                    self._md_normalize_lot_text(line.product_id.name),
                    self._md_normalize_lot_text(line.name),
                }
                bucket = next((lots_by_name[name] for name in product_names if name and lots_by_name.get(name)), deque())
            if not bucket:
                continue

            remaining_qty = abs(line.quantity or 0.0)
            while bucket and (remaining_qty > 0.0 or not result[line.id]):
                lot_value = bucket[0]
                display_value = {
                    'lot_name': lot_value.get('lot_name') or '',
                    'expiration_date': lot_value.get('expiration_date') or '',
                }
                if display_value['lot_name'] and display_value not in result[line.id]:
                    result[line.id].append(display_value)

                lot_qty = lot_value.get('quantity_float') or 0.0
                if lot_qty <= 0.0:
                    bucket.popleft()
                    break
                if remaining_qty <= 0.0 or lot_qty <= remaining_qty + 0.00001:
                    remaining_qty -= lot_qty
                    bucket.popleft()
                else:
                    lot_value['quantity_float'] = lot_qty - remaining_qty
                    remaining_qty = 0.0

        return result

    def _md_prepare_invoice_lot_values(self):
        self.ensure_one()
        try:
            raw_lot_values = self._get_invoiced_lot_values() or []
        except Exception as exc:
            _logger.debug("Could not read invoiced lot values for %s: %s", self, exc)
            raw_lot_values = []

        # Fallback para vendor bills: _get_invoiced_lot_values navega sale_line_ids
        # y no retorna datos para in_invoice/in_refund. Se navega directamente
        # purchase_line_id → move_ids → move_line_ids → lot_id.
        if not raw_lot_values:
            raw_lot_values = self._md_lot_values_from_moves()

        prepared_values = []
        StockLot = self.env['stock.lot'].sudo()
        try:
            PosPackLot = self.env['pos.pack.operation.lot'].sudo()
        except KeyError:
            PosPackLot = None
        for raw_value in raw_lot_values:
            value = dict(raw_value)
            lot = StockLot.browse()

            if value.get('lot_id'):
                lot = StockLot.browse(value['lot_id']).exists()
            elif value.get('pos_lot_id') and PosPackLot is not None:
                pos_pack_lot = PosPackLot.browse(value['pos_lot_id']).exists()
                if pos_pack_lot:
                    value['lot_name'] = value.get('lot_name') or pos_pack_lot.lot_name
                    product = pos_pack_lot.product_id
                    if product:
                        value['product_id'] = product.id
                        lot = StockLot.search([
                            ('product_id', '=', product.id),
                            ('name', '=', pos_pack_lot.lot_name),
                        ], limit=1)

            if lot:
                value['product_id'] = value.get('product_id') or lot.product_id.id
                value['product_name'] = value.get('product_name') or lot.product_id.display_name
                value['lot_name'] = value.get('lot_name') or lot.name
                value['expiration_date'] = self._md_format_lot_date(
                    value.get('expiration_date') or lot.expiration_date
                )
            else:
                value['expiration_date'] = self._md_format_lot_date(value.get('expiration_date'))

            value['quantity_float'] = self._md_lot_quantity_to_float(value.get('quantity'))
            if value.get('lot_name'):
                prepared_values.append(value)
        return prepared_values

    def _md_lot_values_from_moves(self):
        """Fallback lot extraction via stock moves when native API returns empty.

        Navigates purchase_line_id (vendor bills) and sale_line_ids (customer
        invoices) to find associated move lines with lot_id.
        """
        self.ensure_one()
        result = []
        for line in self.invoice_line_ids:
            if line.display_type != 'product' or not line.product_id:
                continue
            lots_seen = set()
            move_lines = self.env['stock.move.line'].sudo().browse()

            if getattr(line, 'purchase_line_id', False) and line.purchase_line_id:
                move_lines |= line.purchase_line_id.move_ids.move_line_ids.filtered('lot_id')

            if getattr(line, 'sale_line_ids', False) and line.sale_line_ids:
                move_lines |= line.sale_line_ids.move_ids.move_line_ids.filtered('lot_id')

            for ml in move_lines:
                lot = ml.lot_id
                if not lot or lot.id in lots_seen:
                    continue
                lots_seen.add(lot.id)
                result.append({
                    'product_id': lot.product_id.id,
                    'product_name': lot.product_id.display_name,
                    'lot_name': lot.name,
                    'expiration_date': self._md_format_lot_date(
                        getattr(lot, 'expiration_date', None)
                    ),
                    'quantity_float': abs(float(ml.quantity or ml.qty_done or 0.0)),
                })
        return result

    def _md_lot_quantity_to_float(self, quantity):
        if isinstance(quantity, (int, float)):
            return abs(float(quantity))
        if not quantity:
            return 0.0
        normalized = str(quantity).strip().replace(',', '.')
        try:
            return abs(float(normalized))
        except ValueError:
            return 0.0

    def _md_format_lot_date(self, value):
        if not value:
            return ''
        if hasattr(value, 'date'):
            value = value.date()
        date_value = fields.Date.to_date(value)
        return date_value.isoformat() if date_value else ''

    def _md_normalize_lot_text(self, value):
        return ' '.join((value or '').split()).casefold()

    def md_get_cfdi_report_values(self):
        """Return CFDI values for the printed invoice without assuming field names.

        Odoo's Mexican EDI implementation stores most SAT printable values in the
        signed XML. Vendor bills may also come from a downloaded SAT XML document,
        so the report reads both native EDI attachments and local SAT documents.
        """
        self.ensure_one()
        values = self._md_empty_cfdi_values()

        try:
            if hasattr(self, '_l10n_mx_edi_decode_cfdi'):
                decoded = self._l10n_mx_edi_decode_cfdi() or {}
                self._md_merge_decoded_cfdi_values(values, decoded)
        except Exception as exc:
            _logger.debug("Could not decode native CFDI values for %s: %s", self, exc)

        xml_bytes = self._md_get_cfdi_xml_bytes()
        if xml_bytes:
            self._md_merge_xml_cfdi_values(values, xml_bytes)

        self._md_merge_move_cfdi_values(values)
        self._md_prepare_qr_url(values)
        return values

    def md_chunk_cfdi_text(self, value, size=115):
        """Split long SAT strings so wkhtmltopdf keeps them inside the cell."""
        text = str(value or '')
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = 115
        size = max(size, 20)
        return [text[index:index + size] for index in range(0, len(text), size)] or ['—']

    def _md_empty_cfdi_values(self):
        return {
            'uuid': '',
            'version': '',
            'fecha': '',
            'fecha_timbrado': '',
            'emisor_rfc': '',
            'emisor_nombre': '',
            'emisor_regimen': '',
            'receptor_rfc': '',
            'receptor_nombre': '',
            'receptor_regimen': '',
            'uso_cfdi': '',
            'forma_pago': '',
            'metodo_pago': '',
            'no_certificado': '',
            'no_certificado_sat': '',
            'rfc_prov_certif': '',
            'sello_cfdi': '',
            'sello_sat': '',
            'cadena_original': '',
            'qr_value': '',
            'qr_url': '',
            'total': '',
        }

    def _md_merge_decoded_cfdi_values(self, values, decoded):
        mapping = {
            'uuid': ('uuid', 'cfdi_uuid'),
            'emisor_rfc': ('supplier_rfc', 'emisor_rfc'),
            'receptor_rfc': ('customer_rfc', 'receptor_rfc'),
            'sello_cfdi': ('sello', 'sello_cfd', 'sello_cfdi'),
            'sello_sat': ('sello_sat',),
            'cadena_original': ('cadena', 'cadena_original'),
            'no_certificado': ('certificate_number', 'no_certificado'),
            'no_certificado_sat': ('certificate_sat_number', 'no_certificado_sat'),
            'fecha_timbrado': ('fecha_timbrado', 'stamp_date'),
            'qr_value': ('barcode_src', 'qr_value'),
        }
        for target, candidates in mapping.items():
            for key in candidates:
                if decoded.get(key):
                    values[target] = decoded[key]
                    break

    def _md_merge_move_cfdi_values(self, values):
        if 'l10n_mx_edi_cfdi_uuid' in self._fields and self.l10n_mx_edi_cfdi_uuid:
            values['uuid'] = values['uuid'] or self.l10n_mx_edi_cfdi_uuid

        if 'l10n_mx_edi_payment_method_id' in self._fields and self.l10n_mx_edi_payment_method_id:
            payment_method = self.l10n_mx_edi_payment_method_id
            code = payment_method.code or ''
            name = payment_method.name or payment_method.display_name or ''
            values['forma_pago'] = values['forma_pago'] or ' '.join(part for part in (code, name) if part)

        if 'l10n_mx_edi_payment_policy' in self._fields and self.l10n_mx_edi_payment_policy:
            values['metodo_pago'] = values['metodo_pago'] or self.l10n_mx_edi_payment_policy

        if 'l10n_mx_edi_usage' in self._fields and self.l10n_mx_edi_usage:
            values['uso_cfdi'] = values['uso_cfdi'] or self.l10n_mx_edi_usage

    def _md_get_cfdi_xml_bytes(self):
        # Odoo 19: CFDI XML attachment lives in l10n_mx_edi.document records
        if 'l10n_mx_edi_document_ids' in self._fields:
            sent_states = ('sent', 'ginv_sent', 'payment_sent', 'partially_sent')
            cfdi_doc = self.l10n_mx_edi_document_ids.filtered(
                lambda d: d.state in sent_states
            ).sorted('id', reverse=True)[:1]
            if cfdi_doc and cfdi_doc.attachment_id:
                xml_bytes = self._md_attachment_to_bytes(cfdi_doc.attachment_id)
                if xml_bytes:
                    return xml_bytes

        # Odoo 16/17 legacy field names (fallback)
        for field_name in (
            'l10n_mx_edi_cfdi_attachment_id',
            'l10n_mx_edi_cfdi_file_id',
            'l10n_mx_edi_attachment_id',
        ):
            if field_name in self._fields:
                attachment = self[field_name]
                xml_bytes = self._md_attachment_to_bytes(attachment)
                if xml_bytes:
                    return xml_bytes

        try:
            SatXml = self.env['sat.xml.document'].sudo()
        except KeyError:
            SatXml = None
        if SatXml is not None:
            sat_doc = SatXml.search([('move_id', '=', self.id)], limit=1)
            if sat_doc and sat_doc.xml_file:
                try:
                    return base64.b64decode(sat_doc.xml_file)
                except Exception as exc:
                    _logger.debug("Could not read SAT XML document for %s: %s", self, exc)

        attachments = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            '|',
            ('mimetype', 'in', ('application/xml', 'text/xml')),
            ('name', 'ilike', '.xml'),
        ], limit=3, order='id desc')
        for attachment in attachments:
            xml_bytes = self._md_attachment_to_bytes(attachment)
            if xml_bytes:
                return xml_bytes
        return b''

    def _md_attachment_to_bytes(self, attachment):
        if not attachment:
            return b''
        try:
            if attachment.datas:
                return base64.b64decode(attachment.datas)
        except Exception as exc:
            _logger.debug("Could not decode attachment %s: %s", attachment, exc)
        return b''

    def _md_merge_xml_cfdi_values(self, values, xml_bytes):
        try:
            root = etree.fromstring(xml_bytes)
        except Exception as exc:
            _logger.debug("Could not parse CFDI XML for %s: %s", self, exc)
            return

        emisor = self._md_first_xml_node(root, "Emisor")
        receptor = self._md_first_xml_node(root, "Receptor")
        tfd = self._md_first_xml_node(root, "TimbreFiscalDigital")

        values['version'] = values['version'] or root.get('Version', '')
        values['fecha'] = values['fecha'] or root.get('Fecha', '')
        values['forma_pago'] = values['forma_pago'] or root.get('FormaPago', '')
        values['metodo_pago'] = values['metodo_pago'] or root.get('MetodoPago', '')
        values['no_certificado'] = values['no_certificado'] or root.get('NoCertificado', '')
        values['sello_cfdi'] = values['sello_cfdi'] or root.get('Sello', '')
        values['total'] = values['total'] or root.get('Total', '')

        if emisor is not None:
            values['emisor_rfc'] = values['emisor_rfc'] or emisor.get('Rfc', '')
            values['emisor_nombre'] = values['emisor_nombre'] or emisor.get('Nombre', '')
            values['emisor_regimen'] = values['emisor_regimen'] or emisor.get('RegimenFiscal', '')

        if receptor is not None:
            values['receptor_rfc'] = values['receptor_rfc'] or receptor.get('Rfc', '')
            values['receptor_nombre'] = values['receptor_nombre'] or receptor.get('Nombre', '')
            values['receptor_regimen'] = values['receptor_regimen'] or receptor.get('RegimenFiscalReceptor', '')
            values['uso_cfdi'] = values['uso_cfdi'] or receptor.get('UsoCFDI', '')

        if tfd is not None:
            values['uuid'] = values['uuid'] or (tfd.get('UUID', '') or '').upper()
            values['fecha_timbrado'] = values['fecha_timbrado'] or tfd.get('FechaTimbrado', '')
            values['rfc_prov_certif'] = values['rfc_prov_certif'] or tfd.get('RfcProvCertif', '')
            values['no_certificado_sat'] = values['no_certificado_sat'] or tfd.get('NoCertificadoSAT', '')
            values['sello_cfdi'] = values['sello_cfdi'] or tfd.get('SelloCFD', '')
            values['sello_sat'] = values['sello_sat'] or tfd.get('SelloSAT', '')
            version = tfd.get('Version', '1.1')
            if not values['cadena_original'] and values['uuid']:
                values['cadena_original'] = '||%s|%s|%s|%s|%s|%s||' % (
                    version,
                    values['uuid'],
                    values['fecha_timbrado'],
                    values['rfc_prov_certif'],
                    values['sello_cfdi'],
                    values['no_certificado_sat'],
                )

    def _md_first_xml_node(self, root, local_name):
        nodes = root.xpath("//*[local-name()=$name]", name=local_name)
        return nodes[0] if nodes else None

    def _md_prepare_qr_url(self, values):
        if not values.get('qr_value') and values.get('uuid'):
            total = values.get('total') or self.amount_total
            try:
                total = '%.6f' % float(total)
            except (TypeError, ValueError):
                total = str(total or '')
            sello = values.get('sello_cfdi') or ''
            values['qr_value'] = (
                'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx'
                '?id=%s&re=%s&rr=%s&tt=%s&fe=%s'
            ) % (
                values.get('uuid', ''),
                values.get('emisor_rfc', ''),
                values.get('receptor_rfc', ''),
                total,
                sello[-8:],
            )
        if values.get('qr_value') and not values.get('qr_url'):
            values['qr_url'] = (
                '/report/barcode/?barcode_type=QR&value=%s&width=130&height=130'
                % quote_plus(values['qr_value'])
            )
