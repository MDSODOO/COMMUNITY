# pos_order_transfer — v19.0.1.0.0

**Categoría**: Point of Sale | **Licencia**: LGPL-3

## Propósito

Permite a un empleado del POS ceder o transferir un pedido en borrador a otro empleado de la misma sesión. Útil en entornos con múltiples cajeros compartiendo una terminal.

## Dependencias

```python
depends = ['pos_hr']
```

## Arquitectura

Módulo puramente frontend (OWL/JS). No modifica modelos de la base de datos.

## Componentes OWL

| Archivo | Componente |
|---|---|
| `static/src/xml/order_transfer_popup.xml` | Popup de selección de empleado destino |
| `static/src/xml/actionpad.xml` | Extensión del ActionPad con botón "Ceder pedido" |
| `static/src/js/` | Lógica del popup y la transferencia |

## Flujo de uso

1. El cajero A tiene un pedido en borrador
2. Hace clic en **Ceder pedido** en el ActionPad
3. Selecciona al cajero B en el popup
4. El pedido queda asignado a cajero B en la misma sesión

## Notas técnicas

- Requiere `pos_hr` para el manejo de empleados en sesión POS
- No genera movimientos de inventario — solo reasigna la referencia de empleado en el pedido
- Compatible con sesiones POS multi-empleado (Odoo 19 estándar)

[⏳ MÓDULO(S) ACTUALIZADO(S)/AUDITADO(S) EN ESTE PASO: pos_order_transfer]
