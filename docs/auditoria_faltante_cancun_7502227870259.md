# Auditoría forense de inventario — Faltante de 50 piezas, ROXIDOLIN CAPS 100MG C/10 (RAAM) — Sucursal Cancún

**Instancia auditada:** `medicinedepot.odoo.com` (Odoo.sh, producción real)
**Método:** navegación autenticada en la UI de producción (sesión ya iniciada del usuario), módulo Inventario/Compras. **Estrictamente solo lectura** — no se editó, validó ni canceló ningún registro durante la auditoría.
**Alcance de acceso:** el usuario de la sesión está limitado al almacén **MDS CANCÚN** (todas las vistas de operaciones, historial y análisis solo muestran esta sucursal). No se tuvo visibilidad de la compañía/almacén **MID (Mérida)** — ver limitación en §5.
**Fecha de ejecución:** 2026-08-27.

---

## 1. Resumen ejecutivo

- **La fecha "18 de junio de 2026" reportada como recepción NO corresponde a ningún evento real del sistema.** El evento real más cercano a esa fecha es una **salida** (no una entrada): un traslado inter-compañía de 40 unidades de Cancún hacia Mérida el **11 de junio de 2026** (documento `TRASLADO CANCUN-MERIDA`). El único evento de **entrada** de 50 unidades ocurrió el **18 de julio de 2026** — un mes después de la fecha reportada. Se recomienda confirmar con el equipo de Cancún si la fecha "18 de junio" fue un error de captura por "18 de julio".
- **Causa raíz confirmada del faltante de 50 piezas: una orden de compra duplicada, capturada dos veces para la misma entrega del proveedor, y ambas marcadas como recibidas.**
  - El 18 de julio de 2026, **GENOBEVA ZÁRATE** creó la orden de compra **`P07869`** (8:31 a.m.) y, 22 minutos después, **`P07872`** (8:53 a.m. / confirmada 9:02 a.m.) — ambas a nombre del mismo proveedor (QUÍMICOS Y FÁRMACOS DE MÉXICO S.A. DE C.V.), con las **mismas 26 líneas de producto, mismas cantidades, mismos lotes** (incluyendo 50 u. de ROXIDOLIN, lote `RRD234`) y el mismo total ($22,760.03). Es, en la práctica, la misma orden duplicada por captura manual.
  - `P07872` fue recibida y **facturada** ese mismo día (18-jul, 9:02 a.m.) — es la entrega real y única del proveedor.
  - `P07869` quedó pendiente ("Sin recibir") durante **más de un mes**. El **24 de agosto de 2026, 5:18 p.m.**, el usuario genérico **MDS ADMIN ODOO** validó su recepción completa (picking `CUN/IN/01421`) — **sin que exista ninguna factura de proveedor asociada** (`Facturado = 0.00` en las 26 líneas). Esto añadió al sistema una segunda entrada "fantasma" de 50 unidades de ROXIDOLIN (y de los otros 25 productos del mismo pedido) que **nunca llegó físicamente** a la sucursal.
- **El kardex del lote `RRD234` cuadra matemáticamente al 100%** una vez identificada la orden duplicada: `0 + 50 (real, 18-jul) − 32 (ventas PdV) + 50 (fantasma, 24-ago) = 68` = saldo actual del sistema. Sin la recepción fantasma, el saldo real sería **18 unidades** — exactamente 50 menos que las 68 que el sistema reporta hoy.
- **Diagnóstico: no hubo merma, robo ni traspaso mal registrado.** El inventario físico de Cancún nunca tuvo 68 piezas; el sistema sobreestimó el inventario en 50 unidades desde el 24 de agosto de 2026 por la validación tardía de una orden de compra duplicada y nunca entregada.

---

## 2. Fase 1 — Ficha del producto y mapeo de Cancún

| Campo | Valor |
|---|---|
| Producto | ROXIDOLIN CAPS 100MG C/10 (DOXICICLINA)(RAAM) |
| ID interno (`product.product`) | 3637 |
| Referencia interna / Código de barras | `7502227870259` |
| Categoría | Todos / Vendibles / ANTIBIOTICO |
| Seguimiento de inventario | Por lotes |
| Costo estándar | $20.568844 / unidad |
| Precio de venta | $26.10 / unidad |
| Cantidad a la mano (sistema, 27-ago-2026) | **68.00 Unidades** |
| Almacén auditado | MDS CANCÚN — única sucursal visible en esta sesión |

