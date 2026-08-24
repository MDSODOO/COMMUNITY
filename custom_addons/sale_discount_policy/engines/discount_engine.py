"""Pure Python discount computation engine (no ORM dependencies)."""
from __future__ import annotations
from dataclasses import dataclass


RESTRICTED_BRAND_PREFIX = "MARCA_RESTRINGIDA_"


@dataclass
class DiscountContext:
    """Input context for discount computation."""
    partner_id: int                      # ID of the order partner
    allowed_partner_ids: list[int]       # Partner IDs allowed by policy
    warehouse_id: int                    # Warehouse ID of the order
    allowed_warehouse_ids: list[int]    # Warehouse IDs allowed by policy (empty = all allowed)
    product_tag_names: list[str]        # All tag names on the product
    restricted_default_codes: set[str]  # Set of restricted SKU codes (EAN/barcode/default_code)
    product_codes: set[str]             # Set of all product codes (barcode + default_code)


@dataclass
class DiscountDecision:
    """Discount computation result."""
    apply_discount: bool    # Whether the discount should be applied
    discount_pct: float     # Discount percentage (only valid if apply_discount=True)
    reason: str             # Reason code: 'APPLIED' | 'WRONG_GROUP' | 'WRONG_BRANCH' | 'RESTRICTED_BRAND' | 'RESTRICTED_SKU'


def compute_discount(ctx: DiscountContext, discount_pct: float) -> DiscountDecision:
    """
    Determine if a discount should apply to an order line.

    Args:
        ctx: Discount context with partner, warehouse, product, and policy info
        discount_pct: Policy discount percentage (e.g., 2.0)

    Returns:
        DiscountDecision with apply_discount flag and reason
    """
    # Check 1: Partner must be in the allowed list
    if ctx.partner_id not in ctx.allowed_partner_ids:
        return DiscountDecision(False, 0.0, 'WRONG_GROUP')

    # Check 2: Warehouse must be in allowed list (if policy specifies any)
    if ctx.allowed_warehouse_ids and ctx.warehouse_id not in ctx.allowed_warehouse_ids:
        return DiscountDecision(False, 0.0, 'WRONG_BRANCH')

    # Check 3: Product must not have a restricted brand tag
    for tag_name in ctx.product_tag_names:
        if tag_name.startswith(RESTRICTED_BRAND_PREFIX):
            return DiscountDecision(False, 0.0, 'RESTRICTED_BRAND')

    # Check 4: Product codes must not intersect with restricted codes list
    if ctx.product_codes and ctx.product_codes & ctx.restricted_default_codes:
        return DiscountDecision(False, 0.0, 'RESTRICTED_SKU')

    # All checks passed: apply the discount
    return DiscountDecision(True, discount_pct, 'APPLIED')
