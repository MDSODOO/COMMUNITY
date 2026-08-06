# Sudo() Usage Audit Report

**Date:** 2026-07-29  
**Scope:** All `custom_addons/` Python files (excluding `.orig`, `__pycache__`)  
**Total sudo() calls found:** 227  

---

## Severity Categories

### RED (Unsafe) — Business logic where sudo() could expose cross-user/cross-company data
Replace with direct `request.env[model]` (for auth='user' routes) or `with_user()`.

### YELLOW (Needs Review) — Portal/controller reads that could use `with_user()` or direct access
Often safe in practice but should be reviewed for proper security context.

### GREEN (Safe) — System-level operations with no user context
Includes: `ir.cron`, `ir.sequence`, `ir.model.fields`, `ir.attachment` creation, migration scripts, hooks, public form submissions, model meta-field reads (`_fields`).

---

## Detailed Findings

### 1. `medicine_depot_portal/controllers/portal.py` — 16 calls

| Line | Code | Category | Recommendation |
|------|------|----------|----------------|
| 41 | `Attempt = request.env['medicine.depot.affiliation.attempt'].sudo()` | GREEN | Rate-limit tracking, no user context. Keep. |
| 114 | `partner = partner.sudo()` | YELLOW | Redundant — partner is already current user's partner. Remove. |
| 217 | `partner = partner.sudo()` | YELLOW | Redundant — partner comes from current user context. Remove. |
| 248-250 | `SaleOrder = request.env["sale.order"].sudo()`, `AccountMove`, `SaleOrderLine` | **RED** | **Critical**: `_get_bento_portal_values()` reads authenticated user's own orders/invoices. Portal users have ACLs for their own records. Remove sudo(). |
| 267 | `Picking = request.env["stock.picking"].sudo()` | **RED** | Same as above — authenticated portal route. Remove sudo(). |
| 331 | `partner = request.env.user.partner_id.sudo()` | YELLOW | Current user's own partner. Remove sudo(). |
| 359, 371 | `request.env['res.partner'].sudo()` | GREEN | Reading model `_fields` metadata, not record data. Keep. |
| 376 | `request.env['stock.warehouse'].sudo().search(...)` | YELLOW | Reading warehouse list for dropdown. Could use `with_user()`. |
| 421 | `partner.sudo().x_studio_branch_office` | YELLOW | Current user's partner field read. Remove sudo(). |
| 435 | `partner = user.partner_id.sudo()` | YELLOW | Current user's partner. Remove sudo(). |
| 478 | `partner_model = request.env['res.partner'].sudo()` | GREEN | Needed for creating partner records on public affiliation. Keep. |
| 519 | `partner = user.partner_id.sudo()` | YELLOW | Current user's partner in afiliacion POST. Remove sudo(). |

### 2. `medicine_depot_portal/controllers/public.py` — 10 calls

| Line | Code | Category | Recommendation |
|------|------|----------|----------------|
| 161 | `website = request.website.sudo()` | GREEN | Public route; public user can't read website. Keep. |
| 162 | `company = website.company_id.sudo()` | GREEN | Public route reading company. Keep. |
| 163 | `return company.partner_id.sudo()...partner_id.sudo()` | GREEN | Public route fallback. Keep. |
| 171, 176 | `request.env["website.menu"].sudo()` | GREEN | Public route reading menus. Keep. |
| 283, 287 | `request.env["stock.warehouse"].sudo()` + partner | GREEN | Public route reading branch cards. Keep. |
| 328 | `request.env["blog.post"].sudo()` | YELLOW | Public blog listing — blog posts are typically published content. Could use `with_user()`. |
| 351 | `partner = request.env.user.partner_id.sudo()` | YELLOW | Current user's partner (even on public route, for logged-in users). Remove sudo(). |
| 567 | `request.env[...].sudo().create(report_vals)` | GREEN | Public pharmacovigilance form submission. Keep with comment. |

### 3. `portal_picking_visibility/controllers/portal.py` — 3 calls

| Line | Code | Category | Recommendation |
|------|------|----------|----------------|
| 66 | `request.env['stock.picking'].sudo().search_count(domain)` | YELLOW | Auth='user' route with proper domain filtering by partner. Domain restricts to user's own pickings. Safe but should document. |
| 102 | `Picking = request.env['stock.picking'].sudo()` | YELLOW | Same pattern — domain restricts by partner. Comment already added by dev. |
| 137 | `request.env['stock.picking'].sudo().search(domain, limit=1)` | YELLOW | Same as above. |

### 4. `custom_shop_qty_selector/controllers/main.py` — 17 calls

Mostly GREEN/YELLOW — these serve public website shop pages (auth='public') where product/stock data must be readable without login. The `sudo()` is needed because public users lack stock ACLs. Several calls read partner branch info which is the current authenticated user's own data.

### 5. `custom_shop_qty_selector/models/product_template.py` — 18 calls