No se identificaron ubicaciones de cuarentena/merma con stock para este producto; las únicas ubicaciones con movimiento en el periodo son `CUN/Existencias` (interna) y la ubicación virtual `Inter-company transit` (usada en traspasos entre sucursales de distinta compañía Odoo).

---

## 3. Fase 2 — Matriz de recepciones auditadas

### 3.1 Evento del "18 de junio" — no existe. Evento real más cercano: salida del 11 de junio

| Campo | Valor |
|---|---|
| Documento | `CUN/INT/00143` |
| Tipo de operación | MDS CANCÚN: Traslados internos |
| Origen → Destino | `CUN/Existencias` → `Virtual Locations/Inter-company transit` |
| Documento origen | **TRASLADO CANCUN-MERIDA** |
| Responsable | GENOBEVA ZARATE |
| Fecha efectiva | **11-jun-2026, 4:52 p.m.** |
| Cantidad ROXIDOLIN | **40.00 unidades** (salida), lotes `RRD232` (20) + `RRD233` (20) |
| Otros productos en el mismo traslado | 27 productos adicionales (traslado consolidado grande) |

Este documento está completo y correctamente validado desde la perspectiva de Cancún. **No se pudo verificar si Mérida generó y validó la recepción correspondiente** — ver limitación de acceso en §5. Si el objetivo original era auditar "una recepción del 18 de junio", no existe tal recepción; lo más cercano en el tiempo es esta salida hacia Mérida.

### 3.2 Recepción real — 18 de julio de 2026 (`P07872` / `CUN/IN/01422`)

| Campo | Valor |
|---|---|
| Orden de compra | `P07872` (ref. proveedor B147618) |
| Proveedor | QUÍMICOS Y FÁRMACOS DE MÉXICO S.A. DE C.V. |
| Creada / confirmada | 18-jul-2026, 8:53 a.m. / 9:02 a.m. — GENOBEVA ZARATE |
| Picking de recepción | `CUN/IN/01422` |
| Fecha efectiva | 18-jul-2026, 9:02 a.m. |
| ROXIDOLIN — Demanda vs. Recibido | 50.00 / **50.00** (lote `RRD234`) |
| Facturado | **Sí** (26/26 líneas facturadas) |
| Estatus | Hecho — **entrega real, sin observaciones** |

### 3.3 Recepción fantasma — 24 de agosto de 2026 (`P07869` / `CUN/IN/01421`)

| Campo | Valor |
|---|---|
| Orden de compra | `P07869` (misma ref. proveedor B147618) |
| Proveedor | QUÍMICOS Y FÁRMACOS DE MÉXICO S.A. DE C.V. (idéntico) |
| Creada / confirmada | 18-jul-2026, **8:31 a.m. / 8:44 a.m.** (18 minutos antes que `P07872`) |
| Picking de recepción | `CUN/IN/01421` |
| Fecha efectiva (validación) | **24-ago-2026, 5:18 p.m.** — 37 días después de creada |
| Validado por | **MDS ADMIN ODOO** (usuario genérico/admin, no Genoveva) |
| ROXIDOLIN — Demanda vs. Recibido | 50.00 / **50.00** (mismo lote `RRD234`) |
| Facturado | **No** (0.00 en las 26 líneas — sin factura de proveedor) |
| Estatus | Hecho — **entrega duplicada, sin respaldo documental del proveedor** |

### 3.4 Comparativa directa

| | `P07872` (real) | `P07869` (duplicada) |
|---|---|---|
| Proveedor | Idéntico | Idéntico |
| Líneas / cantidades / lotes | Idénticos (26 líneas, incl. RRD234 = 50 u.) | Idénticos |
| Total | $22,760.03 | $22,760.03 |
| Recibida el | 18-jul-2026 | 24-ago-2026 (37 días tarde) |
| Facturada | Sí | **No** |
| Validada por | Genoveva Zárate (mismo día de creación) | MDS Admin Odoo (más de un mes después) |

---

## 4. Fase 3 — Kardex consolidado del lote `RRD234` (el que explica el saldo actual)

