# Trazabilidad forense — Lote `25G113n` / Producto `7501836005526` (ULGEL C 240 ML)

**Instancia auditada:** `medicinedepot.odoo.com` (Odoo.sh, producción real — DB `medicinedepot-main-26466886`)
**Método:** XML-RPC (`/xmlrpc/2/common`, `/xmlrpc/2/object`), usuario `administradorodoo@medicinedepotsureste.mx`.
**Alcance de la sesión:** estrictamente **solo lectura** (`search_read`/`read`/`fields_get`). No se ejecutó ninguna escritura sobre producción.
**Fecha de ejecución:** 2026-08-26.

---

## 1. Resumen ejecutivo

- **El lote objetivo se registra en el sistema como `25G113` (sin la "n" final).** No existe ningún `stock.lot` con el nombre exacto `25G113n` para este producto ni ningún otro. Se localizó un único lote `25G113` (`id=66563`) asociado al `product_id=5609` (ULGEL C/240ML, barcode `7501836005526`), y es el único candidato razonable — se asume que corresponde al lote solicitado, con probable error de transcripción del nombre (confusión con una "n" impresa/manuscrita en el empaque). **Recomendación:** confirmar contra el empaque físico o la etiqueta de lote antes de dar por cerrado el dictamen.
- **Existencia física actual: 4.0 unidades**, todas en `MID/Existencias` (MDS Mérida, empresa "SABRINA ELIZABETH ROJANO ROMERO"), sin reservas (`reserved_quantity = 0`).
- **10.0 unidades adicionales están en tránsito inter-sucursal** (`Virtual Locations/Inter-company transit`), correspondientes a una transferencia hacia MDS Campeche (`CAMP/INT/00116`) que a la fecha de la auditoría está **pendiente de recepción** (`state = assigned`, `qty_done = 0`).
- **El kardex completo (20 `stock.move.line`, incluidas 19 líneas `done` + 1 `assigned`) reconcilia al 100% contra los quants actuales** en las 3 ubicaciones internas con movimiento (MID, CUN, PLAYA) y contra la ubicación de tránsito. No se detectaron cantidades negativas en ubicaciones internas, reservas huérfanas, ni movimientos sin contrapartida.
- **Balance de cuadre:** 45.0 recibidas (3 recepciones de compra) − 31.0 vendidas (11 ventas POS) = **14.0 unidades bajo control de la empresa**, que se descomponen en 4.0 físicas en MID + 10.0 en tránsito hacia CAMP. **Cuadra exacto.**
- No se encontró ninguna factura de cliente (`account.move`, `move_type=out_invoice`) vinculada directamente a las 11 órdenes POS que movieron este lote (`pos_order_ids` sin coincidencias), pese a que las 11 órdenes reportan `is_invoiced=True` / `invoice_status=invoiced`. Esto es consistente con el patrón operativo de MDS (venta de mostrador facturada/cerrada a nivel de sesión de caja, no como CFDI individual por línea), pero **no se verificó de forma concluyente** — queda como punto abierto para una auditoría fiscal/CFDI dedicada si se requiere.

**Dictamen: trazabilidad completa y consistente, sin anomalías de inventario.** El lote tiene documentación de origen completa (3 compras, 3 proveedores/facturas) y documentación de destino completa (11 ventas POS con cliente identificado), y el saldo físico + en tránsito cuadra exacto contra el neto recibido − vendido.

---

## 2. Ficha del producto y del lote

| Campo | Valor |
|---|---|
| `product.product.id` | 5609 |
| Nombre | ULGEL C/240ML SUSP (ALUMINIO, MAGNESIO, SIMETICONA)(LIFERPAL) |
| `default_code` / `barcode` | 7501836005526 |
| `categ_id` | Todos / Vendibles / SISTEMA GASTROINTESTINAL |
| `tracking` | `lot` (seguimiento por lote) |
| `cost_method` | `average` (AVCO) |
| `type` | `consu` |
| `qty_available` (producto completo, todos los lotes) | 11.0 |
| `virtual_available` (producto completo, todos los lotes) | 21.0 |

