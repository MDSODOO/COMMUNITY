# Installation & Setup Guide

## Pre-Installation Requirements

Before installing the module, gather:

1. **Farmacias Económicas customers list**
   - Partner names or VAT numbers
   - Any associated legal entities / razones sociales

2. **Product catalog with brand mapping**
   - CSV or Excel with `default_code` + brand name columns
   - Used to assign `MARCA_RESTRINGIDA_*` tags to products

3. **Warehouse information for authorized branches**
   - Names or IDs of Cancún and Playa del Carmen warehouses in your Odoo instance
   - These will be configured on the policy record

4. **Restricted product SKU list (optional for MVP)**
   - CSV with one SKU code per line
   - Imported later via the wizard if needed

## Installation Steps

### Step 1: Install the Module

```bash
odoo -d <database_name> -i sale_discount_policy --no-http
```

Or via the Odoo UI:
1. Apps → Search: "sale_discount_policy"
2. Click **Install**

The module will create:
- `sale.discount.policy` model
- 22 `product.tag` records (MARCA_RESTRINGIDA_*)
- 1 `res.partner.category` (Farmacias Económicas)
- 1 `product.pricelist` (Farmacias Económicas — 2%)
- 1 default `sale.discount.policy` configuration record

### Step 2: Configure the Policy Record

1. Go to **Settings → Sales → Discount Policy**
2. Open the default policy: **"Política 2% Farmacias Económicas"**
3. In the **Scope** section:
   - `Authorized Branches`: Select **Cancún** and **Playa del Carmen** warehouses
   - Leave other fields as-is (partner_category and pricelist are pre-configured)
4. Save

**Note:** If you don't see the warehouses, create them first:
- Go to Inventory → Warehouses
- Create warehouse records with names "Cancún" and "Playa del Carmen"
- Then return to the policy and select them

### Step 3: Assign Customers to Farmacias Económicas Group

1. Go to **CRM / Sales → Customers**
2. For each Farmacias Económicas partner (and linked razones sociales):
   - Open the partner form
   - Go to the **Tags** section
   - Select: **"Farmacias Económicas"**
   - Save

**Bulk assignment (faster):**
- Prepare a CSV with columns: `name,category_id/name` (or `vat,category_id/name`)
  ```
  Farmacia A,Farmacias Económicas
  Farmacia B,Farmacias Económicas
  Farmacia C,Farmacias Económicas
  ```
- Go to Customers
- Click **Import**
- Upload the CSV
- Match columns and import

### Step 4: Import 203 Restricted Articles by EAN (Critical)

⚠️ **This is the most important step.** The system must know exactly which 203 products are excluded from the 2% discount.

#### Option A: Import via CSV Wizard (Recommended)

1. Get the file: `sale_discount_policy/docs/ARTICULOS_SIN_DESCUENTO.csv`
   - Contains: `ean,marca,nombre` (203 rows)
   - Source: "Artículos sin descuento.xlsx"

2. Go to **Settings → Sales → Import Restricted SKUs**

3. Select the CSV file and click **Import**

4. The wizard will:
   - Match each EAN to an existing product in your catalog
   - Tag matching products with `SKU_RESTRINGIDO_EAN`
   - Show results: ✓ found, ✗ not found

5. **Check the results carefully:**
   - If many products are not found, verify that your product records have the EAN code in the `barcode` or `default_code` field
   - You may need to first import the EAN codes into your product catalog if they're not there yet

#### Option B: Native Odoo Product Import (If products already have EAN)

1. Ensure your product records have the EAN stored in the `barcode` field
2. Go to **Products → Products**
3. Click **Import Records**
4. Use `ARTICULOS_SIN_DESCUENTO.csv` and map:
   - `ean` → `barcode`
   - `nombre` → (skip or use for validation)
   - Tag all rows with `SKU_RESTRINGIDO_EAN`
5. Upload and import

#### Step 4b (Optional): Fallback Brand Restrictions

After importing the 203 specific products, you may optionally tag products by brand as a fallback:

1. For each product from Abbott, Bayer, Procter, etc. that's NOT in the 203-product list (optional):
   - Manually tag with `MARCA_RESTRINGIDA_<BRAND>` (example: `MARCA_RESTRINGIDA_ABBOTT`)
   - Or use bulk import below

2. Bulk import brands (optional, for additional brand-level restrictions):
   ```
   default_code,tag_ids/name
   ABBOTT_OTHER_001,MARCA_RESTRINGIDA_ABBOTT
   BAYER_OTHER_001,MARCA_RESTRINGIDA_BAYER
   ```
3. Go to Products → **Import Records** and upload the CSV

## Verification

After setup, verify the configuration:

