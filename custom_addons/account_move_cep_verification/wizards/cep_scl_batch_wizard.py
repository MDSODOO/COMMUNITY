import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CEPSCLBatchWizard(models.TransientModel):
    _name = 'cep.scl.batch.wizard'
    _description = 'Wizard de Verificación CEP Banxico CEP-SCL'

    step = fields.Selection([
        ('select', 'Paso 1: Seleccionar'),
        ('generate', 'Paso 2: Generar Archivo'),
        ('submit', 'Paso 3: Enviado a Banxico'),
        ('import', 'Paso 4: Importar Resultados'),
    ], default='select', required=True)

    # Paso 1
    move_ids = fields.Many2many(
        'account.move',
        string='Transferencias SPEI',
        domain="[('transfer_type','=','spei')]",
    )
    total_moves = fields.Integer('Total', compute='_compute_total')
    validation_errors = fields.Text('Errores de Validación', readonly=True)

    # Paso 2
    txt_file = fields.Binary('Archivo TXT para Banxico')
    txt_filename = fields.Char()
    instructions = fields.Html('Instrucciones', readonly=True)

    # Paso 3
    banxico_token = fields.Char('Token de Banxico')
    batch_id = fields.Many2one('cep.scl.batch', 'Lote Creado', readonly=True)
    user_email = fields.Char('Tu email (para recordatorio)', default=lambda self: self.env.user.email)

    # Paso 4
    zip_file = fields.Binary('ZIP descargado de Banxico')
    zip_filename = fields.Char()
    process_summary = fields.Text('Resumen de Procesamiento', readonly=True)

    @api.depends('move_ids')
    def _compute_total(self):
        for rec in self:
            rec.total_moves = len(rec.move_ids)

    # ------------------------------------------------------------------
    # Acciones por paso
    # ------------------------------------------------------------------

    def action_generate_txt(self):
        """Paso 1 → 2: valida y genera el archivo .TXT."""
        from odoo.addons.account_move_cep_verification.services.cep_banxico_service import CEPBanxicoService

        self.ensure_one()
        if not self.move_ids:
            raise UserError(_('Selecciona al menos una transferencia SPEI.'))

        service = CEPBanxicoService(self.env)
        try:
            txt_content, filename = service.generate_scl_import_file(self.move_ids)
        except UserError:
            raise

        instructions_html = service.get_manual_verification_instructions(filename)

        self.write({
            'step': 'generate',
            'txt_file': base64.b64encode(txt_content.encode('utf-8')),
            'txt_filename': filename,
            'instructions': instructions_html,
        })
        return self._reopen()

    def action_save_token(self):
        """Paso 2 → 3: guarda el token de Banxico y crea el registro de lote."""
        self.ensure_one()
        if not self.banxico_token:
            raise UserError(_('Ingresa el token que te asignó Banxico antes de continuar.'))

        batch = self.env['cep.scl.batch'].create({
            'batch_token': self.banxico_token,
            'submission_date': fields.Datetime.now(),
            'status': 'submitted',
            'move_ids': [(6, 0, self.move_ids.ids)],
        })
        # Actualizar el estado de cada move
        self.move_ids.write({'cep_scl_batch_status': 'pending_result'})

        self.write({
            'step': 'submit',
            'batch_id': batch.id,
        })
        return self._reopen()

    def action_process_zip(self):
        """Paso 3 → 4: procesa el ZIP de resultados de Banxico."""
        from odoo.addons.account_move_cep_verification.services.cep_banxico_service import CEPBanxicoService

        self.ensure_one()
        if not self.zip_file:
            raise UserError(_('Sube el archivo ZIP descargado de Banxico.'))
        if not self.batch_id:
            raise UserError(_('No hay lote registrado. Regresa al paso anterior.'))

        service = CEPBanxicoService(self.env)
        result = service.process_scl_results_zip(self.batch_id, self.zip_file)

        summary = (
            f'Procesamiento completado:\n'
            f'  ✅ Encontrados: {result["found"]}\n'
            f'  ❌ No encontrados: {result["not_found"]}\n'
            f'  📋 Total: {result["total"]}'
        )
        self.write({
            'step': 'import',
            'process_summary': summary,
        })
        return self._reopen()

    def action_advance_to_import(self):
        """Paso 3 → 4: usuario ya tiene el ZIP, avanza sin procesarlo aún."""
        self.ensure_one()
        self.step = 'import'
        return self._reopen()

    def action_go_back(self):
        """Permite regresar al paso anterior."""
        self.ensure_one()
        order = ['select', 'generate', 'submit', 'import']
        idx = order.index(self.step)
        if idx > 0:
            self.step = order[idx - 1]
        return self._reopen()

    def action_view_batch(self):
        """Abre el lote creado en vista form."""
        self.ensure_one()
        if not self.batch_id:
            return {'type': 'ir.actions.act_close'}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lote CEP-SCL'),
            'res_model': 'cep.scl.batch',
            'res_id': self.batch_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Verificación CEP Banxico'),
            'res_model': 'cep.scl.batch.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
