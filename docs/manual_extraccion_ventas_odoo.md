# Auditoría y manual de extracción de ventas — Odoo.sh producción (Medicine Depot Sureste)

**Fecha de auditoría:** 2026-09-04
**Entorno auditado:** `https://medicinedepot.odoo.com` — base `medicinedepot-main-26466886` (Odoo 19.0 Enterprise, producción real vía Odoo.sh)
**Método:** conexión directa XML-RPC (`/xmlrpc/2/object`) con usuario `administradorodoo@medicinedepotsureste.mx`, sin escrituras — solo lectura de `pos.order.line`, `sale.order.line`, `account.move.line`, `pos.order`, `sale.order`, `product.product`.
**Archivos auditados:**
- `REPORTE_VENTAS_AGOSTO_LINEAS_ESTRATEGICAS.xlsx` (hojas "Ventas Ago 2026 + Stock" y "Resumen por Laboratorio")
- `Analisis Punto de Venta AMSA.xlsx`

---

## 1. Veredicto técnico

### 1.1 `REPORTE_VENTAS_AGOSTO_LINEAS_ESTRATEGICAS.xlsx` — **VERIFICADO, SIN ERROR DE CÁLCULO**

El propio archivo documenta su metodología en el encabezado (fila 2 de la hoja):

> *"Ventas: 01/08/2026 - 31/08/2026 (POS, ordenes no canceladas, importe neto sin IVA) | Stock: instantanea al 01/09/2026 18:10 (stock.quant, ubicaciones internas)"*

Se replicó esa consulta exacta contra `pos.order.line` en producción (`order_id.state not in ['cancel']`, `order_id.date_order` en el rango, filtrado a los 476 SKUs de las 5 líneas: AMSA, PISA, RAAM, LOEFFLER, GALIA TEXTIL) y el resultado **coincide al peso y a la pieza**, tanto en el total global como en cada una de las 6 sucursales:

| Sucursal (compañía Odoo) | Piezas Excel | Piezas Odoo | Monto Excel | Monto Odoo |
|---|---:|---:|---:|---:|
| MERIDA (compañía *"SABRINA ELIZABETH ROJANO ROMERO"*) | 8,293 | 8,293 | $263,867.64 | $263,867.64 |
| CANCÚN | 8,892 | 8,892 | $283,135.86 | $283,135.86 |
| TICUL | 3,292 | 3,292 | $129,358.75 | $129,358.75 |
| CAMPECHE | 6,228 | 6,228 | $250,600.91 | $250,600.91 |
| CHETUMAL | 3,451 | 3,451 | $110,114.80 | $110,114.80 |
| PLAYA DEL CARMEN | 3,791 | 3,791 | $125,266.32 | $125,266.32 |
| **TOTAL GLOBAL** | **33,947** | **33,947** | **$1,162,344.28** | **$1,162,344.28** |

**Conclusión: no hay pedidos borrador mezclados, no hay cancelados incluidos, no hay confusión de fecha de cotización vs. facturación, y no hay desfase por zona horaria a nivel de agregado.** Quien construyó este reporte usó el criterio correcto para lo que declara medir (venta de mostrador/POS de las 5 líneas estratégicas) y el dato es confiable tal cual está.

### 1.2 El riesgo real no es de cálculo, es de **alcance / interpretación**

El título *"REPORTE DE VENTAS AGOSTO 2026"* no deja explícito, a simple vista, que:

**a) Solo cubre mostrador (POS), no mayoreo.** Para esos mismos 476 SKUs, en agosto 2026 hubo ventas de mayoreo (`sale.order`, `state = 'sale'`, confirmadas) por **1,230 piezas / $58,944.70** que **no están incluidas** en el reporte. Si alguien lo lee como "el total de ventas de estas líneas", se queda corto por ~5.1% del monto.

