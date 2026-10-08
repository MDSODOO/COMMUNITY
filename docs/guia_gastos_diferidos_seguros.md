# Guía operativa: Gastos diferidos en pólizas de seguros (Odoo 19 — Medicine Depot)

**Fecha de la auditoría:** 2026-08-26
**Instancia:** Odoo.sh producción (`https://medicinedepot.odoo.com/`, DB `medicinedepot-main-26466886`)
**Caso de referencia:** Factura AXA Seguros SA de CV, `BILL/2026/06/0533` (id 720185), $130,195.41 MXN en cuenta `182.01.02`.

---

## 1. Diagnóstico: por qué se borraban las fechas de vigencia

**La configuración global de la compañía NO tenía ningún problema.** Ya estaba (y está) correctamente parametrizada:

| Ajuste | Valor actual |
|---|---|
| Diario de gastos diferidos | `Miscellaneous Operations` (id 12, código `MISC`) |
| Cuenta transitoria de diferidos | `173.01.01 Deferred expenses` (activo circulante) |
| Método de generación | `on_validation` (genera los asientos al publicar la factura) |
| Prorrateo | `month` (mensual) |

La causa real del borrado fue **dónde se capturó el monto**: la línea de $130,195.41 se registró contra `182.01.02 Seguros pagados por anticipado` (cuenta de **activo/anticipo**), y ahí se intentó fijar el rango de vigencia. El motor de diferidos de Odoo 19 solo acepta `deferred_start_date`/`deferred_end_date` en la **línea de gasto** (`601.57.01`, tipo `expense`). Al capturarlas sobre una línea de activo, el sistema las limpia porque ese flujo no corresponde al diseño nativo de "Deferred Expenses".

> Nota técnica: en este build de Odoo 19, `account.account` **no tiene ningún campo de automatización de diferidos** (no existe la opción "Generar entradas diferidas: No / Al publicar / Manualmente" a nivel cuenta). Toda la automatización vive a nivel `res.company` (los 4 ajustes de la tabla de arriba) más el tipo de cuenta (`account_type`) de cada línea de la factura.

**No se requirió ninguna corrección de configuración.** El fix es 100% de proceso de captura.

### 1.1 Confirmación en vivo (2026-08-26, tras reporte de "aún se siguen borrando")

El equipo contable reportó que las fechas se seguían borrando después de recibir esta guía. Para descartar cualquier duda, se reprodujo el comportamiento en vivo, en una factura de prueba en borrador (creada y eliminada en el mismo momento, nunca posteada), con dos líneas idénticas salvo la cuenta:

| Línea de prueba | Cuenta | Resultado al capturar `01/07/2026 → 30/06/2027` (o rango equivalente) |
|---|---|---|
| A | `601.57.01 Seguros` (gasto) | **Persistió** — sobrevivió al cerrar el selector de fechas Y al guardar el borrador. |
| B | `182.01.02 Seguros pagados por anticipado` (activo) | **Se borró de inmediato**, apenas se cerró el selector de fechas — antes incluso de guardar. |

Esto confirma sin ambigüedad que la causa es el tipo de cuenta de la línea (`account_type`), no un tema de configuración, de timing (guardar vs. publicar) ni de ningún otro factor. **Si el problema persiste, es porque en algún punto de la captura todavía se está usando `182.01.02` (u otra cuenta que no sea de tipo gasto) para esa línea o para las fechas.**

### 1.2 ¿La distribución analítica segregada (multi-sucursal, con porcentaje) es también un problema?

**No.** Se probó en vivo una línea en `601.57.01` con distribución analítica segregada (20% Mérida / 80% Campeche, mismo patrón que una póliza compartida entre sucursales) y las fechas persistieron sin problema, incluso después de guardar. **No es necesario segregar la factura en registros separados por sucursal ni evitar la distribución analítica multi-cuenta — funciona igual de bien que una distribución de una sola sucursal, siempre que la cuenta de la línea sea `601.57.01`.**

Un caso reportado como "funciona en la línea de una sola sucursal pero no en la que tiene el porcentaje segregado" normalmente **no** es un problema de la distribución analítica en sí — es que esa línea segregada sigue usando `182.01.02` en vez de `601.57.01`. La distribución analítica (aunque esté partida entre varias sucursales) se puede dejar tal cual; lo único que hay que corregir es la cuenta contable de esa línea.

---

## 2. Cómo capturar correctamente una póliza de seguros diferida

