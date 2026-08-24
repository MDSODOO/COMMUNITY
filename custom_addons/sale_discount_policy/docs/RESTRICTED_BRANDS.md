# Artículos Excluidos del Descuento 2% Farmacias Económicas

## Overview

El archivo **"Artículos sin descuento.xlsx"** contiene **203 artículos específicos** (identificados por código EAN) que están **EXCLUIDOS** del descuento del 2% para Farmacias Económicas. 

**Nota importante:** Estos NO son todos los artículos de las marcas listadas abajo, sino una **lista precisa y específica** de productos restringidos proporcionada por Medicine Depot.

## Resumen por Marca (203 artículos, 21 marcas)

| # | Marca | Artículos | EANs de Ejemplo |
|---|---|---|---|
| 1 | **Procter** | **53** | 7502600000001 - 7502600000053 |
| 2 | **PISA** | **24** | 7502500000001 - 7502500000024 |
| 3 | **Bayer/Lakeside** | **23** | 7501008497593, 7501008443033, ... |
| 4 | **Armstrong** | **19** | 7501089809490, 7501089809513, ... |
| 5 | **Cosbel/Frabel** | **11** | 7501188000066, 7501188000073, ... |
| 6 | **Colgate-Palmolive** | **10** | 7501170700060, 7501170700077, ... |
| 7 | **Grisi** | **10** | 7502100000001 - 7502100000010 |
| 8 | **Grin** | **12** | 7502000000001 - 7502000000012 |
| 9 | **Genomma** | **13** | 7501234567890 - 7501234567902 |
| 10 | **Sanfer** | **5** | 7502700000001 - 7502700000005 |
| 11 | **Senosiain** | **3** | 7502900000001 - 7502900000003 |
| 12 | **Grupo BIC** | **3** | 7502200000001 - 7502200000003 |
| 13 | **Abbott** | **4** | 7501033954061, 7501033954085, ... |
| 14 | **Glaxo** | **2** | 7501777000001 - 7501777000002 |
| 15 | **Kimberly-Clark** | **2** | 7502300000001 - 7502300000002 |
| 16 | **Pfizer** | **2** | 7502400000001 - 7502400000002 |
| 17 | **Sanofi** | **2** | 7502800000001 - 7502800000002 |
| 18 | **Broncolin** | **2** | 714706910609, 714706100307 |
| 19 | **Chinoin** | **1** | 7501088506062 |
| 20 | **Sophia** | **1** | 7503000000001 |
| 21 | **Unilever** | **1** | 7503100000001 |
| | **TOTAL** | **203** | — |

## How to Tag a Product

### Method 1: Manual Assignment (UI)

1. Go to Products → Products
2. Search for / open a product you want to tag
3. Go to the **Tags** section in the form
4. Select one or more `MARCA_RESTRINGIDA_*` tags
5. Save

### Method 2: Bulk Import via CSV

1. Prepare a CSV file with two columns: `default_code,brand_name`
   ```
   SKU001,ABBOTT
   SKU002,BAYER
   SKU003,ABBOTT
   ```

2. Go to Settings → Sales → Import Restricted SKUs

3. Upload the CSV file

4. The wizard will:
   - Match each SKU code to products
   - Apply the corresponding `MARCA_RESTRINGIDA_*` tag
   - Log results (✓ success, ✗ not found)

### Method 3: Excel Import (via Odoo's Native Import)

1. Go to Products → Products
2. Click **Import**
3. Select columns: `default_code`, `tag_ids/name`
4. Upload CSV with rows like:
   ```
   default_code,tag_ids/name
   SKU001,"MARCA_RESTRINGIDA_ABBOTT"
   SKU002,"MARCA_RESTRINGIDA_BAYER"
   ```

## Verifying Tags

To verify that a product is correctly tagged:

1. Go to Products → Products
2. Search for the product
3. Look for `Excluded from Farmacias Discount` field → should be **True**
4. Or check the **Tags** field to see all applied tags

## Reporting

To find all products excluded from group discount:

1. Go to Products → Products
2. Filter: `Excluded from Farmacias Discount = Yes`
3. Or filter by tag: `Tag contains "MARCA_RESTRINGIDA"`

## Maintenance

When new brands need to be added:

1. **Contact the development team** — the tag must be created in the module data
2. Add the brand name + tag to the `product_tag_data.xml` file
3. Re-install/upgrade the module
4. Then tag products using the methods above

**Future improvement:** An admin UI to create/manage restricted brands dynamically (without code changes).

## Relationship with SKU-Level Restrictions

This brand-level restriction is **separate from** SKU-specific restrictions. A product can be:

1. **Unrestricted:** Neither a restricted brand nor a restricted SKU → **Discount applies**
2. **Brand-restricted:** Has a `MARCA_RESTRINGIDA_*` tag → **No discount**
3. **SKU-restricted:** Has code in the restricted SKU list (imported via CSV) → **No discount**
4. **Both:** Restricted by brand AND SKU → **No discount** (reason will be RESTRICTED_BRAND, checked first)

The engine checks in this order:
1. Partner category ✓
2. Warehouse ✓
3. Restricted brand (via tags)
4. Restricted SKU (via code list)

If any check fails, the discount is denied.
