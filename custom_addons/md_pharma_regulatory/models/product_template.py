from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    active_substance_ids = fields.Many2many(
        'md.active.substance', 'md_product_active_substance_rel',
        'product_tmpl_id', 'substance_id',
        string='Sustancia(s) Activa(s)',
    )
    l10n_mx_concentracion = fields.Char(string='Concentración')
    l10n_mx_forma_farmaceutica = fields.Char(string='Forma Farmacéutica')
    l10n_mx_registro_sanitario = fields.Char(string='Registro Sanitario (COFEPRIS)')
    l10n_mx_requiere_receta = fields.Boolean(string='Requiere Receta')
    l10n_mx_controlado = fields.Boolean(
        string='Controlado',
        help='Medicamento sujeto a control especial (grupos IV-VI, Ley General de Salud).',
    )
    l10n_mx_contenido_empaque = fields.Char(
        string='Contenido del Empaque',
        help='Cantidad/presentación por empaque extraída del nombre (ej. "C/100 ML", "C/30 CAPS").',
    )
    l10n_mx_dimensiones = fields.Char(
        string='Dimensiones',
        help='Medidas físicas del producto extraídas del nombre (ej. "18X15 CM").',
    )
    l10n_mx_tipo_envase = fields.Char(
        string='Tipo de Envase',
        help='Tipo de contenedor extraído del nombre (ej. "FRASCO", "ENVASE", "TUBO", "TARRO").',
    )
    l10n_mx_talla = fields.Char(
        string='Talla/Medida',
        help='Talla o medida abreviada extraída del nombre (ej. "CH", "MED", "GDE" -> "CHICO", "MEDIANO", "GRANDE").',
    )
    l10n_mx_tiene_iva = fields.Boolean(
        string='Tiene IVA', compute='_compute_l10n_mx_iva', store=True,
        help='Indica si el producto tiene un impuesto de venta del 16% (IVA) asociado.',
    )
    l10n_mx_iva_label = fields.Char(
        string='Etiqueta IVA', compute='_compute_l10n_mx_iva', store=True,
    )
    l10n_mx_price_con_iva = fields.Float(
        string='Precio con IVA', compute='_compute_l10n_mx_iva', store=True,
    )
    l10n_mx_nombre_homologado = fields.Char(
        string='Nombre Homologado (COFEPRIS)',
        help='Nombre propuesto: código de barras + nombre original + etiquetas regulatorias '
             '(sustancia, forma, concentración, contenido, envase, talla). No reemplaza a "name" '
             'hasta que se apruebe y se promueva explícitamente (evita romper documentos ya emitidos).',
    )
    l10n_mx_homologacion_state = fields.Selection([
        ('no_elegible', 'No elegible'),
        ('propuesto', 'Propuesto'),
        ('aprobado', 'Aprobado'),
        ('aplicado', 'Aplicado'),
    ], default='no_elegible', string='Estado de Homologación', required=True)
    l10n_mx_homologacion_fase = fields.Selection([
        ('fase_1_completo', 'Fase 1: datos completos'),
        ('fase_2_parcial', 'Fase 2: datos parciales'),
        ('fase_3_sin_datos', 'Fase 3: sin datos regulatorios'),
    ], string='Fase de Homologación')

    @api.depends('list_price', 'taxes_id', 'taxes_id.amount')
    def _compute_l10n_mx_iva(self):
        for product in self:
            iva = product.taxes_id.filtered(lambda t: t.amount == 16.0)[:1]
            if iva:
                product.l10n_mx_tiene_iva = True
                product.l10n_mx_iva_label = 'IVA %s%%' % int(iva.amount)
                product.l10n_mx_price_con_iva = product.list_price * (1 + iva.amount / 100.0)
            else:
                product.l10n_mx_tiene_iva = False
                product.l10n_mx_iva_label = False
                product.l10n_mx_price_con_iva = product.list_price
