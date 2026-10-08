# Auditoría forense de inventario — Producto 7501361111501 / Documento P02477

**Instancia auditada:** `medicinedepot.odoo.com` (Odoo.sh, producción real — DB `medicinedepot-main-26466886`)
**Método:** XML-RPC (`/xmlrpc/2/common`, `/xmlrpc/2/object`), usuario `administradorodoo@medicinedepotsureste.mx`, API Key de sesión (no persistida en repositorio ni en memoria del asistente).
**Alcance de la sesión:** estrictamente **solo lectura** (`search_read`/`read`). No se ejecutó ninguna escritura sobre producción.
**Fecha de ejecución:** 2026-08-21.

---

## 1. Resumen ejecutivo

- **`P02477` NO es la causa del desajuste.** Es una cotización de compra (`purchase.order`) en estado `sent` (RFQ enviada a BRUDIFARMA, nunca confirmada), sin transferencias (`picking_ids = []`), sin facturas, `qty_received = 0`, `qty_invoiced = 0`. Ningún `stock.move` en todo el historial del producto referencia `P02477` en su origen. **No tocó el inventario físico ni una sola vez.**
- El saldo de sistema (`qty_available = 49.0`) **coincide exactamente** con la suma de los `stock.quant` en ubicaciones internas (`internal_sum = 49.0`). No hay reservas huérfanas (`reserved_quantity = 0` en todos los quants).
- **Sí existe una anomalía real**, pero es independiente de P02477: un `stock.quant` **negativo de -2.0 unidades** en `CUN/Existencias` (lote `45TA125`, empresa MDS CANCÚN). Se reconstruyó el kardex completo de ese lote/ubicación y el saldo calculado cuadra exactamente con el saldo negativo del sistema: **no es un bug de datos, es un déficit real** — las salidas por venta (POS) superaron en 2 unidades a las entradas recibidas para ese lote específico.
- Los 317 movimientos históricos del producto (`stock.move.line`, estado `done`) reconcilian al 100% contra los quants actuales en **todas** las ubicaciones (CHETU, MID, PLAYA, TICUL, CAMP, CUN). El único punto que no cierra en cero es CUN, y por la razón anterior — no por un movimiento perdido, duplicado o mal revertido.

**Dictamen: se descarta P02477 como origen del desajuste.**

---

## 2. Fase 1 — Identificación técnica y existencias

| Campo | Valor |
|---|---|
| `product.product.id` | 2160 |
| Nombre | TALCO PIES AMARILLO ENVASE C/150G (ODOLEX)(AVANT) |
| `default_code` / `barcode` | 7501361111501 |
| `categ_id` | Todos / Vendibles / COSMETICOS Y PERFUMERIA |
| `tracking` | `lot` (seguimiento por lote) |
| `cost_method` | `average` (AVCO) |
| `valuation` | `real_time` |
| `qty_available` (sistema) | 49.0 |
| `virtual_available` | 49.0 |

### Quants en ubicaciones internas (`usage='internal'`)

| Ubicación | Empresa | Lote | Cantidad | Reservado |
|---|---|---|---|---|
| CHETU/Existencias | MDS CHETUMAL | 49TA125 | 5.0 | 0 |
| CHETU/Existencias | MDS CHETUMAL | 12TA126 | 7.0 | 0 |
| CHETU/Existencias | MDS CHETUMAL | 18TA126 | 10.0 | 0 |
| MID/Existencias | SABRINA ELIZABETH ROJANO ROMERO | 10TA126 | 5.0 | 0 |
| MID/Existencias | SABRINA ELIZABETH ROJANO ROMERO | 15TA126 | 10.0 | 0 |
| PLAYA/Existencias | MDS PLAYA DEL CARMEN | 05TA126 | 5.0 | 0 |
| PLAYA/Existencias | MDS PLAYA DEL CARMEN | 18TA126 | 6.0 | 0 |
| TICUL/Existencias | MDS TICUL | 15TA126 | 3.0 | 0 |
| **CUN/Existencias** | **MDS CANCÚN** | **45TA125** | **-2.0** ⚠️ | 0 |

