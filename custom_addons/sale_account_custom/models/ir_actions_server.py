# -*- coding: utf-8 -*-

from odoo import models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    def _get_eval_context(self, action=None):
        """Backport Odoo 19 fix: keep all server-action variables on one env."""
        return super(
            IrActionsServer,
            self.with_context(mail_notify_force_send=False),
        )._get_eval_context(action=action)