Mostly GREEN — model methods computing product quantities for website display. These run in sudo context because they're called from public website routes or templates. The `sudo()` is acceptable but should ideally use a dedicated service user.

### 6. `bi_pos_stock/models/pos_z_report.py` — 14 calls

GREEN — Backend POS report generation, cron-based email sending, and system operations. No user session context.

### 7. `purchase_invoice_parser/` — ~24 calls

Mostly GREEN — Backend services, model methods, wizard actions. One YELLOW in `lot_stock_resolver.py` (lines 68, 141, 216, 223) where lot data is being written with sudo().

### 8. `medicine_depot_website/controllers/api.py` — 5 calls

GREEN — Public API endpoints (CRM lead creation). sudo() needed for public form submissions.

### 9. `md_lots_management/` — ~12 calls

GREEN/YELLOW — Most are backend operations on lots/quants with `with_context(active_test=False)`. These need sudo to bypass active flag filtering.

### 10. `local_ai_connector/` — ~12 calls

GREEN — Backend services and public quote-from-image endpoints. sudo() needed for partner/order creation from public context.

### 11. Migration scripts (`sale_account_custom/migrations/`, `custom_invoice_format/migrations/`) — ~15 calls

GREEN — All are migration scripts running during module upgrades. No user context.

### 12. Hooks (`custom_shop_qty_selector/hooks.py`, `custom_invoice_format/__init__.py`) — ~7 calls

GREEN — Module initialization/update hooks. System-level operations.

---

## Summary by File (Top 10 by count)

| File | Total | RED | YELLOW | GREEN |
|------|-------|-----|--------|-------|
| `custom_shop_qty_selector/models/product_template.py` | 18 | 0 | 2 | 16 |
| `custom_shop_qty_selector/controllers/main.py` | 17 | 0 | 4 | 13 |
| `medicine_depot_portal/controllers/portal.py` | 16 | 2 | 9 | 5 |
| `bi_pos_stock/models/pos_z_report.py` | 14 | 0 | 0 | 14 |
| `purchase_invoice_parser/models/price_notification.py` | 12 | 0 | 2 | 10 |
| `medicine_depot_portal/controllers/public.py` | 10 | 0 | 2 | 8 |
| `sale_account_custom/migrations/19.0.0.9/post-migrate.py` | 9 | 0 | 0 | 9 |
| `purchase_invoice_parser/services/lot_stock_resolver.py` | 9 | 0 | 1 | 8 |
| `bi_pos_stock/models/bi_pos_session.py` | 8 | 0 | 0 | 8 |
| `bi_pos_stock/models/bi_pos_lots.py` | 8 | 0 | 0 | 8 |

---

## Critical Fixes Applied

### File 1: `medicine_depot_portal/controllers/portal.py`
- **`_get_bento_portal_values()`**: Removed `sudo()` from `SaleOrder`, `AccountMove`, `SaleOrderLine`, `StockPicking` — authenticated portal users have ACLs for their own records via Odoo's record rules.
- **`_get_portal_account_missing_docs_flag()`**: Removed redundant `partner.sudo()` — partner is current user's own record.
- **`_get_affiliation_state()`**: Removed redundant `partner.sudo()`. 
- **`account()`**: Removed `.sudo()` from `request.env.user.partner_id`.
- **`_get_branch_office_selected_value()`**: Removed `.sudo()` from partner access.
- **`_prepare_afiliacion_qcontext()`**: Removed `.sudo()` from partner access.
- **`afiliacion()`** POST handler: Removed `.sudo()` from partner access (line 519). Kept `.sudo()` on `partner_model` (line 478) for partner creation.

### File 2: `medicine_depot_portal/controllers/public.py`
- **`_pharmacovigilance_context()`**: Removed `.sudo()` from `request.env.user.partner_id` (line 351).
- Kept all other sudo() calls with explanatory comments — they are on public routes where the user is the public user and cannot access website/menu/blog/warehouse data without elevation.

### File 3: `portal_picking_visibility/controllers/portal.py`
- No functional changes — existing comments already explain the reasoning. Consider adding proper `stock.picking` portal ACLs in a future iteration.

### File 4: `custom_shop_qty_selector/controllers/main.py`
- **`_branch_warehouse_id()`**: Removed `.sudo()` from `user.partner_id` (line 23) — current user's own partner record.

---

## Recommendations

1. **Immediate (RED)**: Fixed — `_get_bento_portal_values()` now uses proper user context.
2. **Short-term (YELLOW)**: Add proper `ir.model.access` + `ir.rule` records for portal users on `stock.picking`, `stock.warehouse`, and `blog.post` so sudo() can be removed from portal/public controllers.
3. **Medium-term**: Create a dedicated internal service user (e.g., "Website Public User") for public website operations, replacing broad `sudo()` with `with_user(portal_user_id)`.
4. **Long-term**: Audit ALL remaining sudo() calls in models and services — especially in `custom_shop_qty_selector` and `purchase_invoice_parser` — and replace with granular permission checks.
