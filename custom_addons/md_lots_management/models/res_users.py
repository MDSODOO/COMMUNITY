from odoo import api, models


class ResUsers(models.Model):
    """Redirige automáticamente a los usuarios de Consulta Handheld a esa
    vista al iniciar sesión, en vez de detectar el dispositivo por
    user-agent (frágil): se usa el "Home Action" nativo de Odoo, ligado al
    grupo de seguridad group_lots_handheld_user en vez del hardware.
    """

    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._md_apply_handheld_home_action()
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'group_ids' in vals:
            self._md_apply_handheld_home_action()
        return res

    def _md_apply_handheld_home_action(self):
        handheld_group = self.env.ref(
            'md_lots_management.group_lots_handheld_user', raise_if_not_found=False
        )
        action = self.env.ref(
            'md_lots_management.action_production_lot_handheld', raise_if_not_found=False
        )
        if not handheld_group or not action:
            return
        for user in self:
            if handheld_group in user.group_ids and not user.action_id:
                user.action_id = action.id
