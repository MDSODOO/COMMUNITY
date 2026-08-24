# MARGINS_IMPROVEMENT_PLAN — sale_purchase_margins

**Fecha:** 2026-05-19 (revisión 2 — código v19.0.2.0.0)
**Módulo:** `sale_purchase_margins`
**Auditor:** Claude Sonnet 4.6 actuando como Odoo Financial Software Architect
**Alcance:** Análisis estático completo del código fuente actual. Sin modificación de código.

> Este documento reemplaza la versión anterior (rev 1 de 2026-05-19), que documentaba hallazgos
> sobre características que ya habían sido implementadas en el código.

---

## a) Resumen de la Arquitectura Actual

### Componentes principales

| Archivo | Responsabilidad |
|---|---|
| `models/margin_tools.py` | Núcleo matemático: conversión UoM, moneda y fecha. Función `get_standard_cost_for_line`. |
| `models/sale_order_line.py` | Campos `qfm_margin_pct` (editable, inverse) y `qfm_margin_abs` en `sale.order.line`. Reglas por línea comercial. |
| `models/purchase_order_line.py` | Campos `qfm_margin_pct` y `qfm_margin_abs` (solo lectura) en `purchase.order.line`. |
| `models/sale_margin_line_rule.py` | Modelo `qfm.sale.margin.line.rule`: reglas de margen por línea comercial + `company_id`. |
| `models/product_template.py` | `qfm_target_margin_pct` + precio sugerido + `action_apply_suggested_price`. |
| `models/product_product.py` | Bridge `action_apply_suggested_price` para validación de vistas Odoo 19. |
| `models/stock_picking.py` | Hook `write` → repricing automático de `list_price` al validar recepciones. |
| `models/res_company.py` | Campo `qfm_receipt_price_update_policy` (always_update / only_increase / manual_review). |

### Fórmulas activas (verificadas contra código)

**Margen de venta** (`sale_order_line.py:66`):
```
precio_neto = price_unit × (1 − discount/100)
qfm_margin_pct = (precio_neto − costo_std) / precio_neto × 100   [si precio_neto > 0]
qfm_margin_abs = (precio_neto − costo_std) × cantidad
```

**Diferencial de compra** (`purchase_order_line.py:59-63`):
```
margen_unitario = costo_std − precio_compra
qfm_margin_pct = margen_unitario / precio_compra × 100             [si precio_compra > 0]
qfm_margin_abs = margen_unitario × cantidad
```
> Positivo = compra por debajo del costo estándar (ahorro). Negativo = sobreprecio.

**Repricing en recepción** (`stock_picking.py:51`):
```
new_sale_price = purchase_cost / (1 − margin_objetivo/100)
```

### Protecciones ya implementadas (no requieren acción)

- División por cero en venta: `if precio_neto > 0` → `qfm_margin_pct = 0.0` ✅
- División por cero en compra: `if precio_compra > 0` ✅
- Margen objetivo negativo en inverse: `ValidationError` ✅
- Margen objetivo ≥ 100% en inverse: `ValidationError` ✅
- Costo estándar = 0 en inverse: `ValidationError` ✅
- Rango `qfm_target_margin_pct` en producto: `@api.constrains` [0, 100) ✅
- Conversión UoM y moneda con fecha de orden: `margin_tools.py` ✅
- `company_id` en reglas de margen por línea: `unique(company_id, line_key)` ✅
- Agregación por producto en repricing: `updates_by_template` dict ✅
- Política configurable por compañía: `qfm_receipt_price_update_policy` ✅
- Redondeo por moneda: `company_currency.round(new_sale_price)` ✅

---

## b) Hallazgos Críticos y Brechas de Lógica

### H1 — Repricing se activa en devoluciones de cliente (Severidad: **Alta**)

**Evidencia:** `models/stock_picking.py:17-20`

```python
incoming_becoming_done = self.filtered(
    lambda p: p.state != 'done' and p.picking_type_code == 'incoming'
)
```

