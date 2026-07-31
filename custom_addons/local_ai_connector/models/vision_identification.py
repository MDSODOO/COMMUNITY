from odoo import api, fields, models


class LocalAiVisionIdentification(models.Model):
    _name = "local.ai.vision.identification"
    _description = (
        "Registro de cada identificacion de producto desde foto: quien la solicito, "
        "que respondio el modelo de vision, a que producto se mapeo, y cuanto hay "
        "A la mano. Trazabilidad completa para auditoria y mejora continua."
    )
    _order = "create_date desc"

    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        default=lambda self: self.env.user,
        required=True,
        index=True,
    )
    image_filename = fields.Char(string="Nombre del archivo")
    raw_model_output = fields.Text(
        string="Salida cruda del modelo (JSON)",
        help="Respuesta JSON completa devuelta por qwen2.5vl:7b.",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto identificado",
        index=True,
    )
    confidence = fields.Float(
        string="Confianza",
        digits=(16, 4),
        help="Nivel de confianza reportado por el modelo (0.0 - 1.0).",
    )
    nombre_comercial = fields.Char(string="Nombre comercial detectado")
    principio_activo = fields.Char(string="Principio activo detectado")
    presentacion = fields.Char(string="Presentacion detectada")
    cantidad_solicitada = fields.Integer(string="Cantidad solicitada (del cliente)")
    on_hand = fields.Float(
        string="A la mano",
        digits="Product Unit of Measure",
        help="Cantidad fisica A la mano del producto al momento de la identificacion.",
    )
    success = fields.Boolean(
        string="Identificacion exitosa",
        help="True si se encontro un producto en el catalogo con suficiente confianza.",
    )
    error_message = fields.Text(
        string="Mensaje de error",
        help="Descripcion del error si no se pudo identificar el producto.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compania",
        default=lambda self: self.env.company,
    )
