from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LotAssignCompanyWizard(models.TransientModel):
    _name = 'md.lot.assign.company.wizard'
    _description = 'Asignar Empresa a Lote'

    lot_id = fields.Many2one(
        'stock.lot',
        string='Lote',
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
    )
    confirmation_text = fields.Char(
        string='Confirmación',
        readonly=True,
        compute='_compute_confirmation_text',
    )

    @api.depends('lot_id', 'company_id')
    def _compute_confirmation_text(self):
        for wizard in self:
            if wizard.lot_id and wizard.company_id:
                wizard.confirmation_text = (
                    f'Asignando empresa {wizard.company_id.name} al lote {wizard.lot_id.name}'
                )
            else:
                wizard.confirmation_text = ''

    def action_assign_company(self):
        self.ensure_one()
        if not self.lot_id:
            raise ValidationError('Selecciona un lote para asignar empresa.')
        if not self.company_id:
            raise ValidationError('Selecciona una empresa para asignar.')

        self.lot_id.with_context(md_assign_company=True).write({'company_id': self.company_id.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Empresa asignada',
                'message': (
                    f'La empresa {self.company_id.name} ha sido asignada '
                    f'correctamente al lote {self.lot_id.name}.'
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