En Odoo, `picking_type_code='incoming'` cubre **dos tipos de eventos distintos**:
1. ✅ Recepciones de proveedor (`purchase_id` presente)
2. ❌ Devoluciones de cliente (`purchase_id` ausente; la mercancía regresa del cliente al almacén)

Cuando un cliente devuelve mercancía y se valida la recepción, `_qfm_update_sale_prices` se
ejecuta. En ese caso, `move.purchase_line_id` es False, por lo que `_qfm_get_move_purchase_cost`
cae al fallback `move.price_unit` (que es el costo estándar del movimiento de stock). El resultado:
`list_price` se recalcula basado en el `standard_price` actual, **usando una devolución de cliente
como justificante de repricing**, lo cual es un error de negocio. No todas las devoluciones deben
disparar un cambio de precio de venta.

**Impacto:** Posible bajada/subida de precios de catálogo por eventos de devolución no relacionados
con negociación de compra.

---

### H2 — XSS potencial en mensajes HTML del chatter (Severidad: **Media**)

**Evidencia:** `models/stock_picking.py:148-163`

```python
picking_link = (
    f'<a href="/web#model=stock.picking&amp;id={self.id}">'
    f'{self.name}</a>'                         # ← sin escape()
)
...
f'<td ...>{product_tmpl.display_name}</td>'   # ← sin escape()
f'<td ...>{reason}</td>'                       # ← sin escape()
```

Los campos `self.name` (autogenerado, bajo riesgo) y `product_tmpl.display_name` (texto libre del
usuario) se insertan directamente en HTML sin pasar por `html.escape()`. Si el nombre del producto
contiene `<`, `>` o `&`, el HTML del chatter se rompe o puede inyectar contenido.

En la misma clase `purchase_invoice_parser` ya se usa `escape()` como práctica estándar. Este
módulo no sigue la misma convención.

---

### H3 — Constraint Python redundante en reglas de margen (Severidad: **Baja-Media**)

**Evidencia:** `models/sale_margin_line_rule.py:59-71`

```python
@api.constrains('line_key', 'company_id')
def _check_company_scoped_uniqueness(self):
    for rec in self.filtered(lambda r: r.line_key):
        duplicates = self.search_count([...])  # ← query extra en cada save
        if duplicates:
            raise ValidationError(...)
```

Este constraint ejecuta un `search_count` adicional en cada guardado de regla. El motivo de su
existencia es legítimo: en PostgreSQL, `UNIQUE(company_id, line_key)` no considera dos `NULL` como
iguales, por lo que la restricción SQL no captura duplicados cuando `company_id IS NULL`. Sin
embargo, la constraint Python solo necesita ejecutarse cuando `company_id` es vacío, no siempre.

**Impacto:** Query innecesaria cuando `company_id` está definido (caso más común). No es un bug,
pero añade latencia en alta frecuencia de edición.

---

### H4 — Semántica del "Margen Compra" es diferencial, no margen (Severidad: **Baja**)

**Evidencia:** `models/purchase_order_line.py:15-27`

El campo se llama `string='Margen Compra (%)'` pero la fórmula es:
`(costo_std - precio_compra) / precio_compra * 100`

Esta es una **variación de ahorro vs costo estándar**, no un margen comercial de compra
(que sería `(precio_venta - costo_compra) / precio_venta`). El `help=` sí explica la fórmula,
pero la etiqueta visible `Margen Compra (%)` puede inducir a error a usuarios financieros que
esperan la semántica estándar del término "margen".

Un valor positivo significa "se compró por debajo del costo estándar (ahorro)", lo opuesto a la
intuición habitual de "margen positivo = rentabilidad".

---

### H5 — `store=False` en todos los campos impide analítica histórica (Severidad: **Baja**)

**Evidencia:** `models/sale_order_line.py:23` y `models/purchase_order_line.py:17`