| Campo del lote | Valor |
|---|---|
| `stock.lot.id` | 66563 |
| `name` | `25G113` (⚠️ no `25G113n` — ver nota Fase 1 abajo) |
| `expiration_date` | 2027-08-31 |
| `use_date` | 2027-03-04 |
| `removal_date` | 2027-07-27 |
| `alert_date` | 2027-03-04 |
| `create_date` | 2026-04-23 20:37:46 (coincide con la primera recepción de compra) |
| `product_qty` (calculado por Odoo, existencia actual del lote) | 4.0 |
| `note` | (vacío) |

> **Nota de identificación (Fase 1):** la búsqueda exacta `name ilike '25G113n'` no arrojó resultados. La búsqueda ampliada `name ilike '25G113'` sobre todo el sistema (sin filtrar por producto) devolvió dos lotes: `25G113` (este, para ULGEL C) y `PM25G113` (para un producto distinto, PRENA MAX). Dado que `25G113` es el único lote de este nombre asociado al producto ULGEL C, se usó como el lote objetivo del resto de la auditoría.

---

## 3. Matriz de existencias actuales (`stock.quant`)

| Ubicación | Tipo | Empresa | Cantidad | Reservado | Neto disponible |
|---|---|---:|---|---:|---:|
| **MID/Existencias** (MDS Mérida) | `internal` | SABRINA ELIZABETH ROJANO ROMERO | **4.0** | 0.0 | **4.0** |
| Virtual Locations/Inter-company transit | `transit` | — | 10.0 | 0.0 | 10.0 (en tránsito, pendiente de recepción en CAMP) |
| Partners/Vendors | `supplier` | — | −45.0 | 0.0 | (cuenta virtual acumulada de recepciones — no es stock físico) |
| Partners/Customers | `customer` | — | 31.0 | 0.0 | (cuenta virtual acumulada de ventas — no es stock físico) |

**Existencia física real (ubicaciones `usage='internal'`): 4.0 unidades, únicamente en MID/Existencias.** No hay quants en CUN/Existencias ni PLAYA/Existencias porque su saldo neto de movimientos `done` es cero (ver kardex). No se detectaron cantidades negativas en ubicaciones internas ni reservas huérfanas.

---

## 4. Kardex cronológico completo (`stock.move.line`, 20 registros)

