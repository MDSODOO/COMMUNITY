# Design: sale_discount_policy Module

## Overview

The `sale_discount_policy` module automates a 2% discount for customers in the "Farmacias Económicas" group, with intelligent exclusions for restricted brands and specific SKUs. The policy is scoped to specific warehouses (branches).

## Architecture Decisions

### 1. Hybrid Pricelist + Python Guard Model

**Choice:** Use a native `product.pricelist` (with global 2% discount) + Python logic in `_compute_discount()` to selectively clear the discount.

**Why:** Odoo's pricelist system cannot natively express "apply discount EXCEPT for tagged products." By keeping the pricelist as the single source of truth and using a Python guard layer, we get:
- Audit trail: The pricelist appears in Sales → Pricelist views
- Maintainability: No need to manually create/manage individual pricelist items per restricted product
- Consistency: POS inherits the pricelist naturally; only the Python/JS guard applies exceptions

**Alternative considered:** Pure `@api.onchange` override to set `discount` directly
- Downside: Bypasses pricelist audit trail, duplicates logic between Sales and POS

### 2. Product Tags for Restricted Brands

**Choice:** Use `product.tag` (many2many on `product.template`) with a `MARCA_RESTRINGIDA_` prefix.

**Why:**
- Zero schema migration: `product.tag` already exists in Odoo
- Scalable: Adding a new restricted brand is a data operation, not code
- Searchable/reportable: Users can filter products by tags in views
- Multiple tags per product: A product can belong to multiple restricted categories

**Alternative considered:** Custom Boolean field `is_discount_restricted`
- Downside: Requires schema migration; can't track which brand is restricted; less maintainable

### 3. Partner Category Scoping

**Choice:** `res.partner.category` tag called "Farmacias Económicas"

**Why:**
- Standard Odoo mechanism: Used widely across modules
- Applies to all linked entities: Legal entities (razones sociales) sharing the tag all get the discount
- Easy to manage: No custom models needed

### 4. Warehouse (Branch) Scoping

**Choice:** `stock.warehouse` on the `sale.discount.policy` model

**Why:**
- Consistent with existing modules: `sale_stock_availability`, `bi_pos_stock` use warehouse as the branch primitive
- Avoids multi-company complexity: `res.company` is a security boundary, not a discount boundary
- Flexible: Empty warehouse list = apply to all branches; configured list restricts to specific branches

### 5. Pure Python Engine

**Choice:** Dataclass-based `DiscountContext` and `compute_discount()` function with no ORM dependencies

**Why:**
- Testable: Unit tests run without database
- Reusable: Can be called from Sales, POS, reports, or future integrations
- Clean separation: ORM layer builds context; engine makes decisions; UI/server applies decisions

## Data Model

### Models Created

#### `sale.discount.policy`
Configuration record (one per company). Fields:
- `name` (Char): Policy description
- `active` (Bool): Enable/disable the policy
- `discount_pct` (Float): Discount percentage (default 2.0)
- `partner_category_id` (Many2one to `res.partner.category`): The customer group
- `warehouse_ids` (Many2many to `stock.warehouse`): Authorized branches (empty = all)
- `pricelist_id` (Many2one to `product.pricelist`): Associated pricelist
- `company_id` (Many2one to `res.company`): Multi-company scope

#### `product.template` (inherited)
New computed field:
- `is_discount_restricted` (Bool, stored): True if product has a `MARCA_RESTRINGIDA_*` tag

#### `sale.order.line` (inherited)
New field:
- `discount_reason` (Char, computed, not stored): Why discount was/wasn't applied (APPLIED, WRONG_GROUP, WRONG_BRANCH, RESTRICTED_BRAND, RESTRICTED_SKU, NO_POLICY)

#### `pos.order.line` (inherited)
New field:
- `discount_policy_reason` (Char): Server-side record of why discount was cleared

### Data Records

**Pricelist:**
- `product.pricelist`: "Farmacias Económicas — 2%"
- `product.pricelist.item`: Global 2% discount rule

**Tags:**
- 22 × `product.tag` with names `MARCA_RESTRINGIDA_*` (Abbott, Armstrong, Bayer, etc.)

**Category:**
- `res.partner.category`: "Farmacias Económicas"

**Policy:**
- `sale.discount.policy`: Default configuration record

## Computation Flow

### Sales Backend (`sale_order_line._compute_discount`)

1. Call parent class `_compute_discount()` → Pricelist computes initial discount
2. Get active policy for the company
3. Build `DiscountContext` from order + product data
4. Call `compute_discount(ctx, policy.discount_pct)` → Returns `DiscountDecision`
5. If `decision.apply_discount == False`: Set `line.discount = 0.0`
6. Else: Keep the pricelist-computed discount

### POS Frontend (`discount_policy_patch.js`)

1. JS patch on `OrderLine.get_discount()`: Check product tags and partner category
2. If restricted brand AND partner is Farmacias Económicas: Return 0
3. Else: Return the pricelist-computed discount
4. On product add: Show warning if restricted

### POS Backend (`pos_order_line.create`)

Safety net: Clear discount server-side if restrictions apply (in case JS patch is bypassed)

## Discount Engine Logic

```
if partner NOT in required_category:
  return WRONG_GROUP, no discount

if warehouse NOT in allowed list (and list is not empty):
  return WRONG_BRANCH, no discount

if product has MARCA_RESTRINGIDA_* tag:
  return RESTRICTED_BRAND, no discount

if product SKU in restricted_default_codes set:
  return RESTRICTED_SKU, no discount

return APPLIED, apply discount
```

## Restricted Brands (22)

Abbott, Armstrong, Bayer, Broncolin, Chinoin, Colgate, Cosbel, Genomma, Glaxo, Grin, Grisi, Grupo BIC, Electrolit, Electrolife, Kimberly, Pfizer, Procter, Sanfer, Sanofi, Senosiain, Sophia, Unilever

Each gets a `product.tag` named `MARCA_RESTRINGIDA_<BRAND>` in UPPERCASE with underscores replacing spaces.

## Restricted Product SKUs

Handled via:
1. `restricted.product.import` wizard: Upload CSV with one SKU per line
2. Wizard tags matching products with `SKU_RESTRINGIDO`
3. Engine checks `product.default_code` against `restricted_default_codes` set

Future: Could be stored in a dedicated `sale.restricted.product` model for better auditability.

## Testing

- `test_discount_engine.py`: Pure Python unit tests (no ORM) for all decision paths
- `test_sale_order_discount.py`: Integration tests with ORM (sale order, partner, warehouse, product)
- Manual scenarios: Happy path, brand restriction, SKU restriction, group check, warehouse check

## Future Extensions

1. **Task 2:** On-change warning in POS, on-screen alerts
2. **Task 3:** Verification report comparing manual vs automated calculations
3. **SKU-level restrictions:** Store restricted SKU list in a dedicated model for better UX
4. **Audit trail:** Log all discount decisions (no discount applied, reason, etc.)
5. **Multiple policies:** Support multiple discount policies per company (currently unique per company)
