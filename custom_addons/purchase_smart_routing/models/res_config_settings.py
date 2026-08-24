from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    routing_threshold_percent = fields.Float(
        string='Umbral de precio para Routing (%)',
        default=6.0,
        digits=(5, 2),
        config_parameter='purchase_smart_routing.threshold_percent',
        help=(
            'Diferencia mínima de precio (%) para reasignar un producto a otro proveedor.\n'
            'Si la diferencia es menor, se respeta el proveedor de la OC original.\n'
            'Se usa como valor por defecto al crear nuevas sesiones de routing.'
        ),
    )
    routing_po_initial_state = fields.Selection([
        ('draft', 'Borrador (confirmar manualmente)'),
        ('purchase', 'Confirmar automáticamente al generar'),
    ], string='Estado inicial de OCs generadas por Routing',
        default='draft',
        config_parameter='purchase_smart_routing.po_initial_state',
    )