### Regla de oro
> **El monto completo de la póliza se captura en UNA sola línea contra la cuenta de GASTO (`601.57.01`), nunca partido entre gasto y activo.** Las fechas de vigencia se capturan sobre esa misma línea de gasto.
>
> **La columna "Fecha diferida" NUNCA debe tocarse en una línea cuya cuenta sea `182.01.02` (o cualquier otra cuenta de activo/anticipo).** Confirmado en vivo: en esa cuenta, Odoo borra la fecha en cuanto se cierra el selector — es un comportamiento esperado del sistema, no una falla intermitente. Si al capturar la factura aparece una línea con `182.01.02`, hay que eliminarla o cambiarle la cuenta a `601.57.01` antes de intentar poner fechas.

### Paso a paso

1. Crear la factura de proveedor en borrador (Contabilidad ➔ Proveedores ➔ Facturas).
2. En la línea de la póliza, seleccionar la cuenta **`601.57.01 Seguros`** (no `182.01.02`).
3. Capturar el monto total de la póliza en esa línea (ej. $130,195.41).
4. En la columna **"Fecha diferida"**, capturar:
   - **Inicio:** primer día de vigencia (ej. `2026-07-01`)
   - **Fin:** último día de vigencia (ej. `2027-06-30`)
5. Guardar. Las fechas deben permanecer — si se capturaron sobre `601.57.01` no se borran.
6. Publicar la factura (**Confirmar**). Al publicarse (`generate_deferred_expense_entries_method = on_validation`), Odoo automáticamente:
   - Mueve el monto completo a la cuenta transitoria `173.01.01 Deferred expenses` (activo).
   - Genera un asiento de reconocimiento mensual (12 asientos para una póliza anual), cada uno con cargo a `601.57.01` y abono a `173.01.01`, prorrateado por mes calendario.
7. En la factura publicada aparece el botón inteligente **"Gastos diferidos"** — desde ahí se consulta la tabla de amortización completa y el estado de cada asiento mensual (borrador/publicado).

### Diferencia entre los dos métodos de captura

| | Método correcto (diferido automático) | Método manual antiguo (el que se venía usando) |
|---|---|---|
| Cuenta de captura | `601.57.01` (gasto), una sola línea | Partido entre `601.57.01` y `182.01.02` |
| Fechas de vigencia | Se capturan y persisten en la línea de gasto | Se intentaban en `182.01.02` → Odoo las borraba |
| Reconocimiento mensual | Automático, 12 asientos generados por Odoo al publicar | Manual — alguien tenía que recordar y contabilizar cada mes |
| Cuenta puente usada | `173.01.01 Deferred expenses` (config. de compañía) | `182.01.02` (elegida manualmente por el usuario, no reconocida por el motor) |

### ¿Y la cuenta `182.01.02`?

Se mantiene sin cambios en la configuración de diferidos (se evaluó moverla como cuenta transitoria oficial y se decidió **no hacerlo**, para no tocar un ajuste global ya funcional). Si en el futuro contabilidad prefiere que la cuenta transitoria visible sea `182.01.02` en vez de `173.01.01`, es un solo ajuste (`res.company.deferred_expense_account_id`) — avisar para prepararlo y aplicarlo con la aprobación correspondiente.

---

## 3. Sobre la factura de AXA ya registrada (id 720185)

Esta factura específica **se deja tal como está** — ya está posteada (documento fiscal validado) y no se modificó. La corrección de proceso descrita en esta guía aplica **a partir de la próxima factura** con el mismo patrón (pólizas de seguros u otros gastos con vigencia futura). Si contabilidad necesita reclasificar retroactivamente el monto de $130,195.41 hacia el esquema de diferidos automático, es una operación distinta (nota de crédito + reingreso) que debe evaluarse y autorizarse por separado, dado que implica modificar un documento fiscal ya validado.

---

## 4. Resumen para el equipo contable

- La opción de diferidos **ya estaba habilitada** en el sistema — no había que activar nada.
- El único cambio necesario es de **captura**: registrar el monto completo de la póliza en la cuenta de gasto (`601.57.01`), no partirlo con `182.01.02`.
- Las fechas de vigencia se capturan sobre esa línea de gasto y **no se deben tocar manualmente después de guardarlas** — Odoo se encarga del resto al publicar.
- El botón inteligente "Gastos diferidos" en la factura publicada es la fuente de verdad para consultar el calendario de amortización mensual.
