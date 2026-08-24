from odoo import fields, models


class CepVerificationLog(models.Model):
    _name = 'cep.verification.log'
    _description = 'Log de Verificaciones CEP Banxico'
    _order = 'verification_date desc'
    _rec_name = 'trace_code'

    move_id = fields.Many2one('account.move', string='Factura/Pago', ondelete='cascade', index=True)
    trace_code = fields.Char('Clave de Rastreo')
    reference = fields.Char('Número de Referencia')
    operation_date = fields.Date('Fecha de Operación')
    verification_date = fields.Datetime('Fecha de Verificación', default=fields.Datetime.now)
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('found', 'Encontrado'),
        ('not_found', 'No Encontrado'),
        ('manual_review', 'Revisión Manual'),
    ], string='Resultado')
    banxico_response = fields.Text('Respuesta / Detalle Banxico')
    notes = fields.Text('Notas')
