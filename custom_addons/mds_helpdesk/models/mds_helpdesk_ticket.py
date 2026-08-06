from odoo import models, fields, api, _


class MdsHelpdeskTicket(models.Model):
    """Ticket de soporte vinculado directamente al proyecto existente.

    Cambios vs. versión anterior:
    - Añade campo team_id (Many2one) al equipo de soporte del proyecto.
    - on create: hereda project_id y team_id del contexto del Smart Button.
    - action_escalate: lee el usuario N2 desde el equipo, no hardcodeado.
    """
    _name = 'mds.helpdesk.ticket'
    _description = 'Ticket de Soporte MDS'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    # --- Identificación ---
    name = fields.Char(
        string='Título del Ticket',
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string='Folio',
        readonly=True,
        copy=False,
        default=lambda self: _('Nuevo'),
    )

    # --- Relaciones (coexiste dentro del proyecto, no lo duplica) ---
    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        required=True,
        tracking=True,
        help='Proyecto al que pertenece este ticket. Se asigna automáticamente desde el Smart Button.',
    )
    team_id = fields.Many2one(
        'mds.helpdesk.team',
        string='Equipo de Soporte',
        tracking=True,
        help='Se hereda del equipo configurado en el proyecto.',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsable Asignado',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente / Sucursal',
        tracking=True,
    )

    # --- Estado y Prioridad ---
    stage = fields.Selection(
        [
            ('new', '📥 Nuevo'),
            ('analysis', '🔍 En Análisis (N1)'),
            ('escalated', '🛠️ Escalado (N2)'),
            ('testing', '🧪 En Pruebas'),
            ('done', '✅ Resuelto'),
        ],
        string='Etapa',
        default='new',
        tracking=True,
        group_expand='_group_expand_stage',
    )
    priority = fields.Selection(
        [
            ('0', 'Baja'),
            ('1', 'Normal'),
            ('2', 'Alta'),
            ('3', 'Urgente / Bloqueante'),
        ],
        string='Prioridad',
        default='1',
        tracking=True,
    )

    # --- Contenido ---
    description = fields.Html(string='Descripción del Problema')
    tag_ids = fields.Many2many(
        'project.tags',
        'mds_ticket_tag_rel',
        'ticket_id',
        'tag_id',
        string='Etiquetas',
    )

    # ---- Métodos ----

    @api.model
    def _group_expand_stage(self, stages, domain, order=None):
        """Muestra todas las columnas del Kanban aunque estén vacías."""
        return [key for key, _ in type(self).stage.selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Generar folio secuencial MDS-TICK-XXXX
            if vals.get('code', _('Nuevo')) == _('Nuevo'):
                vals['code'] = (
                    self.env['ir.sequence'].next_by_code('mds.helpdesk.ticket')
                    or _('Nuevo')
                )
            # Heredar equipo desde el proyecto si no se especificó
            if vals.get('project_id') and not vals.get('team_id'):
                project = self.env['project.project'].browse(vals['project_id'])
                if project.helpdesk_team_id:
                    vals['team_id'] = project.helpdesk_team_id.id
        return super().create(vals_list)

    def action_escalate(self):
        """Escala el ticket al usuario N2 configurado en el equipo del proyecto."""
        for ticket in self:
            escalation_user = (
                ticket.team_id.escalation_user_id
                if ticket.team_id
                else False
            )
            if not escalation_user:
                # Fallback: buscar Daniel Cervera directamente
                escalation_user = self.env['res.users'].search(
                    [('login', '=', 'daniel.cervera@medicinedepotsureste.mx')],
                    limit=1,
                )
            ticket.write({
                'stage': 'escalated',
                'user_id': escalation_user.id if escalation_user else ticket.user_id.id,
            })
            ticket.message_post(
                body=_(
                    '⚠️ <b>Ticket escalado a Nivel 2.</b> Responsable: <b>%s</b>',
                    escalation_user.name if escalation_user else 'Sin asignar',
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_resolve(self):
        """Marca el ticket como resuelto."""
        self.write({'stage': 'done'})
        for ticket in self:
            ticket.message_post(
                body=_('✅ Ticket resuelto y cerrado.'),
                subtype_xmlid='mail.mt_note',
            )