**Suma total = 49.0 = `qty_available`.** No hay reservas huérfanas reteniendo stock virtual.

> Nota lateral (no relacionada con P02477): varios lotes históricos de este producto llevan el sufijo `" Error"` en el nombre (ej. `01TA124 Error`, `44TA124 Error`), evidencia de una reconciliación manual previa de lotes mal registrados. No afecta el saldo actual — todos esos lotes ya están en cero — pero es una práctica de higiene de datos a revisar en otra auditoría si se desea.

---

## 3. Fase 2 — Documento P02477

| Campo | Valor |
|---|---|
| Modelo | `purchase.order` (no existe como `sale.order`) |
| `id` | 2499 |
| `state` | **`sent`** (RFQ enviada, nunca confirmada a `purchase`) |
| `partner_id` | BRUDIFARMA |
| `company_id` | MDS CANCÚN |
| `date_order` | 2025-07-15 |
| `date_approve` | `false` (nunca aprobada) |
| `picking_ids` | `[]` (ninguna transferencia generada) |
| `invoice_ids` | `[]` |
| Línea del producto 7501361111501 | `product_qty=33.0`, `qty_received=0.0`, `qty_invoiced=0.0` |
| `stock.move` con `origin like 'P02477'` | **0 resultados** |

**Conclusión de fase:** al quedar en `sent`, Odoo nunca generó `stock.picking` ni `stock.move` para esta orden — es estructuralmente imposible que haya afectado el inventario físico.

---

## 4. Fase 3 — Kardex forense

### 4.1 Reconciliación general por ubicación (317 `stock.move.line`, estado `done`)

Balance neto calculado (Σ entradas − Σ salidas) por ubicación vs. quant actual:

| Ubicación | Balance calculado (kardex) | Quant actual (sistema) | Cuadra |
|---|---:|---:|---|
| CHETU/Existencias | 22.0 | 22.0 | ✅ |
| MID/Existencias | 15.0 | 15.0 | ✅ |
| PLAYA/Existencias | 11.0 | 11.0 | ✅ |
| TICUL/Existencias | 3.0 | 3.0 | ✅ |
| CAMP/Existencias | 0.0 | 0.0 (sin quant) | ✅ |
| **CUN/Existencias** | **-2.0** | **-2.0** | ✅ (cuadra, pero es negativo) |

**El kardex reconstruido a partir de los movimientos individuales reproduce exactamente el saldo actual en las 6 ubicaciones internas.** No hay movimientos "perdidos" ni duplicados en ningún punto del historial de 317 líneas.

### 4.2 Kardex detallado — Lote 45TA125 en CUN/Existencias (origen del -2.0)