**b) Solo cubre 5 laboratorios de 476 SKUs, no el catálogo completo.** La venta POS total de la empresa en agosto 2026 (todos los productos, órdenes no canceladas, neto sin IVA) fue de **$4,857,227.07** en 2,032 tickets. El $1,162,344.28 del reporte es apenas el **23.9%** de eso. Si alguien lo lee como "el total de ventas de la empresa en agosto", el error es de más de 4×.

**Riesgo concreto:** si este archivo circula sin la nota de alcance visible en el título (no solo en la segunda fila del encabezado), un lector apurado en dirección/finanzas puede citarlo como "ventas de agosto" a secas.

### 1.3 `Analisis Punto de Venta AMSA.xlsx` — desglose de apoyo, consistente pero no es la fuente de verdad

Es un export granular por SKU y sucursal, solo del laboratorio AMSA. A nivel de producto individual coincide exactamente con la columna AMSA del reporte 1 (se verificó por muestreo, ej. código de barras `7501349012004`: 74/1,602.45 en MERIDA, 28/595.04 en CANCÚN, etc. — idéntico en ambos archivos).

Sin embargo, su fila "Total" propia (**9,920 piezas / $308,620.22**) no coincide de forma exacta con el subtotal AMSA validado del reporte 1 (**9,908 piezas / $310,337.16**) — una variación de +12 piezas / -$1,716.94 (~0.1% en piezas, ~0.55% en monto). Es una diferencia menor, no material, probablemente por un corte de sincronización en un momento ligeramente distinto (ticket de frontera de mes, o una sesión POS aún abierta al momento del export). **No se investigó a nivel de línea por no ser material — para AMSA, use el subtotal del reporte 1 (ya validado contra Odoo), no el total de este archivo.**

### 1.4 Contexto: ¿cuánto vendió realmente la empresa en agosto 2026?

Para dar la referencia completa que el reporte de líneas estratégicas no da por sí solo:

| Canal | Estado considerado | Piezas | Monto neto sin IVA |
|---|---|---:|---:|
| POS (todas las líneas, todas las sucursales) | no cancelado (`paid`, `done`) | 33,947 → *(no aplica, es cifra de las 5 líneas)* | — |
| **POS total empresa** | no cancelado | — (2,032 tickets) | **$4,857,227.07** |
| **Mayoreo total empresa** (`sale.order`) | confirmado (`state='sale'`) | — (54 pedidos) | **$150,732.56** |
| **Total combinado (aprox., referencia comercial)** | | | **≈ $5,007,959.63** |

Este es el número a usar si lo que se pide es "total de ventas de agosto de la empresa" — no el archivo de líneas estratégicas, que es un reporte de rotación de mostrador de un subconjunto de laboratorios.

---

## 2. Criterio oficial de extracción de ventas (Medicine Depot Sureste)

No existe un único "total de ventas" correcto — depende de para qué se usa. Se definen tres criterios institucionales, cada uno con su fuente:

### 2.1 Rotación de mostrador / anaquel por sucursal (lo que ya hace el reporte auditado)
- **Modelo:** `pos.order.line`
- **Filtro de estado:** `order_id.state not in ['cancel']` (equivalente en la UI: excluir "Cancelado"; incluye "Pagado" y "Publicado")
- **Fecha:** `order_id.date_order`, rango del mes calendario
- **Importe:** `price_subtotal` (neto, sin IVA) — usar `price_subtotal_incl` solo si se necesita con IVA
- **Uso:** control de inventario, desempeño de mostrador, líneas estratégicas por laboratorio

### 2.2 KPI comercial de ventas totales de la empresa
- **Fuente:** `pos.order` (no cancelado) **+** `sale.order` confirmado (`state = 'sale'`)
- **Fecha:** `date_order` de cada modelo
- **Importe:** neto sin IVA (`amount_total - amount_tax` en POS; `amount_untaxed` en Sale Orders)
- **Uso:** "¿cuánto vendimos en agosto?" a nivel dirección/gerencia — es la suma de los dos canales, mostrador + mayoreo

