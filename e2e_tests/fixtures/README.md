# Fixtures requeridos / Required fixtures

Coloca aqui los 3 archivos antes de correr la suite. / Place the 3 files here before running the suite.

## 1. `valid_invoice.xml`
CFDI 4.0 valido y bien formado, con conceptos cuyo `NoIdentificacion` (Quifamesa)
o codigo de Addenda (Brudifarma) SI exista como `barcode` de un `product.product`
en la base de datos de destino. Nombra el archivo con el prefijo correcto para
que el parser detecte el proveedor automaticamente:
- Brudifarma: prefijo `2000_` (ej. `2000_2000201962_factura.xml`) — lotes van en el XML.
- Quifamesa: prefijo `QFM` (ej. `QFM861010BL0_Factura_001.xml`) — requiere tambien un PDF
  (sube el mismo archivo como `valid_invoice.pdf` en este directorio si vas a probar el flujo QUIFAMESA completo).

A valid, well-formed CFDI 4.0 file whose line items' `NoIdentificacion`
(Quifamesa) or Addenda code (Brudifarma) DOES match an existing `barcode` on
a `product.product` in the target database. Name the file with the correct
prefix so the parser auto-detects the supplier (see above).

## 2. `broken_invoice.xml`
Un archivo intencionalmente malformado: XML truncado, tags sin cerrar, o
bytes que no son XML valido en absoluto. El objetivo es forzar el path de
`CFDIParser().parse_bytes()` a fallar y ver si el wizard lo captura como
`UserError` limpio o si se filtra un Traceback/500 a la UI.

An intentionally malformed file: truncated XML, unclosed tags, or bytes that
are not valid XML at all. The goal is to force `CFDIParser().parse_bytes()`
to fail and observe whether the wizard turns it into a clean `UserError` or
leaks a raw Traceback/500 to the UI.

## 3. `unmapped_products.xml`
CFDI valido y bien formado, pero con al menos un concepto cuyo
`NoIdentificacion`/codigo de barras NO corresponde a ningun `product.product`
existente. Desde que `_auto_create_product` se agrego a
`purchase_invoice_import_wizard.py`, un codigo sin match YA NO deja
`product_id` vacio: crea dinamicamente un producto almacenable nuevo. La
linea debe quedar marcada `needs_review=True` (confianza 0.0 a proposito)
pero CON `product_id` asignado — fila en naranja (`text-warning`) en el
wizard, no en rojo (`text-danger`, esa combinacion es exclusiva de "sin
producto en absoluto"). El test que usa este fixture
(`test_purchase_parser_ui.spec.ts`) genera una copia con un codigo unico por
corrida (`withUniqueProductCode`) para que el producto auto-creado en una
corrida no "ensucie" la siguiente con un match limpio por `default_code`.

A valid, well-formed CFDI, but with at least one line item whose
`NoIdentificacion`/barcode does NOT match any existing `product.product`.
Since `_auto_create_product` was added to `purchase_invoice_import_wizard.py`,
an unmatched code no longer leaves `product_id` empty: it dynamically
creates a new storable product. The line must still be flagged
`needs_review=True` (confidence 0.0 on purpose) but WITH `product_id` set —
an orange row (`text-warning`) in the wizard, not red (`text-danger`, that
combination is exclusive to "no product at all"). The test that consumes
this fixture (`test_purchase_parser_ui.spec.ts`) generates a copy with a
unique code per run (`withUniqueProductCode`) so the auto-created product
from one run doesn't "pollute" the next with a clean `default_code` match.
