from odoo import models


class ProductTemplate(models.Model):
    """Cargamos los campos regulatorios en product.template porque ahi es
    donde viven (md_pharma_regulatory). Esto basta: en el ProductCard de
    POS (point_of_sale/.../components/product_card), el prop "product"
    que llega al template YA ES un registro de product.template, no de
    product.product -- el grid de productos del POS en Odoo 19 se arma
    a partir de pos.productToDisplayByCateg, que agrupa por plantilla
    (confirmado porque product_screen.xml usa product.id como clave de
    quantityByProductTmplId). Por eso en el XML se leen los campos
    directo como props.product.CAMPO; no hace falta pasar por
    product_tmpl_id (ese campo relacional ni siquiera existe en
    product.template, solo en product.product).

    Segunda tanda de campos (identificacion completa para el cajero /
    popup de detalle regulatorio):
      - active_substance_ids: Many2many a md.active.substance. Como ese
        modelo se agrega a _load_pos_data_models (ver pos_session.py en
        este mismo modulo) y se le declaran campos via _load_pos_data_fields
        (ver active_substance.py), el sistema de related_models del POS
        resuelve automaticamente este M2M a instancias reales del modelo
        (no solo ids) -- mismo mecanismo que ya usa product_variant_ids o
        pos_categ_ids en el core. Por eso en XML se puede iterar
        props.product.active_substance_ids y leer .name / .color directo.
      - product_line_id: Many2one a md.product.line (md_product_lines),
        mismo mecanismo de resolucion automatica.
      - l10n_mx_talla, l10n_mx_registro_sanitario, l10n_mx_requiere_receta,
        l10n_mx_controlado, l10n_mx_dimensiones, l10n_mx_nombre_homologado,
        l10n_mx_homologacion_state: campos simples (Char/Boolean/Selection)
        para el popup de detalle regulatorio y para reforzar el buscador
        de POS (ver static/src/js/product_template_search_patch.js).
    """
    _inherit = 'product.template'

    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        for field in (
            'l10n_mx_forma_farmaceutica',
            'l10n_mx_concentracion',
            'l10n_mx_contenido_empaque',
            'l10n_mx_tipo_envase',
            'l10n_mx_talla',
            'active_substance_ids',
            'product_line_id',
            'l10n_mx_registro_sanitario',
            'l10n_mx_requiere_receta',
            'l10n_mx_controlado',
            'l10n_mx_dimensiones',
            'l10n_mx_nombre_homologado',
            'l10n_mx_homologacion_state',
        ):
            if field not in params:
                params.append(field)
        return params