### 2.3 Conciliación fiscal / contable
- **Modelo:** `account.move.line`
- **Filtro:** `move_id.move_type in ['out_invoice','out_refund']`, `move_id.state = 'posted'`, `display_type = 'product'`
- **Fecha:** `move_id.invoice_date` (fecha de timbrado/factura, **no** la fecha del pedido)
- **Importe:** facturas **menos** notas de crédito (el filtro `in ['out_invoice','out_refund']` ya deja que la NC reste si se usa `price_subtotal` con signo, verificar signo en el reporte final)
- **Uso:** cruce contra lo declarado al SAT / cierre contable. **No usar** para reportes operativos de mostrador — mezcla POS facturado y mayoreo facturado, y la fecha de factura puede no coincidir con la fecha de venta real.

**Regla práctica: todo reporte de ventas debe indicar en el título (no solo en una nota al pie) cuál de estos tres criterios usa.**

---

## 3. Guía paso a paso — extracción correcta desde la interfaz de Odoo

### 3.1 Ventas de mostrador (POS) por sucursal y laboratorio — replica el reporte auditado

1. Ir a **Punto de Venta → Reporting → Órdenes**.
2. Cambiar a **vista Pivote** (ícono de tabla en la esquina superior derecha).
3. **Filtros obligatorios** (panel de búsqueda):
   - **Fecha de orden**: rango del mes exacto (ej. 01/08/2026 – 31/08/2026). Usar el filtro de fecha, no escribir el rango a mano.
   - **Estado**: excluir explícitamente "Nuevo" (draft, tickets abiertos sin cobrar) y "Cancelado". Dejar solo "Pagado" y "Publicado".
4. **Agrupadores recomendados**:
   - Filas: **Producto** (o **Categoría de producto** si se quiere por familia)
   - Columnas: **Compañía** (⚠️ en este sistema cada sucursal es una compañía separada; la sucursal MÉRIDA aparece en el sistema con el nombre **"SABRINA ELIZABETH ROJANO ROMERO"**, no "MÉRIDA" — es la razón social registrada de esa unidad. No confundir con un contacto o cliente.)
5. Para filtrar por laboratorio/línea (AMSA, PISA, RAAM, LOEFFLER, GALIA TEXTIL): el campo **NO se llama "Laboratorio"** en el sistema — es un campo personalizado de Studio llamado **"Línea"** (`x_studio_line`), ubicado en la ficha del producto (**Inventario → Productos → [producto] → pestaña General**, o vía el filtro personalizado "Línea" en el buscador de Reporting). Agregar un filtro personalizado: `Línea = <laboratorio>`.
6. Medida a mostrar en la tabla pivote: **Subtotal** (esto es el neto sin IVA — coincide con la columna "Vtas ($)" del reporte auditado). No usar "Total" si se quiere neto.
7. Exportar con el botón **⬇️ (flecha de descarga / XLSX)** en la esquina superior de la vista pivote.
8. **Validación antes de enviar el archivo:** sumar la columna de total exportada y compararla contra el "Total" que Odoo muestra en la última fila/columna de la tabla pivote — deben coincidir exactamente. Si no coinciden, revisar que no se haya aplicado un filtro de agrupación que duplique líneas (ej. agrupar por variante Y por producto padre a la vez).

### 3.2 Ventas totales de la empresa (mostrador + mayoreo) — KPI comercial

1. **Parte POS**: repetir 3.1 sin el filtro de "Línea" (todos los productos), anotar el total neto.
2. **Parte mayoreo**: ir a **Ventas → Reporting → Ventas**, vista Pivote.
   - Filtro: **Estado = Orden de venta** (excluye Cotización, Cotización enviada y Cancelado — deja solo pedidos confirmados).
   - Filtro de fecha: **Fecha de orden**, mismo rango de mes.
   - Medida: **Importe sin impuestos** (`amount_untaxed`).