Todos los campos de margen son `store=False`. Esto significa:
- No hay snapshot del margen en el momento de confirmación del pedido.
- No se puede hacer pivot/graph view de márgenes históricos desde Odoo.
- No se puede hacer queries SQL directas sobre el margen de órdenes pasadas.

El margen recalcula en tiempo real con el `standard_price` actual, no con el costo vigente en el
momento de la venta.

**Impacto:** Analítica financiera limitada. Reporte "¿cuál fue el margen promedio de ventas en
febrero?" no es directamente soportable desde el ORM.

---

### H6 — O(n) `message_post` en el hook de repricing (Severidad: **Baja**)

**Evidencia:** `models/stock_picking.py:96-108`

```python
for candidate in updates_by_template.values():
    ...
    product_tmpl.sudo().message_post(body=..., subtype_xmlid='mail.mt_note')
```

Cada producto con margen objetivo en la recepción genera un `message_post` individual. Para
recepciones de 50+ SKUs con margenes configurados, esto implica 50+ inserts en `mail.message`
dentro de la misma transacción del `write`. No es un N+1 de consulta, sino un N de writes en el
camino crítico de validación de recepción.

---

### H7 — `ormcache` sin invalidación en cambios de campo Studio (Severidad: **Baja**)

**Evidencia:** `models/sale_order_line.py:86-106`

```python
@api.model
@tools.ormcache()
def _qfm_product_line_field_name(self):
    field_candidates = self.env['ir.model.fields'].sudo().search([...])
    ...
```

El caché `@tools.ormcache()` en un `@api.model` es por registro. Si un campo de tipo relación
con nombre/etiqueta "línea" es añadido/renombrado/eliminado en `product.template` via Studio,
el valor cacheado persiste hasta reinicio del servidor. Bajo riesgo en producción (Studio no
se usa en producción), pero puede causar comportamiento inesperado en desarrollo/staging donde
Studio sí se usa.

---

## c) Propuesta de Refactorización Matemática y de ORM

### C1 — Excluir devoluciones de cliente del repricing (para H1)

**Archivo:** `models/stock_picking.py:17`

Filtrar por presencia de `purchase_id` en el picking. Las recepciones de proveedor siempre tienen
`purchase_id`; las devoluciones de cliente no.

```python
# Antes
incoming_becoming_done = self.filtered(
    lambda p: p.state != 'done' and p.picking_type_code == 'incoming'
)
# Después
incoming_becoming_done = self.filtered(
    lambda p: (
        p.state != 'done'
        and p.picking_type_code == 'incoming'
        and p.purchase_id      # solo recepciones vinculadas a OC, no devoluciones
    )
)
```

Alternativa más defensiva: verificar también en `_qfm_get_move_purchase_cost` que existe
`purchase_line_id` antes de usar el fallback a `move.price_unit`.

---

### C2 — Agregar `escape()` en HTML del chatter (para H2)

**Archivo:** `models/stock_picking.py`

```python
from html import escape  # ya disponible en stdlib

# En _qfm_build_receipt_price_message:
picking_link = (
    f'<a href="/web#model=stock.picking&amp;id={self.id}">'
    f'{escape(self.name)}</a>'
)
...
f'<td ...>{escape(product_tmpl.display_name)}</td>'
f'<td ...>{escape(reason)}</td>'
```

---

### C3 — Optimizar constraint de unicidad global (para H3)

**Archivo:** `models/sale_margin_line_rule.py:59-71`

Ejecutar el `search_count` solo cuando `company_id` es False (caso que el SQL UNIQUE no cubre):

```python
@api.constrains('line_key', 'company_id')
def _check_company_scoped_uniqueness(self):
    for rec in self.filtered(lambda r: r.line_key and not r.company_id):
        duplicates = self.search_count([
            ('id', '!=', rec.id),
            ('line_key', '=', rec.line_key),
            ('company_id', '=', False),
        ])
        if duplicates:
            raise ValidationError(
                'Ya existe una regla global para esa línea de producto.'
            )
```

