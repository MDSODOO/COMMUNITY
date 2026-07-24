from odoo import fields, models


class MdNameAbbreviation(models.Model):
    _name = 'md.name.abbreviation'
    _description = 'Diccionario de abreviaturas en nombres de producto (español MX)'
    _order = 'category, abbreviation'

    CATEGORY_SELECTION = [
        ('talla', 'Talla/Medida'),
        ('material_envase', 'Material de Envase'),
        ('via_administracion', 'Vía de Administración/Uso'),
        ('unidad', 'Unidad de Medida'),
    ]

    category = fields.Selection(CATEGORY_SELECTION, required=True, index=True, string='Categoría')
    abbreviation = fields.Char(
        required=True, index=True, string='Abreviatura',
        help='Forma corta tal como aparece en el nombre del producto (ej. "CH", "MD", "PLAST").',
    )
    full_name = fields.Char(
        required=True, string='Forma Completa',
        help='Forma completa/canónica a la que se expande (ej. "CHICO", "MEDIANO", "PLASTICO"). '
             'Para vías de administración ya "completas" (ORAL, NASAL...), es igual a la abreviatura: '
             'sirven como lista blanca de términos reconocidos, no como texto a recortar del nombre.',
    )
    active = fields.Boolean(default=True, string='Activo')
    notes = fields.Char(string='Notas')

    _abbreviation_category_uniq = models.Constraint(
        'UNIQUE(category, abbreviation)',
        'Ya existe esa abreviatura para esta categoría.',
    )