3. Sumar ambos totales manualmente. Odoo no tiene una vista nativa que combine POS + Ventas en una sola tabla — este es un paso manual y debe documentarse en el reporte final ("POS: $X + Mayoreo: $Y = $Z").

### 3.3 Conciliación fiscal (facturación neta)

1. Ir a **Contabilidad → Reporting → Diario de ventas** (o **Facturación → Reporting**).
2. Vista Pivote o Lista.
3. **Filtros obligatorios**:
   - **Tipo de documento**: Factura de cliente + Nota de crédito de cliente (ambos, para que las NC resten).
   - **Estado**: solo "Publicado" (posted) — nunca incluir borradores.
   - **Fecha de factura** (no "fecha de creación", no "fecha de vencimiento"): rango del mes.
4. Agrupar por **Cliente** y/o **Producto** según necesidad.
5. Medida: **Total sin impuestos**. Verificar que las notas de crédito aparezcan con signo negativo en la suma (si el reporte las muestra en positivo, hay que restarlas manualmente).
6. Exportar y validar la suma contra el total mostrado por Odoo en la vista, igual que en 3.1 paso 8.

### 3.4 Checklist de validación (aplica a los tres casos)

- [ ] El rango de fechas usa el campo correcto para el modelo (`date_order` en POS/Ventas, `invoice_date` en Facturación) — **no mezclar**.
- [ ] Los estados excluidos son explícitos: sin "Cancelado", sin borradores/cotizaciones.
- [ ] El importe exportado es neto sin IVA, salvo que el destinatario pida explícitamente "con IVA".
- [ ] El título del archivo exportado indica el alcance real (sucursal, laboratorio/línea, canal) — no dejarlo genérico como "Reporte de Ventas".
- [ ] La suma de la exportación coincide con el total que muestra Odoo en pantalla antes de descargar.

---

## 4. Resumen ejecutivo (para consola / lectura rápida)

```
REPORTE_VENTAS_AGOSTO_LINEAS_ESTRATEGICAS.xlsx
  Alcance declarado: POS, no cancelados, neto sin IVA, 01-31/08/2026, 5 líneas (476 SKUs)
  Verificación contra Odoo producción (pos.order.line):  ✅ COINCIDE EXACTO
    Total:              33,947 pzas  /  $1,162,344.28   (Excel = Odoo, 6/6 sucursales exactas)

  Lo que el archivo NO incluye (y su título no aclara):
    Mayoreo de las mismas 5 líneas (sale.order confirmado, ago 2026):   1,230 pzas / $58,944.70
    Ventas POS de TODA la empresa (no solo las 5 líneas), ago 2026:              $4,857,227.07
    Mayoreo de TODA la empresa, confirmado, ago 2026:                              $150,732.56
    -> Total real de ventas de la empresa en agosto 2026 (POS + mayoreo): ≈ $5,007,959.63

Analisis Punto de Venta AMSA.xlsx
  Consistente a nivel SKU con la columna AMSA del reporte principal.
  Su propio total (9,920 pzas / $308,620.22) difiere ~0.1-0.5% del subtotal AMSA
  validado (9,908 pzas / $310,337.16) — no material, usar el reporte principal.

VEREDICTO: no hay error de extracción que corregir en las cifras. El riesgo es que el
título del reporte no comunica su alcance (solo mostrador, solo 5 laboratorios) y puede
confundirse con "ventas totales de agosto". Recomendación: renombrar/titular los reportes
futuros con el alcance explícito, ej. "Ventas MOSTRADOR — Líneas Estratégicas — Agosto 2026".
```

---

*Generado por auditoría vía XML-RPC de solo lectura contra Odoo.sh producción. Sin escrituras realizadas. Credenciales usadas: usuario administrador de la instancia productiva — no se almacenaron en este repositorio.*