---

### C4 — Clarificar etiqueta en compras (para H4)

**Opción A (no-breaking, recomendada):** Enriquecer `help=` con advertencia de semántica.

**Opción B (breaking):** Renombrar:
- `string='Ahorro vs Costo Std (%)'` para `qfm_margin_pct`
- `string='Ahorro vs Costo Std (Importe)'` para `qfm_margin_abs`

Recomendación: Opción A primero; Opción B solo si Finanzas confirma que la etiqueta actual genera
confusión operativa.

---

### C5 — Snapshot de margen al confirmar (para H5)

Si el negocio requiere analítica histórica, añadir campos `store=True` en `sale.order.line`
que se populen en el `_action_confirm` del pedido:

```python
qfm_margin_pct_confirmed = fields.Float(
    string='Margen Confirmado (%)',
    store=True,
    readonly=True,
    digits=(16, 2),
)
```

Este es un cambio de esquema (requiere migración). Solo implementar si hay requerimiento explícito
de reporting histórico.

---

### C6 — Batch de `message_post` en repricing (para H6)

Postponer los `message_post` hasta después de todos los `write({'list_price': ...})`,
o limitarlos a cuando la política es `manual_review` (donde el mensaje de chatter es
el output principal). En `always_update` / `only_increase`, el chatter es informativo;
se puede batching con un único mensaje de resumen por recepción en lugar de uno por producto.

---

## d) Roadmap de Implementación

### Fase 1 — Correcciones de lógica de negocio (prioridad alta, ~1 día)

| # | Hallazgo | Acción | Archivo |
|---|---|---|---|
| 1 | H1 | Filtrar `purchase_id` en hook de repricing | `stock_picking.py:17-21` |
| 2 | H2 | Añadir `escape()` en HTML del chatter | `stock_picking.py:135-172` |
| 3 | Cobertura | Nuevo test: devolución de cliente NO debe ejecutar repricing | `tests/test_margin_computation.py` |

Estas tres acciones son mecánicas, no cambian la API ni el esquema.

---

### Fase 2 — Calidad de código (prioridad media, ~1 día)

| # | Hallazgo | Acción | Archivo |
|---|---|---|---|
| 4 | H3 | Optimizar constraint Python en reglas (solo para `company_id=False`) | `sale_margin_line_rule.py:59` |
| 5 | H4 | Opción A: mejorar `help=` en campo de margen de compra | `purchase_order_line.py:15-27` |
| 6 | H6 | Evaluar batch o resumen único de `message_post` en repricing | `stock_picking.py:96` |

---

### Fase 3 — Escalabilidad y analítica (prioridad baja, ~1 sprint, requiere decisión de negocio)

| # | Hallazgo | Acción |
|---|---|---|
| 7 | H5 | Definir si se requiere snapshot histórico de margen al confirmar pedidos |
| 8 | H5 | Si sí: añadir campos `store=True` + migración + vistas pivot/graph |
| 9 | H7 | Si se usa Studio: añadir mecanismo de invalidación de `ormcache` (raro en prod) |

---

## Criterios de Aceptación

- Devoluciones de cliente no generan cambio de precio de venta.
- HTML del chatter es seguro para nombres de producto con caracteres especiales.
- Constraint de reglas globales pasa solo cuando `company_id IS NULL`.
- Test de regresión cubre el nuevo comportamiento del hook de repricing.
- Ningún cambio de API pública (campos, métodos públicos) en Fase 1 y 2.

---

## Terminología

> Regla de negocio vigente: cualquier referencia a cantidades físicas de inventario o existencias
> debe decir **"A la mano"**. NUNCA "Disponible".
>
> Búsqueda en el módulo: ningún archivo usa las palabras "Disponible" ni "disponible" en contexto
> de inventario. ✅ Regla cumplida por el código actual.
