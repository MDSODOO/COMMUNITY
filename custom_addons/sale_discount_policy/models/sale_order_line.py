from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools.float_utils import float_compare
from ..engines import compute_discount, DiscountContext


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount_reason = fields.Char(
        string='Discount Reason',
        compute='_compute_discount_reason',
        store=False,
        help='Why discount was (not) applied: APPLIED, WRONG_GROUP, WRONG_BRANCH, RESTRICTED_BRAND, RESTRICTED_SKU',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create and apply discount policy on new lines."""
        res = super().create(vals_list)
        res._apply_discount_policy()
        return res

    def write(self, vals):
        """Apply discount policy when relevant fields change."""
        res = super().write(vals)
        if not self.env.context.get('skip_discount_policy') and {
            'product_id',
            'order_id',
            'product_uom_qty',
            'product_uom',
            'product_uom_id',
            'discount',
        } & set(vals):
            self._apply_discount_policy()
        return res

    def _get_active_discount_policy(self):
        """Return the active policy for this order's company, or False."""
        return self.env['sale.discount.policy'].search([
            ('active', '=', True),
            ('company_id', '=', self.order_id.company_id.id),
        ], limit=1)

    def _apply_discount_policy(self):
        """Apply discount policy logic to all lines."""
        if not self:
            return

        policy_by_company = {}
        for company in self.mapped('order_id.company_id'):
            policy_by_company[company.id] = self.env['sale.discount.policy'].search([
                ('active', '=', True),
                ('company_id', '=', company.id),
            ], limit=1)

        for line in self:
            if not line.product_id or not line.order_id.partner_id:
                continue

            policy = policy_by_company.get(line.order_id.company_id.id)
            if not policy:
                continue

            ctx = line._build_discount_context(policy)
            decision = compute_discount(ctx, policy.discount_pct)

            target_discount = decision.discount_pct if decision.apply_discount else 0.0
            if float_compare(
                line.discount,
                target_discount,
                precision_digits=6,
            ) == 0:
                continue

            line.with_context(skip_discount_policy=True).write({
                'discount': target_discount,
            })

    def _get_restricted_codes_cache(self):
        """Get cached restricted codes (EANs) for performance."""
        cache_key = '_discount_policy_restricted_codes'
        if not hasattr(self.env, cache_key):
            restricted_skus = self.env['sale.restricted.sku'].search([])
            setattr(self.env, cache_key, set(restricted_skus.mapped('ean')))
        return getattr(self.env, cache_key)

    def _build_discount_context(self, policy):
        """Build DiscountContext for engine computation."""
        allowed_partner_ids = policy.partner_ids.ids if policy.partner_ids else []
        allowed_warehouse_ids = policy.warehouse_ids.ids if policy.warehouse_ids else []
        partner_id = self.order_id.partner_id.id
        warehouse_id = self.order_id.warehouse_id.id if self.order_id.warehouse_id else 0
        product_tag_names = self.product_id.product_tmpl_id.product_tag_ids.mapped('name')

        # Collect all product codes (barcode + default_code) to match against restrictions
        product_codes = {c for c in {self.product_id.barcode, self.product_id.default_code} if c}

        # Use cached restricted codes for performance
        restricted_default_codes = self._get_restricted_codes_cache()

        return DiscountContext(
            partner_id=partner_id,
            allowed_partner_ids=allowed_partner_ids,
            warehouse_id=warehouse_id,
            allowed_warehouse_ids=allowed_warehouse_ids,
            product_tag_names=product_tag_names,
            restricted_default_codes=restricted_default_codes,
            product_codes=product_codes,
        )

    def _compute_discount_reason(self):
        """Compute and cache the discount decision reason."""
        if not self:
            return

        policy_by_company = {}
        for company in self.mapped('order_id.company_id'):
            policy_by_company[company.id] = self.env['sale.discount.policy'].search([
                ('active', '=', True),
                ('company_id', '=', company.id),
            ], limit=1)

        for line in self:
            policy = policy_by_company.get(line.order_id.company_id.id)
            if not policy:
                line.discount_reason = 'NO_POLICY'
                continue
            ctx = line._build_discount_context(policy)
            decision = compute_discount(ctx, policy.discount_pct)
            line.discount_reason = decision.reason

    @api.onchange('product_id', 'order_id')
    def _onchange_warn_discount_restricted(self):
        """Warn user when a restricted product is added to an eligible order."""
        policy = self._get_active_discount_policy()
        if not policy or not self.product_id:
            return

        ctx = self._build_discount_context(policy)
        decision = compute_discount(ctx, policy.discount_pct)

        if decision.reason in ('RESTRICTED_BRAND', 'RESTRICTED_SKU'):
            return {
                'warning': {
                    'title': _('Product Without Group Discount'),
                    'message': _(
                        'Product "%(product)s" belongs to a restricted brand or SKU list. '
                        'The %(discount)s%% discount does not apply.',
                        product=self.product_id.display_name,
                        discount=policy.discount_pct,
                    ),
                }
            }