| Fecha | Documento | Tipo | Entrada | Salida | Saldo calculado |
|---|---|---|---:|---:|---:|
| 2025-12-19 21:06 | CUN/IN/00906 (P04607) | Recepción compra | 160.0 | | 160.0 |
| 2025-12-19 22:21 | CUN/PdV/04716 | Venta POS | | 80.0 | 80.0 |
| 2026-01-09 22:34 | CUN/PdV/04956 | Venta POS | | 80.0 | 0.0 |
| 2026-02-12 17:26 | CUN/IN/01024 (P05322) | Recepción compra | 240.0 | | 240.0 |
| 2026-02-12 22:01 | CUN/IN/01031 (P05338) | Recepción compra | 60.0 | | 300.0 |
| 2026-02-19 17:46 | CUN/PdV/05511 | Venta POS | | 1.0 | 299.0 |
| 2026-02-24 20:18 | CUN/PdV/05575 | Venta POS | | 80.0 | 219.0 |
| 2026-02-25 21:28 | CUN/PdV/05600 | Venta POS | | 10.0 | 209.0 |
| 2026-03-03 23:20 | CUN/PdV/05711 | Venta POS | | 3.0 | 206.0 |
| 2026-03-14 14:04 | CUN/PdV/05840 | Venta POS | | 2.0 | 204.0 |
| 2026-03-20 18:57 | CUN/PdV/05915 | Venta POS | | 80.0 | 124.0 |
| 2026-04-08 15:19 | CUN/PdV/06127 | Venta POS | | 5.0 | 119.0 |
| 2026-04-10 20:12 | Ajuste de inventario | Ajuste manual (+) | 4.0 | | 123.0 |
| 2026-04-16 16:43 | CUN/PdV/06193 | Venta POS | | 5.0 | 118.0 |
| 2026-04-24 14:36 | CUN/PdV/06289 | Venta POS | | 2.0 | 116.0 |
| 2026-05-05 21:27 | CUN/PdV/06399 | Venta POS | | 42.0 | 74.0 |
| 2026-05-13 20:07 | CUN/PdV/06486 | Venta POS | | 4.0 | 70.0 |
| 2026-05-19 16:30 | CUN/PdV/06528 | Venta POS | | 2.0 | 68.0 |
| 2026-05-27 18:00 | CUN/PdV/06621 | Venta POS | | 1.0 | 67.0 |
| 2026-05-30 16:05 | CUN/PdV/06647 | Venta POS | | 3.0 | 64.0 |
| 2026-05-30 19:04 | CUN/PdV/06652 | Venta POS | | 2.0 | 62.0 |
| 2026-06-03 17:50 | CUN/PdV/06691 | Venta POS | | 3.0 | 59.0 |
| 2026-07-03 22:25 | CUN/PdV/06997 | Venta POS | | 3.0 | 56.0 |
| 2026-07-09 16:24 | CUN/PdV/07073 | Venta POS | | 8.0 | 48.0 |
| 2026-08-12 19:37 | CUN/PdV/07399 | Venta POS | | 6.0 | 42.0 |
| 2026-08-19 18:17 | CUN/PdV/07462 | Venta POS | | 2.0 | 40.0 |
| 2026-08-19 22:28 | CUN/PdV/07465 | Venta POS | | 40.0 | 0.0 |
| 2026-08-19 22:28 | CUN/PdV/07465 (línea 2) | Venta POS | | 2.0 | **-2.0** |

**El saldo calculado línea por línea llega exactamente a -2.0, igual que el quant del sistema.** Las recepciones de este lote provienen de las órdenes de compra **P04607, P05322 y P05338** — ninguna es P02477.

### 4.3 Ajustes de inventario y pickings cancelados (contexto)

- Se identificaron 40 movimientos con origen/destino en ubicación de tipo `inventory` (ajustes manuales) para el producto en general; ninguno referencia `P02477`.
- Se identificaron 4 `stock.picking` cancelados históricamente ligados al producto, todos con origen en órdenes de venta (`S01403`, `S01823`, `S02256`, `S02850`) — ninguno relacionado con `P02477`.
- `stock.valuation.layer` no está expuesto/instalado para este usuario en esta instancia — no fue posible cruzar valoración contable en esta sesión (ver limitación abajo).

### 4.4 Determinación de causa raíz (checklist del plan original)

| Hipótesis | Resultado |
|---|---|
| a) Doble validación de líneas de recepción | ❌ Descartado — el kardex de 317 líneas reconcilia exactamente contra los quants, sin excedentes |
| b) Picking cancelado sin revertir quant | ❌ Descartado — los 4 cancelados no tocan CUN/lote 45TA125, y el balance ya cuadra sin ellos |
| c) Ajuste manual que enmascaró la falla original | ⚠️ Parcial — hubo un ajuste de +4 el 2026-04-10 en CUN, pero está **correctamente contabilizado** en el kardex; no oculta nada, solo pospuso el momento en que el déficit se manifestó |
| d) Movimiento a ubicación virtual/proveedor erróneo | ❌ Descartado — no se detectó ningún movimiento atípico hacia `Partners/Vendors` para este lote fuera de su devolución/recepción normal |
| **P02477 como origen** | ❌ **Descartado — cero movimientos de stock asociados, orden nunca confirmada** |

