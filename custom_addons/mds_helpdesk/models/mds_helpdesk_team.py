from odoo import models, fields


class MdsHelpdeskTeam(models.Model):
    """Equipo de soporte liviano que se vincula 1:1 al Proyecto.

    Diferencia clave vs. versión anterior:
    - NO crea un proyecto separado; se asocia al proyecto existente
      via Many2one en project.project.
    - Centraliza la configuración de escalación (usuario N2) y
      los miembros del equipo N1 en un solo registro reutilizable.
    """
    _name = 'mds.helpdesk.team'
    _description = 'Equipo de Soporte MDS'

    name = fields.Char(
        string='Nombre del Equipo',
        required=True,
        help='Ej: "Equipo MDS Operaciones", "Equipo MDS Desarrollo".',
    )
    project_ids = fields.One2many(
        'project.project',
        'helpdesk_team_id',
        string='Proyectos Vinculados',
    )
    member_ids = fields.Many2many(
        'res.users',
        'mds_helpdesk_team_member_rel',
        'team_id',
        'user_id',
        string='Miembros del Equipo (Nivel 1)',
        help='Usuarios que atienden tickets en primer nivel.',
    )
    escalation_user_id = fields.Many2one(
        'res.users',
        string='Responsable de Escalación (Nivel 2)',
        help='Usuario al que se reasignan los tickets que requieren intervención técnica avanzada.',
    )
    ticket_ids = fields.One2many(
        'mds.helpdesk.ticket',
        'team_id',
        string='Tickets del Equipo',
    )
    ticket_count = fields.Integer(
        string='Total Tickets',
        compute='_compute_ticket_count',
    )

    def _compute_ticket_count(self):
        for team in self:
            team.ticket_count = len(team.ticket_ids)
