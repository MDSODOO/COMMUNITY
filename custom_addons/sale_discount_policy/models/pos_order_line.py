from odoo import models, fields, api
from odoo.tools.float_utils import float_compare


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    discount_policy_reason = fields.Char(
        string='Policy Discount Reason',
        help='Reason why discount was (not) applied at POS.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Server-side safety net: clear discount if product is restricted."""
        res = super().create(vals_list)
        if not res:
            return res

        company_ids = res.mapped('order_id.company_id').ids
        policies = self.env['sale.discount.policy'].search([
            ('active', '=', True),
            ('company_id', 'in', company_ids),
        ])
        policy_by_company = {}
        for policy in policies:
            policy_by_company.setdefault(policy.company_id.id, policy)
        restricted_eans = set(
            self.env['sale.restricted.sku'].search([]).mapped('ean')
        )

        for line in res:
            if not line.product_id or not line.order_id.partner_id:
                continue
            policy = policy_by_company.get(line.order_id.company_id.id)
            if not policy:
                continue

            # Check if partner is eligible for discount
            partner_id = line.order_id.partner_id.id
            allowed_partner_ids = policy.partner_ids.ids if policy.partner_ids else []

            if partner_id not in allowed_partner_ids:
                continue

            product_tag_names = line.product_id.product_tmpl_id.product_tag_ids.mapped('name')

            # Check 1: Restricted brand tags
            target_reason = False
            for tag in product_tag_names:
                if tag.startswith('MARCA_RESTRINGIDA_'):
                    target_reason = 'RESTRICTED_BRAND'
                    break

            # Check 2: Restricted by EAN/SKU code
            if not target_reason:
                product_codes = {
                    c for c in {
                        line.product_id.barcode,
                        line.product_id.default_code,
                    } if c
                }
                if product_codes and product_codes & restricted_eans:
                    target_reason = 'RESTRICTED_SKU'

            if target_reason:
                update_vals = {}
                if float_compare(line.discount, 0.0, precision_digits=6) != 0:
                    update_vals['discount'] = 0.0
                if line.discount_policy_reason != target_reason:
                    update_vals['discount_policy_reason'] = target_reason
                if update_vals:
                    line.write(update_vals)

        return res