| Fecha | Documento | Movimiento | Cantidad | Saldo lote RRD234 |
|---|---|---|---|---|
| 18-jul, 9:02 a.m. | `CUN/IN/01422` (P07872) | Entrada — **real** | +50.00 | 50.00 |
| 22-jul, 4:22 p.m. | `CUN/PdV/...` | Venta PdV | −1.00 | 49.00 |
| 23-jul, 12:05 p.m. | `CUN/PdV/...` | Venta PdV | −5.00 | 44.00 |
| 01-ago, 1:52 p.m. | `CUN/PdV/...` | Venta PdV | −5.00 | 39.00 |
| 07-ago, 7:43 a.m. | `CUN/PdV/...` | Venta PdV | −3.00 | 36.00 |
| 10-ago, 2:24 p.m. | `CUN/PdV/...` | Venta PdV | −3.00 | 33.00 |
| 12-ago, 7:50 a.m. | `CUN/PdV/...` | Venta PdV | −2.00 | 31.00 |
| 12-ago, 10:45 a.m. | `CUN/PdV/...` | Venta PdV | −4.00 | 27.00 |
| 17-ago, 2:03 p.m. | `CUN/PdV/...` | Venta PdV | −2.00 | 25.00 |
| 17-ago, 3:05 p.m. | `CUN/PdV/...` | Venta PdV | −3.00 | 22.00 |
| 19-ago, 7:54 a.m. | `CUN/PdV/...` | Venta PdV | −2.00 | 20.00 |
| 21-ago, 3:11 p.m. | `CUN/PdV/...` | Venta PdV | −2.00 | **18.00 ← saldo físico real** |
| 24-ago, 5:18 p.m. | `CUN/IN/01421` (P07869) | Entrada — **fantasma (duplicada, no facturada)** | +50.00 | **68.00 ← saldo del sistema hoy** |

**Ecuación de cuadre:**

```
Saldo real físico (21-ago)                    = 18 unidades
+ Recepción fantasma no entregada (24-ago)     = 50 unidades
────────────────────────────────────────────────────────────
Saldo registrado en el sistema (27-ago)        = 68 unidades
```

El 100% de las 13 transacciones del lote reconcilia sin residuo: no hay ninguna venta, traspaso o ajuste sin explicar. La única "entrada" que no tiene contraparte física verificable es la del 24 de agosto.

*(Los lotes anteriores del producto — `RRD230`, `RRD232`, `RRD233` — se agotaron entre ventas de PdV y el traslado a Mérida del 11-jun; todos están en 0.00 unidades a la fecha y no contribuyen al saldo actual.)*

---

## 5. Verificación cruzada entre sucursales (ampliación de filtros, 2026-08-27)

La sesión inicial estaba limitada a la compañía/almacén **MDS CANCÚN**. Se amplió el filtro de compañías del selector de Odoo a las 6 sucursales (Cancún, Mérida, Campeche, Chetumal, Playa del Carmen, Ticul) para verificar dos puntos pendientes:

**5.1 ¿Se recibió en Mérida el traslado del 11 de junio?**

Filtrando `Historial de movimientos` por producto + ubicación `Inter-company transit` en las 6 compañías aparecen las 4 líneas completas del traslado:

| Fecha | Documento | Desde → A | Lote | Cantidad |
|---|---|---|---|---|
| 11-jun, 4:52 p.m. | `CUN/INT/00143` | CUN/Existencias → Virtual/Inter-company transit | RRD232 | 20.00 (salida) |
| 11-jun, 4:52 p.m. | `CUN/INT/00143` | CUN/Existencias → Virtual/Inter-company transit | RRD233 | 20.00 (salida) |
| 20-jun, 11:56 a.m. | `MID/INT/0...` | Virtual/Inter-company transit → MID/Existencias | RRD232 | 20.00 (entrada) |
| 20-jun, 11:56 a.m. | `MID/INT/0...` | Virtual/Inter-company transit → MID/Existencias | RRD233 | 20.00 (entrada) |

**Confirmado: Mérida sí recibió las 40 unidades completas**, 9 días después del envío (tránsito razonable para un traslado inter-compañía, sin automatización de recepción instantánea). Este traslado queda descartado como causa del faltante — no es un cabo suelto.

**5.2 ¿El lote `RRD234` es exclusivo de Cancún?**

No. Con las 6 compañías visibles, el mismo número de lote `RRD234` aparece también en Mérida, Chetumal, Playa del Carmen, Ticul y Campeche (p. ej. Chetumal recibió 20 u. de `RRD234` directamente de un proveedor el 10-ago, por una orden de compra propia de esa sucursal). Esto es normal: `RRD234` es el número de lote/batch del **fabricante**, no un identificador exclusivo de una recepción o sucursal — cada sucursal compra su propio stock al mismo proveedor y hereda el mismo número de lote físico. No cambia el diagnóstico de §1: el problema es específico de los documentos `P07869`/`P07872` en Cancún, no una confusión de lotes entre sucursales.