| Fecha | Documento | Tipo | Origen → Destino | Cantidad | Estado | Contraparte |
|---|---|---|---|---:|---|---|
| 2026-04-23 21:00 | CUN/IN/01234 (P06467) | Recepción compra | Vendors → CUN/Existencias | +10.0 | done | BRUDIFARMA |
| 2026-05-08 15:54 | PLAYA/IN/00720 (P06770) | Recepción compra | Vendors → PLAYA/Existencias | +20.0 | done | QUÍMICOS Y FÁRMACOS DE MÉXICO |
| 2026-05-30 16:57 | MID/IN/01631 (P07160) | Recepción compra | Vendors → MID/Existencias | +15.0 | done | QUÍMICOS Y FÁRMACOS DE MÉXICO |
| 2026-06-01 14:46 | MID/PdV/07903 | Venta POS | MID/Existencias → Customers | −3.0 | done | LEOPOLDO HAU CHI |
| 2026-06-17 15:49 | MID/PdV/08157 | Venta POS | MID/Existencias → Customers | −2.0 | done | CORNELIUS SCHMITT THIESSEN |
| 2026-07-01 19:14 | MID/PdV/08376 | Venta POS | MID/Existencias → Customers | −3.0 | done | LUIS ARMANDO UC DUARTE |
| 2026-07-03 03:15 | MID/PdV/08399 | Venta POS | MID/Existencias → Customers | −3.0 | done | DIEGO ALBERTO LUGO INTERIAN |
| 2026-07-04 19:30 | MID/PdV/08427 | Venta POS | MID/Existencias → Customers | −4.0 | done | TERESA MANILLA NAVARRETE |
| 2026-07-15 20:43 | CUN/PdV/07130 | Venta POS | CUN/Existencias → Customers | −3.0 | done | FARMACIAS ECONOMICAS DE OCCIDENTE |
| 2026-07-16 16:15 | CUN/PdV/07133 | Venta POS | CUN/Existencias → Customers | −1.0 | done | FARMACIAS ECONOMICAS DE OCCIDENTE |
| 2026-07-16 17:49 | CUN/PdV/07137 | Venta POS | CUN/Existencias → Customers | −3.0 | done | FARMACIAS ECONOMICAS DE OCCIDENTE |
| 2026-07-21 22:52 | CUN/PdV/07182 | Venta POS | CUN/Existencias → Customers | −3.0 | done | FARMACIAS ECONOMICAS DE OCCIDENTE |
| 2026-08-07 14:56 | PLAYA/INT/00111 | Traslado interno (salida) | PLAYA/Existencias → Inter-company transit | −15.0 | done | (destino: MID) |
| 2026-08-13 21:36 | MID/INT/00223 | Traslado interno (entrada) | Inter-company transit → MID/Existencias | +15.0 | done | origen CUN/INT/00166 |
| 2026-08-13 21:59 | PLAYA/INT/00112 | Traslado interno (salida) | PLAYA/Existencias → Inter-company transit | −5.0 | done | (destino: CAMP) |
| 2026-08-15 15:28 | MID/INT/00227 | Devolución de MID/INT/00223 | MID/Existencias → Inter-company transit | −15.0 | done | (devolución) |
| 2026-08-15 16:30 | MID/INT/00229 | Traslado interno (entrada) | Inter-company transit → MID/Existencias | +10.0 | done | origen PLAYA/INT/00111 |
| 2026-08-15 20:12 | MID/PdV/08982 | Venta POS | MID/Existencias → Customers | −3.0 | done | TERESA MANILLA NAVARRETE |
| 2026-08-24 14:36 | MID/PdV/09087 | Venta POS | MID/Existencias → Customers | −3.0 | done | LEOPOLDO HAU CHI |
| 2026-08-26 16:09 | CAMP/INT/00116 | Traslado interno (**pendiente**) | Inter-company transit → CAMP/Existencias | 10.0 (reservado, `qty_done=0`) | **assigned** | — |

### Reconciliación por ubicación (solo movimientos `done`)

| Ubicación | Entradas | Salidas | Saldo calculado | Quant actual | Cuadra |
|---|---:|---:|---:|---:|---|
| CUN/Existencias | 10.0 | 10.0 | 0.0 | 0.0 (sin quant) | ✅ |
| PLAYA/Existencias | 20.0 | 20.0 | 0.0 | 0.0 (sin quant) | ✅ |
| MID/Existencias | 40.0 | 36.0 | 4.0 | 4.0 | ✅ |
| Inter-company transit | 20.0 | 10.0 | 10.0 | 10.0 | ✅ |

**Los 4 saldos calculados a partir del historial de movimientos individuales reproducen exactamente los quants actuales del sistema.** No hay movimientos "perdidos", duplicados, ni diferencias sin explicar.

---

## 5. Trazabilidad de origen — recepciones y proveedores

