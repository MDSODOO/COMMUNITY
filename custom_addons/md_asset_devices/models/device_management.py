# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DeviceManagement(models.Model):
    _name = "device.management"
    _description = "Gestión de Dispositivos Físicos"
    _rec_name = "nombre_dispositivo"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _codigo_dispositivo_uniq = models.Constraint(
        'UNIQUE(codigo_dispositivo)',
        'El código/serial del dispositivo debe ser único.',
    )

    # Estado y control
    state = fields.Selection([
        ('active', 'En uso'),
        ('maintenance', 'Mantenimiento'),
        ('retired', 'Fuera de servicio'),
    ], string="Estado", default='active', required=True, tracking=True)
    active = fields.Boolean(string="Activo", default=True, tracking=True)
    color = fields.Integer('Color Kanban')

    # Identificación
    nombre_dispositivo = fields.Char(string="Dispositivo", required=True, tracking=True)
    modelo_dispositivo = fields.Char(string="Modelo", tracking=True)
    codigo_dispositivo = fields.Char(string="Código/Serial", default="/", copy=False, tracking=True)
    logo_dispositivo = fields.Binary(string="Logo/Imagen")
    categoria = fields.Selection([
        ('laptop', 'Laptop'),
        ('desktop', 'Desktop'),
        ('monitor', 'Monitor'),
        ('printer', 'Impresora'),
        ('server', 'Servidor'),
        ('networking', 'Equipos de Red'),
        ('storage', 'Almacenamiento'),
        ('otro', 'Otro'),
    ], string="Categoría", required=True, tracking=True)

    # Ubicación y asignación
    company_id = fields.Many2one(
        'res.company', string="Sucursal", required=True, tracking=True,
        default=lambda self: self.env.company,
    )
    ubicacion_fisica = fields.Char(string="Ubicación Física", tracking=True)
    usuario_asignado = fields.Many2one('hr.employee', string="Asignado a", ondelete='set null')
    departamento = fields.Many2one('hr.department', string="Departamento", ondelete='set null')

    # A la mano (REGLA CRÍTICA)
    cantidad_a_la_mano = fields.Integer(
        string="Cantidad A la mano",
        compute='_compute_cantidad_a_la_mano',
        store=False
    )

    # Financiero
    fecha_adquisicion = fields.Date(string="Fecha de Adquisición", tracking=True)
    costo_adquisicion = fields.Float(string="Costo de Adquisición", digits=(10, 2))
    valor_actual = fields.Float(string="Valor Actual", compute='_compute_valor_actual', digits=(10, 2))

    # Garantía
    garantia_fecha_inicio = fields.Date(string="Garantía - Desde", tracking=True)
    garantia_fecha_fin = fields.Date(string="Garantía - Hasta", tracking=True)
    garantia_vigente = fields.Boolean(
        string="Garantía Vigente",
        compute='_compute_garantia_vigente',
        search='_search_garantia_vigente',
    )
    garantia_porcentaje_restante = fields.Integer(
        string="Porcentaje Garantía Restante",
        compute='_compute_garantia_porcentaje'
    )

    # Relaciones One2many (Submodelos)
    inventory_ids = fields.One2many('device.inventory', 'device_id', string="Inventario A la mano")
    assignment_ids = fields.One2many('device.assignment', 'device_id', string="Asignaciones")
    maintenance_ids = fields.One2many('device.maintenance', 'device_id', string="Mantenimientos")
    documentation_ids = fields.One2many('device.documentation', 'device_id', string="Documentación")
    payment_ids = fields.One2many('device.payment', 'device_id', string="Pagos")
    subscription_ids = fields.One2many('device.subscription', 'device_id', string="Suscripciones")
    todo_ids = fields.One2many('device.todo', 'device_id', string="Tareas")

    # Smart button counts / Contadores para botones inteligentes
    assignment_count = fields.Integer(compute='_compute_assignment_count', string="Cant. Asignaciones")
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string="Cant. Mantenimientos")
    documentation_count = fields.Integer(compute='_compute_documentation_count', string="Documentos")
    payment_count = fields.Integer(compute='_compute_payment_count', string="Cant. Pagos")
    subscription_count = fields.Integer(compute='_compute_subscription_count', string="Cant. Suscripciones")
    invoice_count = fields.Integer(compute='_compute_invoice_count', string="Facturas")
    todo_count = fields.Integer(compute='_compute_todo_count', string="Tareas Pendientes")
    todo_urgente_count = fields.Integer(compute='_compute_todo_count', string="Tareas Urgentes")

    # Cost and alert summaries / Resúmenes de costos y alertas
    mantenimiento_costo_total = fields.Float(
        string="Costo Total de Mantenimientos",
        compute='_compute_cost_summaries',
        digits=(10, 2)
    )
    pagos_monto_total = fields.Float(
        string="Total de Pagos",
        compute='_compute_cost_summaries',
        digits=(10, 2)
    )
    suscripciones_costo_anual_total = fields.Float(
        string="Costo Anual de Suscripciones",
        compute='_compute_cost_summaries',
        digits=(10, 2)
    )
    mantenimiento_vencido_count = fields.Integer(
        string="Mantenimientos Vencidos",
        compute='_compute_alert_counts',
        store=True,
    )
    documentos_vencidos_count = fields.Integer(
        string="Documentos Vencidos",
        compute='_compute_alert_counts',
        store=True,
    )
    suscripciones_vencidas_count = fields.Integer(
        string="Suscripciones Vencidas",
        compute='_compute_alert_counts',
        store=True,
    )

    # Datos para Kanban
    proximo_mantenimiento_fecha = fields.Date(
        compute='_compute_proximo_mantenimiento',
        string="Próximo Mantenimiento"
    )
    proxima_suscripcion_vencimiento = fields.Date(
        compute='_compute_proxima_suscripcion_vencimiento',
        string="Próxima Suscripción Vencimiento"
    )

    # ─── COMPUTES ───────────────────────────────────────────
    @api.depends('inventory_ids.cantidad_a_la_mano')
    def _compute_cantidad_a_la_mano(self):
        for device in self:
            device.cantidad_a_la_mano = sum(inv.cantidad_a_la_mano for inv in device.inventory_ids)

    @api.depends('costo_adquisicion', 'fecha_adquisicion')
    def _compute_valor_actual(self):
        for device in self:
            if not device.costo_adquisicion or not device.fecha_adquisicion:
                device.valor_actual = device.costo_adquisicion or 0.0
                continue

            # Depreciación simple: 10% por año
            from datetime import date
            anos = (date.today() - device.fecha_adquisicion).days / 365.25
            depreciacion = device.costo_adquisicion * (anos * 0.10)
            device.valor_actual = max(0, device.costo_adquisicion - depreciacion)

    @api.depends('garantia_fecha_fin')
    def _compute_garantia_vigente(self):
        from datetime import date
        today = date.today()
        for device in self:
            device.garantia_vigente = (
                device.garantia_fecha_fin and device.garantia_fecha_fin >= today
            )

    def _search_garantia_vigente(self, operator, value):
        from datetime import date
        today = date.today()
        if (operator == '=' and value) or (operator == '!=' and not value):
            return ['|', ('garantia_fecha_fin', '=', False),
                         ('garantia_fecha_fin', '>=', today)]
        return [('garantia_fecha_fin', '!=', False),
                ('garantia_fecha_fin', '<', today)]

    @api.depends('garantia_fecha_inicio', 'garantia_fecha_fin')
    def _compute_garantia_porcentaje(self):
        from datetime import date
        today = date.today()
        for device in self:
            if not device.garantia_fecha_inicio or not device.garantia_fecha_fin:
                device.garantia_porcentaje_restante = 0
                continue

            total_dias = (device.garantia_fecha_fin - device.garantia_fecha_inicio).days
            dias_restantes = (device.garantia_fecha_fin - today).days

            if total_dias <= 0:
                device.garantia_porcentaje_restante = 0
            else:
                device.garantia_porcentaje_restante = max(0, int((dias_restantes / total_dias) * 100))

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for device in self:
            device.assignment_count = len(device.assignment_ids)

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for device in self:
            device.maintenance_count = len(device.maintenance_ids)

    @api.depends('documentation_ids')
    def _compute_documentation_count(self):
        for device in self:
            device.documentation_count = len(device.documentation_ids)

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for device in self:
            device.payment_count = len(device.payment_ids)

    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for device in self:
            device.subscription_count = len(device.subscription_ids)

    @api.depends('payment_ids.invoice_id')
    def _compute_invoice_count(self):
        for device in self:
            device.invoice_count = len(device.payment_ids.mapped('invoice_id'))

    @api.depends('todo_ids', 'todo_ids.estado', 'todo_ids.prioridad')
    def _compute_todo_count(self):
        for device in self:
            pendientes = device.todo_ids.filtered(lambda t: t.estado not in ('done', 'cancelled'))
            device.todo_count = len(pendientes)
            device.todo_urgente_count = len(pendientes.filtered(lambda t: t.prioridad == 'urgente'))

    @api.depends(
        'maintenance_ids.costo_total',
        'maintenance_ids.estado',
        'payment_ids.monto',
        'subscription_ids.costo_anual',
        'subscription_ids.estado',
    )
    def _compute_cost_summaries(self):
        for device in self:
            maintenances = device.maintenance_ids.filtered(lambda m: m.estado != 'cancelled')
            subscriptions = device.subscription_ids.filtered(lambda s: s.estado != 'cancelado')
            device.mantenimiento_costo_total = sum(maintenances.mapped('costo_total'))
            device.pagos_monto_total = sum(device.payment_ids.mapped('monto'))
            device.suscripciones_costo_anual_total = sum(subscriptions.mapped('costo_anual'))

    @api.depends(
        'maintenance_ids.fecha_programada',
        'maintenance_ids.estado',
        'documentation_ids.fecha_vencimiento',
        'subscription_ids.fecha_vencimiento',
        'subscription_ids.estado',
    )
    def _compute_alert_counts(self):
        from datetime import date
        today = date.today()
        for device in self:
            device.mantenimiento_vencido_count = len(device.maintenance_ids.filtered(
                lambda m: m.estado in ('scheduled', 'in_progress') and m.fecha_programada and m.fecha_programada < today
            ))
            device.documentos_vencidos_count = len(device.documentation_ids.filtered(
                lambda d: d.fecha_vencimiento and d.fecha_vencimiento < today
            ))
            device.suscripciones_vencidas_count = len(device.subscription_ids.filtered(
                lambda s: s.estado != 'cancelado' and s.fecha_vencimiento and s.fecha_vencimiento < today
            ))

    @api.depends('maintenance_ids.fecha_programada')
    def _compute_proximo_mantenimiento(self):
        for device in self:
            mantenimientos = device.maintenance_ids.filtered(lambda m: m.estado in ['scheduled', 'in_progress'])
            if mantenimientos:
                device.proximo_mantenimiento_fecha = min(m.fecha_programada for m in mantenimientos)
            else:
                device.proximo_mantenimiento_fecha = None

    @api.depends('subscription_ids.fecha_vencimiento')
    def _compute_proxima_suscripcion_vencimiento(self):
        from datetime import date
        today = date.today()
        for device in self:
            suscripciones_activas = device.subscription_ids.filtered(
                lambda s: s.estado != 'cancelado' and s.fecha_vencimiento >= today
            )
            if suscripciones_activas:
                device.proxima_suscripcion_vencimiento = min(s.fecha_vencimiento for s in suscripciones_activas)
            else:
                device.proxima_suscripcion_vencimiento = None

    # ─── ACTIONS ────────────────────────────────────────────
    def action_set_active(self):
        self.state = 'active'

    def action_set_maintenance(self):
        self.state = 'maintenance'

    def action_retire_device(self):
        self.state = 'retired'
        active_assignments = self.assignment_ids.filtered(lambda a: a.estado == 'activa')
        if active_assignments:
            active_assignments.write({
                'estado': 'devuelto',
                'fecha_devolucion': fields.Date.today(),
            })

    def _sync_assignment_summary(self):
        """Keep assignment summary aligned with active lines / Mantiene el resumen alineado."""
        for device in self:
            active_assignments = device.assignment_ids.filtered(lambda a: a.estado == 'activa')
            assignment = active_assignments[:1]
            employee = assignment.usuario_asignado if assignment else False
            device.write({
                'usuario_asignado': employee.id if employee else False,
                'departamento': employee.department_id.id if employee and employee.department_id else False,
            })

    def _sync_maintenance_state(self):
        """Reflect open maintenance without reopening retired devices / Sin reactivar retirados."""
        for device in self:
            if device.state == 'retired':
                continue
            has_open_maintenance = any(
                maintenance.estado == 'in_progress'
                for maintenance in device.maintenance_ids
            )
            target_state = 'maintenance' if has_open_maintenance else 'active'
            if device.state != target_state:
                device.state = target_state

    def action_view_assignments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.assignment',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
            'name': f'Asignaciones - {self.nombre_dispositivo}',
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.maintenance',
            'view_mode': 'list,form,calendar',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
            'name': f'Mantenimientos - {self.nombre_dispositivo}',
        }

    def action_view_documentation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.documentation',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
            'name': f'Documentación - {self.nombre_dispositivo}',
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.payment',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
            'name': f'Pagos - {self.nombre_dispositivo}',
        }

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.subscription',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
            'name': f'Suscripciones - {self.nombre_dispositivo}',
        }

    def action_view_invoices(self):
        self.ensure_one()
        invoices = self.payment_ids.mapped('invoice_id')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {
                'default_move_type': 'out_invoice',
                'default_invoice_origin': self.nombre_dispositivo,
            },
            'name': f'Facturas - {self.nombre_dispositivo}',
        }

    def action_view_overdue_maintenance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.maintenance',
            'view_mode': 'list,form,calendar',
            'domain': [
                ('device_id', '=', self.id),
                ('estado', 'in', ('scheduled', 'in_progress')),
                ('fecha_programada', '<', fields.Date.today()),
            ],
            'context': {'default_device_id': self.id},
            'name': f'Mantenimientos Vencidos - {self.nombre_dispositivo}',
        }

    def action_view_overdue_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.documentation',
            'view_mode': 'list,form',
            'domain': [
                ('device_id', '=', self.id),
                ('fecha_vencimiento', '<', fields.Date.today()),
            ],
            'context': {'default_device_id': self.id},
            'name': f'Documentos Vencidos - {self.nombre_dispositivo}',
        }

    def action_view_overdue_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.subscription',
            'view_mode': 'list,form',
            'domain': [
                ('device_id', '=', self.id),
                ('estado', '!=', 'cancelado'),
                ('fecha_vencimiento', '<', fields.Date.today()),
            ],
            'context': {'default_device_id': self.id},
            'name': f'Suscripciones Vencidas - {self.nombre_dispositivo}',
        }

    def action_view_todos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'device.todo',
            'view_mode': 'list,form,calendar',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
            'name': f'Tareas - {self.nombre_dispositivo}',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('codigo_dispositivo') or vals.get('codigo_dispositivo') == '/':
                vals['codigo_dispositivo'] = self.env['ir.sequence'].next_by_code('device.management') or '/'
        return super().create(vals_list)
