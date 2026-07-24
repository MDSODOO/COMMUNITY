from odoo import api, models


class MdActiveSubstance(models.Model):
    """Habilita md.active.substance como modelo cargable al POS (mixin
    pos.load.mixin) para que el M2M active_substance_ids en product.template
    se resuelva del lado del cliente a instancias reales (con .name y
    .color), en vez de solo una lista de ids. Ver pos_session.py para el
    registro en _load_pos_data_models.

    Nota: el campo "color" de este modelo DEBE ser distinto de 0 para que
    el tag se vea (mismo bug que ya se encontro y corrigio en el kanban de
    Inventario, ver md_pharma_regulatory/views/product_visual_views.xml).
    """
    _name = 'md.active.substance'
    _inherit = ['md.active.substance', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'color']