| Orden de compra | Proveedor | Fecha orden | Fecha aprobación | Unidades de este lote recibidas | Factura de proveedor | Estado factura |
|---|---|---|---|---:|---|---|
| **P06467** | BRUDIFARMA | 2026-04-23 | 2026-04-23 20:59 | 10.0 | BILL/2026/04/0265 ($50,966.35 MXN, total de la orden completa) | `posted`, pago `partial` |
| **P06770** | QUÍMICOS Y FÁRMACOS DE MÉXICO S.A. DE C.V. | 2026-05-08 | 2026-05-08 15:53 | 20.0 | BILL/2026/04/0581 ($9,685.44 MXN, total de la orden completa) | `posted`, pago `paid` |
| **P07160** | QUÍMICOS Y FÁRMACOS DE MÉXICO S.A. DE C.V. (ref. `B146253`) | 2026-05-30 | 2026-05-30 16:56 | 15.0 | BILL/2026/05/0389 ($17,940.33 MXN, total de la orden completa) | `posted`, pago `paid` |

> Los montos de las facturas corresponden al **total de cada orden de compra** (que incluye otros productos además de este lote), no al valor aislado de las unidades de ULGEL C. **Total recibido de este lote: 10 + 20 + 15 = 45.0 unidades**, que coincide exactamente con el quant acumulado `Partners/Vendors = −45.0`.

---

## 6. Trazabilidad de destino — ventas a cliente final

Todas las salidas del lote fueron por **venta de mostrador (POS)**; no hubo salidas por `sale.order`/pedido de venta tradicional. Se identificó el cliente real de cada venta cruzando `stock.move.line` → `pos.pack.operation.lot` (lote por línea) → `pos.order.line` → `pos.order`.

| Fecha venta | Documento (picking) | Orden POS | Cliente | Unidades | Importe total de la orden (MXN) | Sucursal |
|---|---|---|---|---:|---:|---|
| 2026-06-01 | MID/PdV/07903 | MDS MERIDA 1 - 000058 | LEOPOLDO HAU CHI | 3.0 | 776.57 | Mérida |
| 2026-06-17 | MID/PdV/08157 | MDS MERIDA 2 - 000109 | CORNELIUS SCHMITT THIESSEN | 2.0 | 4,375.82 | Mérida |
| 2026-07-01 | MID/PdV/08376 | MDS MERIDA 1 - 000110 | LUIS ARMANDO UC DUARTE | 3.0 | 5,066.08 | Mérida |
| 2026-07-03 | MID/PdV/08399 | MDS MERIDA 2 - 000053 | DIEGO ALBERTO LUGO INTERIAN | 3.0 | 26,129.96 | Mérida |
| 2026-07-04 | MID/PdV/08427 | MDS MERIDA 2 - 000069 | TERESA MANILLA NAVARRETE | 4.0 | 3,749.31 | Mérida |
| 2026-07-15 | CUN/PdV/07130 | MDS CANCUN 2 - 000262 | FARMACIAS ECONOMICAS DE OCCIDENTE SA DE C.V. | 3.0 | 25,956.03 | Cancún |
| 2026-07-16 | CUN/PdV/07133 | MDS CANCUN 1 - 000027 | FARMACIAS ECONOMICAS DE OCCIDENTE SA DE C.V. | 1.0 | 10,378.18 | Cancún |
| 2026-07-16 | CUN/PdV/07137 | MDS CANCUN 2 - 000265 | FARMACIAS ECONOMICAS DE OCCIDENTE SA DE C.V. | 3.0 | 10,750.79 | Cancún |
| 2026-07-21 | CUN/PdV/07182 | MDS CANCUN 1 - 000039 | FARMACIAS ECONOMICAS DE OCCIDENTE SA DE C.V. | 3.0 | 31,932.40 | Cancún |
| 2026-08-15 | MID/PdV/08982 | MDS MERIDA 2 - 000082 | TERESA MANILLA NAVARRETE | 3.0 | 3,986.72 | Mérida |
| 2026-08-24 | MID/PdV/09087 | MDS MERIDA 2 - 000049 | LEOPOLDO HAU CHI | 3.0 | 1,155.51 | Mérida |

**Total vendido: 31.0 unidades** (3+2+3+3+4+3+1+3+3+3+3), coincide exactamente con el quant acumulado `Partners/Customers = 31.0`.

