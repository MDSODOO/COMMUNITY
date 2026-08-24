"""
Wizard para cargar la demanda de una sesión de routing
a partir de Órdenes de Compra existentes en Odoo.

Complementa al routing_import_wizard.py (que importa desde Excel).
"""
import logging
from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RoutingDemandImport(models.TransientModel):
    _name = 'routing.demand.import'
    _description = 'Importar Demanda desde Órdenes de Compra'

    routing_id = fields.Many2one(
        'purchase.routing', string='Sesión de Routing',
        required=True, ondelete='cascade',
    )

    # ── Filtros de OCs fuente ─────────────────────────────────────────
    date_from = fields.Date(string='OCs desde')
    date_to = fields.Date(string='OCs hasta')
    po_state = fields.Selection([
        ('draft', 'Solo Borradores'),
        ('sent', 'Solo Enviadas al Proveedor'),
        ('draft_sent', 'Borrador y Enviadas'),
    ], string='Estado OCs', default='draft_sent', required=True)
    partner_ids = fields.Many2many(
        'res.partner',
        'routing_demand_import_partner_rel',
        'wizard_id', 'partner_id',
        string='Filtrar por Proveedor',
        domain=[('supplier_rank', '>', 0)],
        help='Dejar vacío para incluir OCs de todos los proveedores.',
    )
    consolidate_by_product = fields.Boolean(
        string='Consolidar por Producto',
        default=True,
        help=(
            'Suma las cantidades de líneas con el mismo producto '
            'y conserva el proveedor dominante por volumen.'
        ),
    )

    # ── Estadísticas de vista previa ──────────────────────────────────
    state = fields.Selection([
        ('config', 'Configurar'),
        ('preview', 'Vista Previa'),
    ], default='config')
    po_count_found = fields.Integer(string='OCs encontradas', readonly=True)
    line_count_found = fields.Integer(string='Líneas encontradas', readonly=True)
    product_count_found = fields.Integer(string='Productos únicos', readonly=True)
    preview_warnings = fields.Text(string='Advertencias', readonly=True)

    # ── Paso 1: Vista previa ──────────────────────────────────────────
    def action_preview(self):
        """Valida los filtros y muestra estadísticas antes de importar."""
        self.ensure_one()
        pos = self._get_source_pos()
        lines = pos.mapped('order_line').filtered('product_id')

        warnings = []
        lines_no_supplierinfo = lines.filtered(
            lambda l: not l.product_id.seller_ids
        )
        if lines_no_supplierinfo:
            prods = lines_no_supplierinfo.mapped('product_id.name')[:5]
            extra = f" (y {len(lines_no_supplierinfo) - 5} más)" if len(lines_no_supplierinfo) > 5 else ""
            warnings.append(
                f"⚠ {len(lines_no_supplierinfo)} líneas tienen productos sin "
                f"proveedor configurado: {', '.join(prods)}{extra}"
            )

        self.write({
            'state': 'preview',
            'po_count_found': len(pos),
            'line_count_found': len(lines),
            'product_count_found': len(lines.mapped('product_id')),
            'preview_warnings': "\n".join(warnings) if warnings else False,
        })
        return self._reopen()

    # ── Paso 2: Importar demanda ──────────────────────────────────────
    def action_import(self):
        """Importa la demanda de las OCs como líneas en la sesión de routing."""
        self.ensure_one()
        pos = self._get_source_pos()
        lines = pos.mapped('order_line').filtered('product_id')

        if not lines:
            raise UserError(_(
                'No se encontraron líneas con producto en las OCs seleccionadas.'
            ))

        routing = self.routing_id
        # Limpiar detalles y líneas existentes si el routing está en borrador/calculado
        if routing.state in ('draft', 'calculated'):
            routing.line_ids.mapped('detail_ids').unlink()
            routing.line_ids.unlink()
            if routing.state == 'calculated':
                routing.state = 'draft'

        routing_line_vals = self._build_routing_lines(lines)
        self.env['purchase.routing.line'].create(routing_line_vals)

        _logger.info(
            'Demanda importada desde OCs a routing %s: %d líneas de %d OCs',
            routing.name, len(routing_line_vals), len(pos),
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_back(self):
        self.write({'state': 'config'})
        return self._reopen()

    # ── Helpers ───────────────────────────────────────────────────────
    def _get_source_pos(self):
        """Retorna purchase.order filtradas según los parámetros del wizard."""
        states_map = {
            'draft': ['draft'],
            'sent': ['sent'],
            'draft_sent': ['draft', 'sent'],
        }
        domain = [
            ('state', 'in', states_map.get(self.po_state, ['draft', 'sent'])),
            ('company_id', '=', self.routing_id.company_id.id),
        ]
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        pos = self.env['purchase.order'].search(domain)
        if not pos:
            raise UserError(_(
                'No se encontraron Órdenes de Compra con los filtros indicados.\n'
                'Ajusta el rango de fechas o el estado de las OCs.'
            ))
        return pos

    def _build_routing_lines(self, po_lines) -> list:
        """
        Construye vals para purchase.routing.line desde líneas de OC.
        Si consolidate_by_product, agrupa por producto sumando cantidades
        y conserva el source_partner dominante por volumen.
        """
        routing_id = self.routing_id.id

        if not self.consolidate_by_product:
            return [
                {
                    'routing_id': routing_id,
                    'product_id': line.product_id.id,
                    'qty_demanded': line.product_qty,
                    'source_partner_id': line.order_id.partner_id.id,
                }
                for line in po_lines
            ]

        # Consolidar por producto
        product_data = {}
        for line in po_lines:
            pid = line.product_id.id
            qty = line.product_qty
            partner_id = line.order_id.partner_id.id

            if pid not in product_data:
                product_data[pid] = {
                    'routing_id': routing_id,
                    'product_id': pid,
                    'qty_demanded': 0.0,
                    '_partner_volumes': {},
                }
            product_data[pid]['qty_demanded'] += qty
            vols = product_data[pid]['_partner_volumes']
            vols[partner_id] = vols.get(partner_id, 0.0) + qty

        result = []
        for data in product_data.values():
            dominant_partner = max(
                data.pop('_partner_volumes').items(), key=lambda x: x[1]
            )[0]
            data['source_partner_id'] = dominant_partner
            result.append(data)

        return result

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
