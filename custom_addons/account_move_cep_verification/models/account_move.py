from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    transfer_type = fields.Selection(
        [('spei', 'SPEI'), ('otro', 'Otro')],
        string='Tipo de Transferencia',
        default='otro',
    )
    transfer_trace_code = fields.Char('Clave de Rastreo', size=30)
    transfer_reference = fields.Char('Número de Referencia', size=7)
    emission_bank_code = fields.Char('Banco Emisor', size=5)
    receiving_bank_code = fields.Char('Banco Receptor', size=5)
    transfer_amount = fields.Monetary('Monto de Transferencia', currency_field='currency_id')
    transfer_operation_date = fields.Date('Fecha de Operación')

    cep_verification_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('verified_manual', 'Verificado Manual'),
        ('not_found_banxico', 'No Encontrado en Banxico'),
        ('manual_review_needed', 'Revisar Manualmente'),
    ], string='Estado CEP', default='pending')
    cep_verification_date = fields.Datetime('Fecha de Verificación', readonly=True)
    cep_raw_response = fields.Text('Respuesta CEP-SCL (JSON)')
    cep_verification_log = fields.Text('Log de Verificación')

    cep_scl_batch_id = fields.Char('Token de Lote Banxico', readonly=True)
    cep_scl_batch_status = fields.Selection([
        ('not_uploaded', 'No Cargado'),
        ('pending_result', 'Esperando Resultado Banxico'),
        ('downloaded', 'CEP Descargado'),
    ], string='Estado en Lote', default='not_uploaded', readonly=True)

    def action_open_cep_verification_wizard(self):
        self.ensure_one()
        if self.transfer_type != 'spei':
            raise UserError(_('Solo se pueden verificar transferencias de tipo SPEI.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Verificar CEP en Banxico'),
            'res_model': 'cep.scl.batch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_ids': [(6, 0, self.ids)]},
        }

    def action_mark_manual_review(self):
        self.ensure_one()
        self.write({
            'cep_verification_status': 'manual_review_needed',
            'cep_verification_date': fields.Datetime.now(),
        })
