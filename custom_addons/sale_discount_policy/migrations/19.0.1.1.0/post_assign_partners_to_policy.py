from odoo import api
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Ensure discount policy is properly configured with Farmacias Económicas customer."""
    env = api.Environment(cr, 1, {})

    _logger.info("🔧 Starting discount policy configuration migration...")

    # Step 1: Find or create the discount policy
    policy = env['sale.discount.policy'].search([
        ('name', '=', 'Política 2% Farmacias Económicas'),
    ], limit=1)

    if not policy:
        _logger.info("  Creating new discount policy...")
        policy = env['sale.discount.policy'].create({
            'name': 'Política 2% Farmacias Económicas',
            'discount_pct': 2.0,
            'active': True,
        })
    else:
        _logger.info(f"  Found existing policy: {policy.name}")

    # Step 2: Find Farmacias Económicas customer
    _logger.info("  Searching for Farmacias Económicas customer...")
    customer = env['res.partner'].search([
        ('name', 'ilike', 'FARMACIAS ECONOMICAS DE OCCIDENTE'),
    ], limit=1)

    if not customer:
        _logger.warning("  ⚠️  Customer 'FARMACIAS ECONOMICAS DE OCCIDENTE' not found")
        _logger.info("  Available customers (first 5):")
        for c in env['res.partner'].search([], limit=5):
            _logger.info(f"    - {c.name} (ID: {c.id})")
    else:
        _logger.info(f"  ✅ Found customer: {customer.name} (ID: {customer.id})")

        # Step 3: Assign customer to policy
        if customer not in policy.partner_ids:
            _logger.info("  Assigning customer to policy...")
            policy.partner_ids = [(4, customer.id)]
        else:
            _logger.info("  Customer already in policy")

    # Step 4: Verify configuration
    _logger.info("  ✅ Migration complete")
    _logger.info(f"     Policy: {policy.name}")
    _logger.info(f"     Discount: {policy.discount_pct}%")
    _logger.info(f"     Partners: {policy.partner_ids.mapped('name')}")

    env.cr.commit()