**Causa real del -2.0:** sobreventa acumulada del lote `45TA125` en el punto de venta de CUN. Entradas: 160 + 240 + 60 (compras) + 4 (ajuste manual) = **464 u.** Salidas: suma de las 24 ventas POS listadas en 4.2 = **466 u.** Déficit = 466 − 464 = **2 u.**, exactamente el quant negativo observado. Esto es compatible con una configuración que permite vender con stock insuficiente (venta sin bloqueo de disponibilidad), no con un error de sistema.

---

## 5. Fase 4 — Plan de remediación (propuesta, DRY-RUN)

**No se ejecutó ningún ajuste.** El siguiente script es una propuesta para regularizar el único punto real de desajuste (CUN/Existencias, lote 45TA125, -2.0 → 0.0), en modo `dry_run=True` por defecto.

```python
import xmlrpc.client, os

DRY_RUN = True  # cambiar a False solo tras validar en persona con el responsable de CUN

url = os.environ["ODOO_URL"]
db = os.environ["ODOO_DB"]
login = os.environ["ODOO_LOGIN"]
apikey = os.environ["ODOO_APIKEY"]

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, login, apikey, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

def execute(model, method, args, kwargs=None):
    return models.execute_kw(db, uid, apikey, model, method, args, kwargs or {})

QUANT_ID = 162756          # stock.quant negativo en CUN/Existencias, lote 45TA125
CANTIDAD_OBJETIVO = 0.0    # regularizar a cero (no se puede "verificar físicamente" un déficit)

if DRY_RUN:
    quant = execute("stock.quant", "read", [[QUANT_ID]],
                     {"fields": ["quantity", "location_id", "lot_id", "product_id"]})
    print("DRY-RUN — no se escribe nada. Quant actual:", quant)
    print(f"Se propondría fijar quantity={CANTIDAD_OBJETIVO} vía el asistente de "
          f"'Ajuste de inventario' de Odoo (inventory_quantity + apply), NO con write() directo "
          f"sobre stock.quant, para que genere el stock.move de ajuste correspondiente y quede "
          f"trazado en el kardex.")
else:
    # Vía Odoo, el ajuste correcto es a través de 'inventory_quantity' + acción 'action_apply_inventory',
    # no un write() directo a 'quantity' (que no genera movimiento ni trazabilidad).
    execute("stock.quant", "write", [[QUANT_ID], {"inventory_quantity": CANTIDAD_OBJETIVO}])
    execute("stock.quant", "action_apply_inventory", [[QUANT_ID]])
    print("Ajuste aplicado y trazado como movimiento de inventario.")
```

**Recomendación operativa (no técnica):** antes de aplicar el ajuste, confirmar con la sucursal CUN si físicamente falta ese producto/lote en anaquel, o si fue una venta legítima que el sistema permitió sin validar disponibilidad. Si se confirma sobreventa recurrente, evaluar activar el bloqueo de venta sin stock disponible para esta categoría en el POS de CUN.

---

## 6. Limitaciones de esta sesión

- `stock.valuation.layer` no existe/no está accesible para este usuario en esta instancia → no se pudo hacer el cruce financiero de valoración contable (punto 3.2 del plan original).
- Auditoría limitada al producto `7501361111501`; no se generalizó a otros productos con lotes `" Error"` (hallazgo lateral, fuera de alcance).
- Todo lo anterior se obtuvo en modo estrictamente lectura contra producción; no se aplicó ningún ajuste.
