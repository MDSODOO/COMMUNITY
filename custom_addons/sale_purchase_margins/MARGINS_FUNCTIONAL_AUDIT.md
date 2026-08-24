# Auditoría Funcional Integral — `sale_purchase_margins`

**Fecha:** 2026-05-18
**Auditor:** Claude (Opus 4.7) actuando como QA + Arquitecto Odoo
**Alcance:** Lógica de cálculo de márgenes, integridad matemática, vistas y casos borde.
**Versión auditada:** 19.0.1.0.0 (rama `test`)

> Reporte de evaluación, **sin modificar código fuente**. Propuestas de refactor incluidas para aprobación al final.

---

## 1. Estado de las fórmulas matemáticas

### 1.1 `sale.order.line._compute_qfm_sale_margin` — ✅ Correcto con observaciones

```python
precio_venta = price_unit * (1 - discount/100)
qfm_margin_pct = (precio_venta - costo) / precio_venta * 100
qfm_margin_abs = (precio_venta - costo) * cantidad
```

| Aspecto | Veredicto |
|---|---|
| Fórmula (margen comercial sobre precio neto) | ✅ Correcta |
| División por cero en `qfm_margin_pct` | ✅ Protegida (`if precio_venta > 0`) |
| Clamp del descuento `[0,100]` | ✅ Aplica `min/max` |
| Cantidad nula → `qfm_margin_abs = 0` | ✅ Seguro |
| Conversión UoM y currency en `get_standard_cost_for_line` | ✅ Implementada |
| `try/except` no enmascara `UserError/ValidationError` | ✅ Bien diseñado |

**Observación 1 (semántica, no bug):** Cuando `precio_venta == 0` y `costo > 0`, el porcentaje queda en `0%` mientras el importe queda en `-costo*cantidad`. Es coherente con el test `test_sale_margin_zero_price_is_safe`, pero el usuario verá *0% de margen* con *importe negativo*, lo cual es confuso. Matemáticamente el ratio es indefinido; conviene **al menos documentarlo en el tooltip**.

### 1.2 `purchase.order.line._compute_qfm_purchase_margin` — ⚠️ Fórmula correcta pero **etiqueta engañosa**

```python
margen_unitario = costo_estandar - precio_compra
qfm_margin_pct = margen_unitario / precio_compra * 100
qfm_margin_abs = margen_unitario * cantidad
```

| Aspecto | Veredicto |
|---|---|
| División por cero | ✅ Protegida (`if precio_compra > 0`) |
| Cálculo "ahorro vs costo estándar" | ✅ Operativamente correcto |
| Etiqueta `Margen Compra (%)` | ⚠️ Semánticamente discutible |

**Hallazgo 2 (terminología):** lo etiquetado como "Margen Compra" **no es margen contable**, es un **diferencial vs. costo estándar** (ahorro/sobreprecio). Cuando `price_unit < standard_price` sale positivo, lo cual sugiere "compra barata". Si el equipo de compras espera el término "margen" con la semántica de venta, se prestará a malinterpretaciones. **Sugerencia:** renombrar a `Ahorro vs Costo Std (%)` o agregar `help=` explicando la fórmula.

### 1.3 `_qfm_apply_target_margin_to_price_unit` (inverse) — ⚠️ Falta validación

```python
precio_venta_neto = costo_unitario / (1 - margen_objetivo/100)
precio_unitario_nuevo = precio_venta_neto / factor_descuento
```

| Aspecto | Veredicto |
|---|---|
| `margen_objetivo >= 100` | ✅ `ValidationError` |
| `descuento == 100` (factor=0) | ✅ `ValidationError` |
| `margen_objetivo < 0` (margen negativo objetivo) | ❌ **NO validado** |
| `costo_unitario == 0` → `precio_unitario_nuevo == 0` | ❌ **Silenciosamente fija precio en 0** |

**Hallazgo 3 (bug lógico crítico):** Si el producto no tiene `standard_price` configurado y el usuario fija un margen objetivo, el precio unitario se reescribe a `0`. Esto puede provocar **ventas a precio cero sin alerta**. Debe validarse `costo_unitario > 0` antes de aplicar el inverse, o avisar al usuario.

