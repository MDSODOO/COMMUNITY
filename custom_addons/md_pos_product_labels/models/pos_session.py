from odoo import models


class PosSession(models.Model):
    """Agrega md.active.substance y md.product.line a la lista de modelos
    que el POS descarga al arrancar sesion. Sin esto, aunque
    active_substance_ids/product_line_id viajen como ids en
    product.template, el cliente no tendria los registros relacionados
    (name, color) para resolverlos -- ver related_models/model_classes.js
    en el core: un M2M/M2O solo se resuelve a instancias reales si el
    modelo relacionado tambien esta en _load_pos_data_models.
    """
    _inherit = 'pos.session'

    def _load_pos_data_models(self, config):
        res = super()._load_pos_data_models(config)
        for model in ('md.active.substance', 'md.product.line'):
            if model not in res:
                res.append(model)
        return res