### Test 1: Check Policy Configuration

1. Go to **Settings → Sales → Discount Policy**
2. Confirm that `Authorized Branches` includes Cancún and Playa del Carmen
3. Confirm `Partner Category` is set to "Farmacias Económicas"
4. Confirm `Pricelist` is "Farmacias Económicas — 2%"

### Test 2: Create a Test Sale Order

1. Go to **Sales → Orders**
2. Click **Create**
3. **Customer:** Select a Farmacias Económicas partner
4. **Warehouse:** Cancún
5. **Product:** A non-restricted product (e.g., generic pharmaceutical, no MARCA_RESTRINGIDA_* tag)
6. **Quantity:** 1, **Price:** 100
7. Press **Tab** after entering the price
8. **Expected:** `Discount` field should show **2.0%**
9. Save the order

### Test 3: Restricted Product Warning

1. Create a new sale order (same as Test 2)
2. **Product:** Select a product tagged with `MARCA_RESTRINGIDA_BAYER` or similar
3. After selecting the product, **a warning should appear** saying:
   > "Product is excluded from Farmacias Discount"
4. **Expected:** `Discount` field should be **0%** (no discount)
5. Save the order

### Test 4: Wrong Customer (No Discount)

1. Create a new sale order
2. **Customer:** Select a regular customer (NOT in Farmacias Económicas)
3. **Warehouse:** Cancún
4. **Product:** Generic product (no restricted tag)
5. **Expected:** `Discount` field should be **0%**

### Test 5: Wrong Warehouse (No Discount)

1. Create a new sale order
2. **Customer:** Farmacias Económicas partner
3. **Warehouse:** A warehouse other than Cancún or Playa del Carmen (e.g., "Mexico City")
4. **Product:** Generic product
5. **Expected:** `Discount` field should be **0%**

### Test 6: POS Session

1. Go to **POS → POS Configuration**
2. Open a POS config (e.g., Cancún branch)
3. **Start Session**
4. **Customer:** Select a Farmacias Económicas partner
5. **Add product:** Generic item → **Discount should be 2%** in the receipt preview
6. **Add product:** Bayer-tagged item → **Alert should appear**, discount should be 0%

## Troubleshooting

### Issue: Discount not applying to Farmacias Económicas order

**Check:**
1. Is the policy record active? (Settings → Sales → Discount Policy → `active = Yes`)
2. Is the customer tagged with "Farmacias Económicas"? (CRM → Customers → Tags)
3. Is the warehouse in the `Authorized Branches` list on the policy?
4. Does the product have a restricted brand tag? (Products → Tags)

### Issue: No warning when adding restricted product

**Check:**
1. Is the product correctly tagged with `MARCA_RESTRINGIDA_*`?
   - Go to Products, open the product, check `Excluded from Farmacias Discount` field
2. Is the customer in the Farmacias Económicas group?
3. Is the policy active?

### Issue: Import Restricted SKUs wizard not working

**Check:**
1. CSV format: One SKU code per line, no header row
2. SKU codes match the `default_code` field exactly (case-sensitive)
3. File encoding is UTF-8
4. You have permission to create/edit product tags and products

### Issue: Pricelist not showing in form

**Check:**
1. Has the module completed installation? (Apps → Check module status)
2. Refresh the browser (Ctrl+F5)
3. If still missing, the pricelist may not have been created — re-install the module

## Post-Installation Checks

Run these to verify everything is in place:

```python
# In Odoo Console (bin/odoo shell):
from odoo import SUPERUSER_ID

# Check policy exists
policies = env['sale.discount.policy'].search([])
print(f"Policies: {len(policies)}")

# Check tags exist
tags = env['product.tag'].search([('name', 'like', 'MARCA_RESTRINGIDA')])
print(f"Restricted brand tags: {len(tags)}")

# Check partner category exists
categories = env['res.partner.category'].search([('name', '=', 'Farmacias Económicas')])
print(f"Partner categories: {len(categories)}")

# Check pricelist exists
pricelists = env['product.pricelist'].search([('name', 'like', 'Farmacias')])
print(f"Pricelists: {len(pricelists)}")
```

## Support & Maintenance

For questions or issues:
1. Check the **DESIGN.md** document for architecture details
2. Check the **RESTRICTED_BRANDS.md** for brand tagging instructions
3. Review test cases in `tests/` folder for usage examples
4. Contact the development team for bugs or feature requests

## Next Steps

- **Task 2:** Implement on-screen warnings and alerts in POS
- **Task 3:** Set up verification report comparing manual vs automated calculations
- **Data Maintenance:** Keep the restricted brand and SKU lists up-to-date as business rules change