**Hallazgo 4 (validación faltante):** No se rechaza `margen_objetivo < 0`. Un usuario que escriba `-10%` obtendrá un precio **inferior al costo** sin advertencia. La advertencia onchange `_onchange_qfm_margin_warning` aparece después, pero el inverse permite la operación.

### 1.4 `stock_picking._qfm_update_sale_prices` — ✅ Conservador

```python
new_sale_price = purchase_cost / (1 - margin/100)
```

| Aspecto | Veredicto |
|---|---|
| `purchase_cost <= 0` | ✅ Skip |
| `margin <= 0 or margin >= 100` | ✅ Skip |
| Recepciones de devolución (negativas) | ⚠️ No diferencia; `move.purchase_line_id` puede pertenecer a devolución |
| Multi-currency en `convert_unit_price` | ✅ Conversión a moneda de compañía |
| Sobrescritura silenciosa de `list_price` | ⚠️ No avisa si el nuevo precio es **menor** que el anterior |

**Hallazgo 5 (riesgo de negocio):** Cuando una recepción trae un costo menor que el histórico, el `list_price` **baja automáticamente** sin confirmación. En negocio farmacéutico esto puede destruir margen acumulado en inventario previo (FIFO real vs. costo de la última compra). **Sugerencia:** considerar política `only_increase` o `requiere_aprobacion` configurable a nivel compañía.

### 1.5 `product_template._compute_qfm_suggested_list_price` — ✅ Correcto

```python
if standard_price > 0 and 0 < margin < 100:
    suggested = standard_price / (1 - margin/100)
```

Sin observaciones. Protegido contra extremos.

---

## 2. Estado de las vistas UI

### 2.1 `views/sale_order_view.xml`

```xml
<xpath expr="//field[@name='order_line']/list/field[@name='price_unit']" position="after">
    <field name="qfm_margin_pct" widget="percentage" force_save="1"/>
    <field name="qfm_margin_abs" readonly="1" sum="Total Margen Importe"/>
</xpath>
```

| Aspecto | Veredicto |
|---|---|
| Inyección después de `price_unit` (lista de líneas) | ✅ Lógica visual correcta |
| `widget="percentage"` en margen editable | ✅ Coherente con inverse |
| `force_save="1"` | ✅ Necesario porque el campo es `store=False` pero el inverse necesita el valor |
| `sum="Total Margen Importe"` sobre campo `store=False` | ⚠️ **Suma poco confiable** |
| Falta vista en **formulario expandido** de la línea (`form` dentro del `list`) | ⚠️ No editable en edición avanzada |
| Falta inyección en **vista de cotización imprimible / pivote / reporte** | ℹ️ Opcional |

**Hallazgo 6 (UI):** En Odoo 19 los campos non-stored se suman en memoria; con cientos de líneas o cuando la vista pagina, el total puede salir desfasado. **Sugerencia:** o bien convertir el campo a `store=True` (con consideración de invalidación) o eliminar el atributo `sum` para no inducir error de lectura.

### 2.2 `views/purchase_order_view.xml`

```xml
<field name="qfm_margin_pct" readonly="1"/>
<field name="qfm_margin_abs" readonly="1" sum="Total Margen Importe"/>
```

| Aspecto | Veredicto |
|---|---|
| `readonly="1"` (no se permite invertir desde compras) | ✅ Coherente con el modelo |
| Misma observación de `sum` sobre non-stored | ⚠️ Igual que 2.1 |

### 2.3 `views/product_template_view.xml`

```xml
<field name="qfm_target_margin_pct" widget="percentage"/>
<field name="qfm_suggested_list_price" readonly="1" invisible="qfm_target_margin_pct &lt;= 0"/>
<button name="action_apply_suggested_price" ... invisible="qfm_suggested_list_price &lt;= 0"/>
```

| Aspecto | Veredicto |
|---|---|
| Widget percentage para margen objetivo | ✅ OK |
| Botón "Aplicar precio sugerido" oculto si no hay sugerencia | ✅ OK |
| Validación de rango `qfm_target_margin_pct < 100` | ❌ **No hay constraint** |
| `digits=(5,2)` permite valores hasta `999.99` | ⚠️ Permite entrada inválida |

