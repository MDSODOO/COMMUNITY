# purchase_vendor_ref — v19.0.1.0.0

**Categoría**: Purchase | **Licencia**: LGPL-3

## Propósito

Propaga automáticamente la referencia del proveedor (`partner_ref`) de la Orden de Compra al campo `ref` y `payment_reference` de la factura de proveedor generada. Elimina la necesidad de ingresar manualmente la referencia en la factura.

## Dependencias

```python
depends = ['purchase']
```

## Modelos

### `purchase.order` (extensión)

Sobreescribe `_create_invoices()` para copiar `partner_ref` de la OC a los campos correspondientes de la factura.

```python
# Al generar la factura desde una OC:
invoice.ref = purchase_order.partner_ref
invoice.payment_reference = purchase_order.partner_ref
```

## Notas técnicas

- Módulo simple y focalizado — sin vistas, sin wizards, sin datos
- La propagación solo ocurre si `partner_ref` está poblado en la OC
- No sobreescribe si la factura ya tiene una referencia preexistente (evita pérdida de datos)

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: purchase_vendor_ref]