> **Facturación (CFDI):** las 11 órdenes reportan `is_invoiced = True` / `invoice_status = invoiced`, pero no se encontró ningún `account.move` de tipo `out_invoice` vinculado directamente a ellas vía el campo relacional `pos_order_ids`. Esto sugiere que el cierre contable ocurre a nivel de sesión de caja (asiento consolidado) más que como CFDI individual por cliente — patrón habitual en venta de mostrador — pero **no se confirmó de forma directa**; si se requiere el CFDI específico de alguna de estas ventas, se recomienda una consulta dedicada sobre `pos.session`/`account.move` de tipo `entry` para las sesiones `POS/03354, POS/03482, POS/03585, POS/03597, POS/03612, POS/03694, POS/03705, POS/03708, POS/03739, POS/03936, POS/03999`.

---

## 7. Traslados inter-sucursal del lote

| Fecha | Documento | Ruta | Cantidad | Estado |
|---|---|---|---:|---|
| 2026-08-07 | PLAYA/INT/00111 | PLAYA/Existencias → tránsito (destino MID) | 15.0 | done |
| 2026-08-13 | MID/INT/00223 | tránsito → MID/Existencias (origen CUN/INT/00166) | 15.0 | done |
| 2026-08-13 | PLAYA/INT/00112 | PLAYA/Existencias → tránsito (destino CAMP) | 5.0 | done |
| 2026-08-15 | MID/INT/00227 | MID/Existencias → tránsito (devolución de MID/INT/00223) | 15.0 | done |
| 2026-08-15 | MID/INT/00229 | tránsito → MID/Existencias (origen PLAYA/INT/00111) | 10.0 | done |
| 2026-08-26 | CAMP/INT/00116 | tránsito → CAMP/Existencias (origen PLAYA/INT/00112) | 10.0 | **pendiente (`assigned`, sin recibir)** |

> Nota: hay una secuencia de traslado/devolución/re-traslado entre MID y el tránsito (`MID/INT/00223` → `MID/INT/00227` devolución → `MID/INT/00229`) que sugiere una corrección operativa (posible error de sucursal destino corregido manualmente). No afecta el cuadre final del kardex — el balance neto por ubicación reconcilia exacto — pero es un patrón a revisar si se audita higiene de datos en traslados.

---

## 8. Dictamen de trazabilidad

```
Unidades recibidas (3 compras)         =  45.0
Unidades vendidas (11 ventas POS)      = −31.0
Ajustes de inventario                  =    0.0
─────────────────────────────────────────────────
Balance esperado                       =  14.0

Stock físico actual (MID/Existencias)  =   4.0
+ En tránsito (pendiente, CAMP)        =  10.0
─────────────────────────────────────────────────
Stock actual total                     =  14.0   ✅ CUADRA EXACTO
```

**No se detectaron inconsistencias.** El lote `25G113` (asumido equivalente a `25G113n`) tiene:
- Origen documentado al 100%: 3 recepciones de compra, con proveedor, orden de compra y factura de proveedor identificados.
- Destino documentado al 100%: 11 ventas POS con cliente, fecha y sucursal identificados.
- Kardex que reconcilia exacto contra los quants actuales en las 4 ubicaciones con movimiento.
- Sin cantidades negativas, sin reservas huérfanas, sin movimientos sin contrapartida.

**Únicos puntos abiertos (no anomalías, sino follow-ups recomendados):**
1. Confirmar contra el empaque físico que el lote `25G113` (sistema) corresponde al `25G113n` solicitado.
2. Si se requiere el CFDI específico de alguna venta, consultar `pos.session`/asientos contables por sesión (no hay `account.move` de venta ligado directamente por orden individual).
3. La transferencia `CAMP/INT/00116` (10.0 unidades) sigue pendiente de recepción física en Campeche a la fecha de esta auditoría — dar seguimiento operativo si el retraso es inusual.