**Hallazgo 7:** El usuario puede capturar `qfm_target_margin_pct = 150` en la ficha del producto. Aunque el compute lo ignora (`margin < 100` necesario), no se informa al usuario que su valor fue descartado. **Sugerencia:** `@api.constrains` o validación visual.

### 2.4 `views/sale_margin_line_rule_view.xml`

| Aspecto | Veredicto |
|---|---|
| Vista list editable bottom | ✅ OK |
| Menú bajo `sale.menu_sale_config` | ✅ OK |
| `line_key` readonly en formulario | ✅ OK |

Sin observaciones.

---

## 3. Casos borde analizados

| Caso | Comportamiento actual | Veredicto |
|---|---|---|
| Producto sin `standard_price` (=0) | `qfm_margin_pct = 100%` y `qfm_margin_abs = precio*qty` | ⚠️ Engañoso: aparece como "100% de margen" cuando en realidad **no hay costo registrado** |
| Cambio de cantidad | Recalcula `qfm_margin_abs` (incluido en `@api.depends`) | ✅ |
| Cambio de UoM en línea | `get_standard_cost_for_line` convierte | ✅ |
| Cambio de moneda en cabecera | `order_id.currency_id` está en `@api.depends`; convierte costo | ✅ |
| Descuento = 100% | Compute: `precio_venta = 0`, `qfm_margin_pct = 0`; Inverse: `ValidationError` | ✅ |
| Margen objetivo = 0% en inverse | `precio_venta_neto = costo`; precio = costo / factor_descuento | ✅ (precio = costo) |
| Margen objetivo negativo en inverse | Aplica fórmula sin error → precio < costo | ❌ **Sin validación** |
| Costo = 0 con margen objetivo > 0 | Precio se fija a `0` | ❌ **Bug, silencioso** |
| Recepción de devolución | `purchase_line_id` puede traer costo negativo o de orden devolutiva | ⚠️ No diferenciado |
| Multi-compañía (line en company A, producto en B) | `product.with_company(company)` en `margin_tools` | ✅ |

---

## 4. Terminología "A la mano"

Búsqueda exhaustiva en el módulo:

```
grep -iE "disponible|a la mano" sale_purchase_margins/
# (sin coincidencias)
```

**Resultado:** ✅ El módulo no expone textos de stock. **Regla cumplida por omisión.** No requiere intervención.

---

## 5. Resumen ejecutivo de hallazgos

| # | Severidad | Componente | Descripción |
|---|---|---|---|
| 1 | 🟡 Bajo | sale_order_line | `qfm_margin_pct=0` cuando `precio=0` y `costo>0` (confusión visual) |
| 2 | 🟡 Bajo | purchase_order_line | Etiqueta "Margen Compra" semánticamente discutible |
| 3 | 🔴 **Alto** | sale_order_line (inverse) | `costo=0` con margen objetivo → fija `price_unit=0` sin alerta |
| 4 | 🟠 Medio | sale_order_line (inverse) | No rechaza margen objetivo negativo |
| 5 | 🟠 Medio | stock_picking | Recepción baja `list_price` sin confirmación ni política configurable |
| 6 | 🟡 Bajo | views (sale/purchase) | `sum` sobre campo `store=False` puede dar totales no confiables |
| 7 | 🟡 Bajo | product_template | No hay constraint de rango sobre `qfm_target_margin_pct` |

---

## 6. Propuestas exactas de refactorización

### 6.1 Hallazgo 3 + 4 — Validación en `_qfm_apply_target_margin_to_price_unit`

**Archivo:** `models/sale_order_line.py` (alrededor de la línea 156)

