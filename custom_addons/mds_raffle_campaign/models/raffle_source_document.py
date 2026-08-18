import re
import unicodedata
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models


class RaffleSourceDocument(models.Model):
    _name = 'raffle.source.document'
    _description = 'Documento de Venta de Origen (importado de Excel histórico)'
    _order = 'doc_date, folio'

    folio = fields.Char(string='Folio', required=True, index=True)
    source_file = fields.Selection([
        ('diario', 'Diario de Ventas (POS/Físico)'),
        ('pedidos', 'Pedidos (B2B Online)'),
    ], string='Origen del archivo', required=True)
    doc_date = fields.Date(string='Fecha', required=True, index=True)
    partner_name = fields.Char(string='Cliente (texto del Excel)')
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', default=lambda s: s.env.company.currency_id)
    amount_neto = fields.Monetary(string='Importe neto', currency_field='currency_id')
    amount_tax = fields.Monetary(string='Impuesto', currency_field='currency_id')
    amount_total = fields.Monetary(string='Total', currency_field='currency_id')
    line_ids = fields.One2many('raffle.source.document.line', 'document_id', string='Líneas')
    line_count = fields.Integer(string='Cantidad de líneas', compute='_compute_line_count')

    linked_document_id = fields.Many2one(
        'raffle.source.document', string='Documento vinculado (misma venta)', index=True,
        help='DIARIO (factura) y PEDIDOS (pedido B2B) se traslapan: un pedido facturado '
             'aparece en ambos Excel con el mismo cliente y monto, 0-2 días después. Este '
             'campo enlaza la pareja para dejar claro que es LA MISMA venta contada una vez '
             'en el desglose del boleto — no dos ventas distintas ni un duplicado real.')
    is_billed_duplicate = fields.Boolean(
        string='Es la factura de un pedido ya registrado', compute='_compute_is_billed_duplicate',
        store=True,
        help='True solo para el documento de source_file=diario de un par vinculado — así '
             'se puede filtrar/marcar en las listas sin ambigüedad sobre cuál de los dos '
             'es "el duplicado".')

    _folio_source_uniq = models.Constraint(
        "UNIQUE(folio, source_file)",
        "Ya existe un documento de origen con ese folio y ese archivo — no se reimporta.",
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for doc in self:
            doc.line_count = len(doc.line_ids)

    @api.depends('linked_document_id', 'source_file')
    def _compute_is_billed_duplicate(self):
        for doc in self:
            doc.is_billed_duplicate = bool(doc.linked_document_id) and doc.source_file == 'diario'

    @staticmethod
    def _normalize_partner_name(name):
        normalized = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().upper()
        normalized = re.sub(r'S\s*\.?\s*A\s*\.?\s*(DE)?\s*C\s*\.?\s*V\s*\.?\b', 'SA DE CV', normalized)
        normalized = re.sub(r'S\s*\.?\s*DE\s*R\s*\.?\s*L\s*\.?\b', 'S DE RL', normalized)
        return re.sub(r'\s+', ' ', normalized).strip()

    @api.model
    def _link_billed_pedidos(self):
        """DIARIO y PEDIDOS se traslapan por facturación por lote (ver
        docs/plan_implementacion_quifamesa.md, bug #4 del backfill de
        histórico): un pedido B2B que se factura aparece de nuevo en el
        DIARIO con el mismo cliente y el mismo monto exacto, 0-2 días
        después. Sin este enlace, la pestaña "Documentos de Venta
        Relacionados" de un boleto puede mostrar ambos documentos como si
        fueran dos ventas independientes cuando es una sola. Empareja por
        (cliente normalizado, monto exacto) + ventana de fecha [pedido,
        pedido+2], igual que el fix original. Idempotente: solo enlaza
        documentos sin linked_document_id todavía."""
        pedidos = self.search([('source_file', '=', 'pedidos'), ('linked_document_id', '=', False)])
        diarios = self.search([('source_file', '=', 'diario'), ('linked_document_id', '=', False)])
        if not pedidos or not diarios:
            return self.browse()

        pedidos_by_key = defaultdict(list)
        for p in pedidos:
            key = (self._normalize_partner_name(p.partner_name), round(p.amount_total, 2))
            pedidos_by_key[key].append(p)

        linked = self.browse()
        for d in diarios:
            key = (self._normalize_partner_name(d.partner_name), round(d.amount_total, 2))
            candidates = pedidos_by_key.get(key)
            if not candidates:
                continue
            for p in candidates:
                if p.linked_document_id:
                    continue
                delta = (d.doc_date - p.doc_date).days
                if 0 <= delta <= 2:
                    d.linked_document_id = p.id
                    p.linked_document_id = d.id
                    linked |= d | p
                    break
        return linked


class RaffleSourceDocumentLine(models.Model):
    _name = 'raffle.source.document.line'
    _description = 'Línea de Documento de Venta de Origen'
    _order = 'id'

    document_id = fields.Many2one(
        'raffle.source.document', string='Documento', required=True, ondelete='cascade')
    product_name = fields.Char(string='Producto (texto del Excel)')
    qty = fields.Float(string='Unidades')
    currency_id = fields.Many2one(related='document_id.currency_id', string='Moneda')
    amount = fields.Monetary(string='Importe', currency_field='currency_id')
