import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CepSclBatch(models.Model):
    _name = 'cep.scl.batch'
    _description = 'Lote de Verificación Banxico CEP-SCL'
    _order = 'created_date desc'
    _rec_name = 'batch_token'

    batch_token = fields.Char('Token de Banxico', copy=False, index=True)
    created_date = fields.Datetime('Fecha de Creación', default=fields.Datetime.now, readonly=True)
    submission_date = fields.Datetime('Fecha de Envío a Banxico')
    status = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviado a Banxico'),
        ('results_available', 'Resultados Disponibles'),
        ('imported', 'Importado'),
    ], string='Estado', default='draft', tracking=False)
    total_transfers = fields.Integer('Total', compute='_compute_totals', store=True)
    transfers_found = fields.Integer('Encontradas', default=0)
    transfers_not_found = fields.Integer('No Encontradas', default=0)
    zip_file = fields.Binary('ZIP de Resultados')
    zip_filename = fields.Char()
    move_ids = fields.Many2many(
        'account.move',
        'cep_scl_batch_move_rel',
        'batch_id', 'move_id',
        string='Movimientos SPEI',
    )
    notes = fields.Text('Notas / Recordatorios')

    @api.depends('move_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_transfers = len(rec.move_ids)

    def cron_remind_pending_batches(self):
        """Registra warning en log para lotes enviados hace más de 24h sin resultados."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        pending = self.search([
            ('status', '=', 'submitted'),
            ('submission_date', '<=', cutoff),
        ])
        for batch in pending:
            _logger.warning(
                'CEP-SCL: lote ID=%s lleva >24h sin importar resultados. '
                'Token Banxico: %s. Ir a https://www.banxico.org.mx/cep-scl/ '
                'para descargar el ZIP y subirlo en Odoo.',
                batch.id, batch.batch_token or 'NO GUARDADO',
            )
            batch.notes = (batch.notes or '') + (
                f'\n[Aviso automático] Lote pendiente de resultados desde {batch.submission_date}.'
            )