```python
def _qfm_apply_target_margin_to_price_unit(self):
    for line in self:
        if not line.product_id:
            continue
        margen_objetivo = line.qfm_margin_pct or 0.0

        # NUEVO: rechazar margen objetivo negativo
        if margen_objetivo < 0.0:
            raise ValidationError(_('El margen objetivo no puede ser negativo.'))
        if margen_objetivo >= 100.0:
            raise ValidationError(_('El margen objetivo debe ser menor a 100%.'))
        ...
        try:
            costo_unitario = get_standard_cost_for_line(line, 'product_uom_id')
        except (UserError, ValidationError):
            raise
        except Exception:
            _logger.exception(...)
            continue

        # NUEVO: si no hay costo, no aplicar precio cero silencioso
        if costo_unitario <= 0.0:
            raise ValidationError(_(
                'El producto %s no tiene costo estándar definido. '
                'Configura el costo antes de aplicar un margen objetivo.'
            ) % line.product_id.display_name)
        ...
```

### 6.2 Hallazgo 6 — Eliminar `sum` sobre campos non-stored

**Archivos:** `views/sale_order_view.xml`, `views/purchase_order_view.xml`

```xml
<!-- Antes -->
<field name="qfm_margin_abs" readonly="1" sum="Total Margen Importe"/>
<!-- Después: dos opciones -->
<!-- (A) Quitar el sum -->
<field name="qfm_margin_abs" readonly="1"/>
<!-- (B) Volver el campo store=True con compute correcto -->
```

Recomendación: **opción A** por simplicidad (el módulo es store=False por diseño).

### 6.3 Hallazgo 7 — Constraint en `product_template`

**Archivo:** `models/product_template.py`

```python
from odoo.exceptions import ValidationError
from odoo import _

@api.constrains('qfm_target_margin_pct')
def _check_qfm_target_margin_pct(self):
    for tmpl in self:
        margin = tmpl.qfm_target_margin_pct or 0.0
        if margin < 0.0 or margin >= 100.0:
            raise ValidationError(_(
                'El margen objetivo del producto debe estar entre 0 y 99.99%.'
            ))
```

### 6.4 Hallazgo 5 — Política configurable en `stock_picking`

**Archivo:** `models/stock_picking.py` + `models/res_config_settings.py` (nuevo)

Política `qfm_picking_price_policy` con valores:
- `'auto'` (comportamiento actual)
- `'only_increase'` (sólo subir `list_price`)
- `'manual'` (sólo postear sugerencia en chatter, no escribir)

Implementación pendiente de aprobación porque introduce settings nuevos.

### 6.5 Hallazgo 1 + 2 — Mejoras de UX (no urgentes)

- Agregar `help=` en `qfm_margin_pct` (sale) explicando comportamiento con `precio=0`.
- Renombrar campo de compra o agregar `help=` explicando la fórmula `(costo_std - precio) / precio`.

---

## 7. Pruebas existentes — Cobertura

El archivo `tests/test_margin_computation.py` cubre:
- ✅ Margen venta con descuento
- ✅ Margen venta con precio cero
- ✅ Margen compra positivo y negativo
- ✅ Inverse de margen con y sin descuento
- ✅ Margen objetivo = 100% → ValidationError
- ✅ Normalización de claves de regla por línea
- ✅ Rechazo de regla con margen ≥ 100

**Brechas detectadas (a cubrir tras refactor):**
- ❌ Inverse con margen negativo (Hallazgo 4)
- ❌ Inverse con `costo = 0` (Hallazgo 3)
- ❌ Constraint de rango en `product_template` (Hallazgo 7)
- ❌ Comportamiento de `stock_picking` ante recepción con costo menor

---

## 8. Decisión requerida

**¿Estás de acuerdo con los hallazgos de esta auditoría para proceder a inyectar las mejoras funcionales sugeridas?**

Si lo apruebas, mi plan de implementación inmediato sería:

1. **Prioridad Alta (Hallazgos 3 y 4):** validar `costo_unitario > 0` y `margen >= 0` en el inverse de `sale.order.line` + tests.
2. **Prioridad Media (Hallazgo 7):** `@api.constrains` en `product_template` + test.
3. **Prioridad Baja (Hallazgo 6):** quitar `sum` de los XML de sale/purchase.
4. **Discusión separada (Hallazgo 5):** propuesta de política en `stock_picking` (requiere alineación de negocio antes de codificar).
5. **Cosmético (Hallazgos 1, 2):** ajustar `help=` y revisar etiqueta del campo de compra.

A la espera de tu aprobación para proceder con los pasos 1-3, y de tu definición sobre el paso 4.
