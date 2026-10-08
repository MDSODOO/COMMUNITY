from odoo import models, fields, api


class ProjectProject(models.Model):
    """Extiende el proyecto existente para vincular un equipo de Helpdesk.

    Cambios clave vs. versión anterior:
    - helpdesk_team_id: Many2one hacia mds.helpdesk.team, configurable
      desde la pestaña "Configuración" del proyecto sin crear otro proyecto.
    - ticket_ids / ticket_count: One2many + computed para el Smart Button.
    - action_view_tickets: Abre los tickets filtrados por ESTE proyecto,
      con contexto default para que nuevos tickets hereden project_id y team_id.
    """
    _inherit = 'project.project'

    helpdesk_team_id = fields.Many2one(
        'mds.helpdesk.team',
        string='Equipo de Soporte MDS',
        help='Equipo de Helpdesk asignado a este proyecto. Los tickets creados desde aquí heredarán este equipo automáticamente.',
    )
    ticket_ids = fields.One2many(
        'mds.helpdesk.ticket',
        'project_id',
        string='Tickets de Soporte',
    )
    ticket_count = fields.Integer(
        string='Tickets',
        compute='_compute_ticket_count',
    )

    @api.depends('ticket_ids')
    def _compute_ticket_count(self):
        data = self.env['mds.helpdesk.ticket'].read_group(
            [('project_id', 'in', self.ids)],
            ['project_id'],
            ['project_id'],
        )
        mapped = {d['project_id'][0]: d['project_id_count'] for d in data}
        for project in self:
            project.ticket_count = mapped.get(project.id, 0)

    def action_view_tickets(self):
        """Abre la vista de tickets asociados a este proyecto.

        El contexto inyecta default_project_id y default_team_id para
        que al hacer clic en "Crear" desde la vista de tickets, el nuevo
        ticket herede automáticamente el proyecto y el equipo.
        """
        self.ensure_one()
        return {
            'name': f'🎟️ Tickets — {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'mds.helpdesk.ticket',
            'view_mode': 'kanban,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'default_team_id': self.helpdesk_team_id.id if self.helpdesk_team_id else False,
            },
        }