**5.3 Alcance no cubierto:** no se auditó si el patrón de "dos órdenes de compra idénticas capturadas minutos aparte" se repite en otras sucursales o con otros proveedores — el proveedor QUÍMICOS Y FÁRMACOS DE MÉXICO S.A. DE C.V. tiene 4,131 órdenes históricas en las 6 compañías, y una revisión exhaustiva de duplicados es una auditoría de gobernanza de compras aparte, de mayor alcance que este caso puntual. Se deja como recomendación en el plan de acción (punto 6).

---

## 6. Dictamen y plan de acción

**Dictamen:** el faltante de 50 piezas de ROXIDOLIN CAPS 100MG en Cancún **no es una pérdida física** (merma, robo o error de traspaso) sino una **sobreestimación contable** causada por la validación, 37 días tarde, de una orden de compra (`P07869`) que era un duplicado accidental de otra (`P07872`) ya recibida y facturada el mismo día que ambas fueron creadas. La mercancía de `P07869` nunca llegó a la sucursal — no existe factura del proveedor que la respalde.

El traslado a Mérida (11-jun) y el resto de sucursales quedan descartados como causa — es un problema acotado a dos documentos de Cancún.

### Plan de acción

**Fase 1 — Corrección contable inmediata (responsable: Inventario/Compras Cancún, plazo: esta semana)**

1. Generar un ajuste de inventario en `CUN/Existencias` para el lote `RRD234`, de 68 a 18 unidades (−50), citando esta auditoría y el picking `CUN/IN/01421` como justificación.
2. Confirmar con **GENOBEVA ZÁRATE** (compradora de ambas órdenes) si recuerda haber capturado `P07869` por duplicado — esto ayuda a fechar el error y a descartar que sea un problema del sistema en lugar de captura manual.
3. Verificar con Cuentas por Pagar que **no exista ninguna factura ni pago programado** contra `P07869` (ya se confirmó `Facturado = 0.00` en las 26 líneas, pero debe cerrarse formalmente el ciclo compra-pago).
4. Cancelar o marcar `P07869` como duplicado de `P07872` en el sistema, dejando trazabilidad de la corrección (no eliminar el registro).

**Fase 2 — Contener el daño en el resto del pedido (responsable: Inventario Cancún, plazo: esta semana)**

5. `P07869`/`P07872` comparten **26 líneas idénticas** (mismas cantidades y lotes). Todas ellas quedaron dobladas en `CUN/Existencias` el 24-ago, no solo ROXIDOLIN. Repetir el mismo ajuste de inventario (Fase 1, punto 1) para los otros 25 productos del pedido antes de que generen sus propios "faltantes" reportados en el piso de venta.

**Fase 3 — Controles preventivos (responsable: Compras / TI, plazo: próximas 2-4 semanas)**

6. **Alerta de orden duplicada:** evaluar una validación en `purchase.order` que marque como sospechosas dos órdenes al mismo proveedor, con el mismo total y línea de productos, confirmadas en una ventana corta (p. ej. menos de 1 hora) — como ocurrió aquí (22 minutos de diferencia).
7. **Antigüedad máxima antes de recibir:** una orden de compra con más de ~15 días de atraso frente a su fecha de entrega esperada no debería poder validarse con un clic genérico de "Recibir todo". Debe forzar una revisión manual línea por línea contra lo que físicamente llegó — `P07869` estuvo 37 días parada y se validó sin ese control.
8. **Restringir el usuario "MDS ADMIN ODOO"** para operaciones de recepción de mercancía: quien valida una recepción física debería ser siempre la persona que la recibió en almacén, no una cuenta administrativa genérica — así queda claro quién verificó (o no verificó) la mercancía contra la orden.

**Fase 4 — Verificación de alcance más amplio (responsable: Auditoría interna, plazo: a criterio, fuera del alcance de este caso)**

9. Este caso identificó el patrón "dos órdenes idénticas capturadas minutos aparte" en Cancún. No se auditó si se repite en las otras 5 sucursales o con otros proveedores (el proveedor de este caso, QUÍMICOS Y FÁRMACOS DE MÉXICO, tiene 4,131 órdenes históricas en las 6 compañías). Si se quiere descartar que sea un hábito recurrente y no un incidente aislado, es una auditoría de gobernanza de compras independiente — se sugiere acotarla por proveedor + rango de fechas antes de intentar cubrir las 6 sucursales de una sola vez.
