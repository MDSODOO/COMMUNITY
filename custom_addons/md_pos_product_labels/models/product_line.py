from odoo import api, models


class MdProductLine(models.Model):
    """Habilita md.product.line como modelo cargable al POS (mixin
    pos.load.mixin) para que el M2O product_line_id en product.template se
    resuelva del lado del cliente a una instancia real (con .name), en vez
    de solo un id. Ver pos_session.py para el registro en
    _load_pos_data_models.

    No se muestra como badge permanente en la card (decision de UX: la
    marca/linea comercial rara vez es lo que distingue rapido dos
    presentaciones para el cajero, y agregar un badge mas satura la card).
    Se muestra en el popup de detalle regulatorio (ver
    regulatory_detail_popup.xml) y se indexa en el buscador de POS (ver
    product_template_search_patch.js).
    """
    _name = 'md.product.line'
    _inherit = ['md.product.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name']
