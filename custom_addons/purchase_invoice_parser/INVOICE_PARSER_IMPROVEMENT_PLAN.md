# Plan de Mejoras: `purchase_invoice_parser`

> **Auditor:** Claude Code (Senior Odoo Software Architect)
> **Fecha:** 2026-05-19
> **Versión del módulo:** 19.0.2.2.0
> **Rama auditada:** `test`
> **Alcance:** Todos los archivos Python y XML del módulo.

---

## 1. Resumen Ejecutivo

El módulo `purchase_invoice_parser` es funcionalmente **maduro y correcto**. Implementa un flujo completo de importación de CFDI 4.0 con soporte para:

- Extracción de datos SAT (Emisor, Receptor, Conceptos, Impuestos IVA).
- Matching multi-estrategia de proveedor y producto.
- Lectura de Addenda BRUDIFARMA con lotes/caducidades.
- Extracción de lotes desde PDF (parser propio por proveedor).
- Flujo multi-factura vía ZIP.
- Asignación de impuestos con contexto multi-compañía.

La cobertura de pruebas automatizadas es **notable** (936 líneas de tests) y cubre los flujos críticos.

Sin embargo, la evolución orgánica del módulo ha acumulado **deuda técnica significativa**. El wizard principal creció hasta ~1 100 líneas y concentra responsabilidades que deberían estar en servicios independientes. Existen duplicaciones de código, funciones anidadas, queries N+1 y varias superficies de fragilidad ante datos inesperados.

**Estado global:** Funcional y estable para producción. Escalabilidad y mantenibilidad comprometidas. Deuda técnica media-alta.

---

## 2. Hallazgos y Riesgos Críticos

### 2.1 God Object — Wizard de 1 100 líneas

**Archivo:** `models/purchase_invoice_import_wizard.py`

El wizard concentra: parseo de XML, orquestación de servicios, lógica de impuestos, creación de OC, adjuntos, resúmenes HTML y gestión de estado ZIP. Viola el Principio de Responsabilidad Única.

**Riesgos:**
- Bugs difíciles de aislar sin ejecutar toda la cadena.
- Extensibilidad forzada a tocar un archivo monolítico.
- Pruebas de integración pesadas donde se necesitan pruebas unitarias.

---

### 2.2 Funciones Anidadas Antipatrón

**Archivo:** `models/purchase_invoice_import_wizard.py`, líneas 407–499

`pick_purchase_tax()` y `get_tax()` están declaradas dentro de `action_create_purchase_order()`. No pueden ser testeadas de forma aislada ni reutilizadas desde otros métodos del mismo wizard.

```python
# Problema: funciones definidas dentro de un método de 180 líneas
def action_create_purchase_order(self):
    def pick_purchase_tax(candidates, expect_exento=False):  # No testeable
        ...
    def get_tax(tasa, factor='', iva_presente=True):         # No testeable
        ...
```

---

### 2.3 RFC Hardcodeado en Múltiples Lugares

El RFC de BRUDIFARMA (`'BRU971010227'`) aparece en **cuatro archivos distintos**, con una sola declaración como constante de clase (`ProductMatcher.BRUDIFARMA_RFC`) y tres como literales:

| Archivo | Línea | Forma |
|---------|-------|-------|
| `models/purchase_invoice_import_wizard.py` | 207 | Literal `'BRU971010227'` |
| `models/purchase_invoice_import_wizard.py` | 917 | Literal `'BRU971010227'` |
| `services/product_matcher.py` | 15 | `BRUDIFARMA_RFC = 'BRU971010227'` |
| `services/addenda_parsers.py` | 38 | `rfc = 'BRU971010227'` |

**Riesgo:** Un cambio de RFC (posible por fusión/escisión del proveedor) requiere actualizar 4 archivos con riesgo de olvidar uno.

---

### 2.4 Queries N+1 en Bucles de Lotes

**Archivos:** `models/purchase_invoice_import_wizard.py`

#### En `_do_parse_pdf()` (líneas 957–994):
```python
for line in self.line_ids:
    for lot_vals in lots:
        existing = StockLot.search([...], limit=1)  # 1 query por lote
        self.env['purchase.invoice.import.wizard.lot'].create({...})  # 1 query
```
Con una factura de 50 productos y 2 lotes cada uno: **~200 queries DB**.

#### En `_do_populate_addenda_lots()` (líneas 757–778):
```python
for line in self.line_ids:
    for addenda_lot, lot_qty in aggregated_line_lots:
        existing = self._find_existing_stock_lot(...)  # 1-2 queries por lote
        self.env['...lot'].create({...})               # 1 query
```

**Solución:** Pre-cargar todos los `stock.lot` candidatos con una sola query y construir un dict de lookup en memoria antes del bucle.

---

### 2.5 Código Muerto — `tax_warnings` Nunca Poblado

**Archivo:** `models/purchase_invoice_import_wizard.py`, líneas 405 y 637–642

```python
tax_warnings = []  # Línea 405: se inicializa
# ... 232 líneas sin ningún tax_warnings.append(...)
if tax_warnings:   # Línea 637: condición siempre False
    items = ''.join(...)
    body += ...
```

Este bloque HTML nunca se ejecuta. Es código muerto que confunde al lector.

---

### 2.6 Doble Escritura de Impuestos Post-Creación de OC

**Archivo:** `models/purchase_invoice_import_wizard.py`, líneas 606–615

Después de `po = create({...})`, el código itera nuevamente sobre las líneas para reescribir `tax_ids`. El comentario reconoce que Odoo recalcula los impuestos durante `create()`. Esto es un workaround frágil.

**Riesgo:** Si Odoo cambia el comportamiento de `create()` o si se actualiza el módulo `purchase`, el doble-write puede introducir comportamientos inesperados.

**Alternativa recomendada:** Crear las líneas sin `tax_ids` y escribirlas en un paso separado con `with_context(no_recompute=True)` o usar `write()` post-creación de forma explícita.

---

### 2.7 Duplicación de Código entre PDF Parser y Addenda Parser

**Archivos:** `services/pdf_lot_provider.py` y `services/addenda_parsers.py`

El método `_clean_lot_name()` y el regex `_LOT_CADUCIDAD_TRAIL_RE` están duplicados en ambos archivos con implementaciones idénticas:

```python
# addenda_parsers.py línea 11:
_LOT_CADUCIDAD_TRAIL_RE = re.compile(r'(?i)\s*fecha(?:\s+de)?\s+caducidad.*$')

# pdf_lot_provider.py línea 67:
_BRUDIFARMA_LOT_CADUCIDAD_TRAIL_RE = re.compile(r'(?i)\s*fecha(?:\s+de)?\s+caducidad.*$')
```

**Riesgo:** Un ajuste del regex en un archivo no se propaga al otro, generando comportamiento divergente.

---

### 2.8 No se Valida la Versión del CFDI

**Archivo:** `services/cfdi_parser.py`

El parser no verifica el atributo `Version` del CFDI. Un CFDI 3.3 (estructura diferente) sería procesado sin advertencia, produciendo datos incorrectos silenciosamente.

```python
# Falta esta validación:
version = root.get('Version')
if version and version != '4.0':
    doc.parse_errors.append(f"Versión CFDI no soportada: {version}. Se esperaba 4.0.")
```

---

### 2.9 XSS Potencial en HTML Generado en Python

**Archivo:** `models/purchase_invoice_import_wizard.py`, `_do_populate_addenda_lots()`

Los nombres de lotes se insertan directamente en cadenas HTML sin escapar:
```python
# Línea 782-818: construcción de summary_parts con f-strings
f"<p><b>Lotes en Addenda:</b> {total_lots}</p>",
```

Aunque los contadores son enteros (sin riesgo), si en el futuro se insertan strings del proveedor (como nombres de lotes), habría riesgo XSS. El import de `escape` existe en el wizard pero solo se usa en `_build_zip_pair_summary`.

---

### 2.10 No se Manejan IEPS ni Retenciones

**Archivo:** `services/cfdi_parser.py`, `_parse_concepto()`

El módulo solo extrae el Traslado con `Impuesto == '002'` (IVA). En el sector farmacéutico mexicano es común encontrar:

- **IEPS** (`Impuesto == '003'`): Aplicable a medicamentos con ciertas características.
- **Retenciones** (`cfdi:Retenciones`): ISR/IVA retenido por el receptor.

Ambos se ignoran silenciosamente, lo que puede causar descuadres contables.

---

### 2.11 Búsqueda de Lotes Existentes con `ilike` (Falsos Positivos)

**Archivo:** `models/purchase_invoice_import_wizard.py`, `_find_existing_stock_lot()`, línea 896–902

```python
candidates = stock_lot_model.search(
    base_domain + [('name', 'ilike', compact)],  # ilike = contiene
    limit=25,
)
for candidate in candidates:
    if self._compact_lot_code(candidate.name) == compact:
        return candidate
```

`ilike` no es exacto — devuelve todos los lotes que **contienen** `compact`. Si el lote buscado es `6092`, se devolverán lotes con nombres `6092`, `06092`, `160920`, `ABC6092`, etc. El filtro en Python evita falsos positivos finales, pero los 25 candidatos pueden no incluir el lote correcto si hay más de 25 nombres que contengan el substring.

**Alternativa:** Usar `('name', '=', compact)` en la segunda búsqueda.

---

### 2.12 `pdf_lot_parser.py` es un Shim Sin Documentación de Depreciación

**Archivo:** `services/pdf_lot_parser.py`

```python
def parse_lots_by_article(pdf_bytes):
    """Shim de compatibilidad: conserva la API historica del modulo."""
    return get_provider('generic').parse(pdf_bytes)
```

Este archivo existe solo por compatibilidad con código antiguo. No hay indicación de cuándo será eliminado ni qué módulos externos podrían estar importándolo.

---

### 2.13 Sin Validación de Tamaño de Archivos

**Archivo:** `models/purchase_invoice_import_wizard.py`

No existe ninguna validación del tamaño de los archivos cargados (XML, PDF, ZIP). Un ZIP de 100 MB con decenas de facturas se procesaría completamente en memoria, potencialmente causando OOM en el servidor Odoo.

---

### 2.14 Estado del ZIP como JSON en Campo `Text`

Los campos `zip_remaining_pairs_json` y `zip_created_po_ids_json` almacenan listas JSON-encoded como `fields.Text`. Cada par XML/PDF se serializa a base64 completo antes de guardarse. Para ZIPs con muchos archivos grandes, esto podría exceder límites de tamaño de campo en la BD o generar registros `ir.attachment` implícitamente grandes.

---

### 2.15 `SupplierMatcher` Sin Filtro de Compañía

**Archivo:** `services/supplier_matcher.py`

La búsqueda de proveedor por RFC no incluye filtro de compañía:
```python
partner = Partner.search(
    [('vat', '=ilike', rfc), ('supplier_rank', '>', 0)],
    limit=1,
)
```

En un entorno multi-compañía, puede devolver un proveedor de otra compañía. Debería filtrarse por `company_id` o `company_ids` dependiendo de la configuración del entorno.

---

## 3. Propuesta de Refactorización

### 3.1 Patrón Recomendado: Servicio de Creación de OC

Extraer la lógica de `action_create_purchase_order()` a un servicio independiente `purchase_order_builder.py`:

```
services/
├── cfdi_parser.py          (sin cambios)
├── addenda_parsers.py      (consolidar con shared_utils)
├── product_matcher.py      (sin cambios)
├── supplier_matcher.py     (añadir filtro compañía)
├── pdf_lot_provider.py     (sin cambios)
├── zip_extractor.py        (sin cambios)
├── purchase_order_builder.py  [NUEVO] ← lógica de creación de OC
├── tax_resolver.py            [NUEVO] ← lógica de resolución de impuestos
└── lot_stock_resolver.py      [NUEVO] ← búsqueda/creación de stock.lot en batch
```

**Responsabilidades:**
- `PurchaseOrderBuilder`: Recibe un `CFDIDocument` + wizard lines y produce un `purchase.order`. Contiene la lógica de mapeo de campos, validaciones de negocio y adjuntos.
- `TaxResolver`: Encapsula `get_tax()` y `pick_purchase_tax()`. Cacheable por compañía.
- `LotStockResolver`: Pre-carga todos los `stock.lot` candidatos en una sola query y resuelve existencias en memoria (elimina N+1).

### 3.2 Registry Pattern para Addenda (ya existe — ampliar)

El sistema `_ADDENDA_PARSERS` es el patrón correcto. Para escalar a nuevos proveedores:

```python
# addenda_parsers.py — patrón de auto-registro
class AddendaParserRegistry:
    _parsers: dict[str, BaseAddendaParser] = {}

    @classmethod
    def register(cls, parser_class):
        instance = parser_class()
        cls._parsers[instance.rfc] = instance
        return parser_class

    @classmethod
    def get(cls, rfc: str) -> Optional[BaseAddendaParser]:
        return cls._parsers.get((rfc or '').upper())

@AddendaParserRegistry.register
class BrudifarmaAddendaParser(BaseAddendaParser):
    rfc = 'BRU971010227'
    ...
```

Esto permite agregar nuevos parsers de Addenda sin tocar `get_addenda_parser()`.

### 3.3 Constante Centralizada de RFCs Conocidos

```python
# services/known_rfcs.py  [NUEVO]
class KnownRFC:
    BRUDIFARMA = 'BRU971010227'
    # Agregar aquí nuevos proveedores con tratamiento especial
```

Todos los archivos importarían desde aquí, eliminando los literales dispersos.

### 3.4 Refactorizar `_find_existing_stock_lot` con Búsqueda Exacta

```python
# Paso 1: búsqueda exacta (actual — correcto)
existing = stock_lot_model.search(base_domain + [('name', '=ilike', lot_name)], limit=1)
if existing:
    return existing

# Paso 2: búsqueda exacta del código compacto (REEMPLAZAR ilike por =)
compact = self._compact_lot_code(lot_name)
if compact and compact != lot_name:
    existing = stock_lot_model.search(base_domain + [('name', '=ilike', compact)], limit=1)
    if existing:
        return existing
return stock_lot_model.browse()
```

### 3.5 Batch Pre-carga de `stock.lot` para Eliminar N+1

```python
# LotStockResolver.resolve_lots(lines, company_id) → dict[str, stock.lot]
# Pre-carga todos los lotes relevantes en una query:
all_lot_names = {lot.name for line in lines for lot in line.lot_ids}
existing_lots = StockLot.search([
    ('name', 'in', list(all_lot_names)),
    ('company_id', 'in', [company_id, False]),
])
by_name = {lot.name.strip(): lot for lot in existing_lots}
# Luego: by_name.get(lot_name) en lugar de search() por lote
```

### 3.6 Consolidar Utilidades Compartidas entre Parsers

Crear `services/lot_utils.py` con:
- `LOT_CADUCIDAD_TRAIL_RE` (único punto de definición)
- `clean_lot_name(raw: str) -> str` (función compartida)
- `parse_date(day_s, mon_s, year_s) -> Optional[date]` (mover desde `pdf_lot_provider.py`)

---

## 4. Roadmap de Ejecución

### Fase 1: Correcciones de Seguridad y Bugs (Prioridad: Crítica)

**Objetivo:** Eliminar los riesgos funcionales sin refactorizar la arquitectura.

1. **[F1-01]** Añadir validación de versión CFDI en `cfdi_parser.py`.
   - Verificar `root.get('Version') == '4.0'`; emitir `parse_error` si no coincide.

2. **[F1-02]** Aplicar `escape()` a todos los strings de proveedor en `_do_populate_addenda_lots()` y `_do_parse_pdf()` antes de insertar en HTML.

3. **[F1-03]** Eliminar el código muerto de `tax_warnings` (inicialización en línea 405 y bloque condicional en líneas 637–642).

4. **[F1-04]** Corregir la búsqueda fuzzy de `_find_existing_stock_lot` — reemplazar el `ilike` del paso 2 por `=ilike` exacto sobre el código compacto.

5. **[F1-05]** Añadir validación de tamaño de archivos en `action_parse_xml`, `action_parse_pdf` y `action_parse_zip`. Sugerencia: límite configurable vía `ir.config_parameter`, default 10 MB.

6. **[F1-06]** Añadir filtro de compañía en `SupplierMatcher.find_partner()` usando `company_id` del contexto o pasado como parámetro.

---

### Fase 2: Deduplicación y Limpieza (Prioridad: Alta)

**Objetivo:** Eliminar duplicaciones DRY y centralizar constantes.

7. **[F2-01]** Crear `services/lot_utils.py` con `LOT_CADUCIDAD_TRAIL_RE`, `clean_lot_name()` y `parse_date()`. Actualizar `addenda_parsers.py` y `pdf_lot_provider.py` para importar desde aquí.

8. **[F2-02]** Crear `services/known_rfcs.py` con `KnownRFC.BRUDIFARMA = 'BRU971010227'`. Reemplazar todos los literales en el wizard y `product_matcher.py`.

9. **[F2-03]** Deprecar formalmente `services/pdf_lot_parser.py`: añadir docstring de depreciación con fecha objetivo y verificar que ningún módulo externo lo importe antes de eliminarlo.

10. **[F2-04]** Extraer `pick_purchase_tax()` y `get_tax()` como métodos privados de la clase `PurchaseInvoiceImportWizard` (o mejor, del nuevo `TaxResolver` en Fase 3). Esto los hace testeables en aislamiento.

11. **[F2-05]** Documentar la dependencia condicional con `lot_selection` (el módulo que añade `lot_id` a `purchase.order.line`). Centralizar el flag `has_lot_fields` como propiedad del wizard, no como variable local.

---

### Fase 3: Extracción de Servicios (Prioridad: Media)

**Objetivo:** Reducir el wizard a orquestador puro, delegando lógica a servicios.

12. **[F3-01]** Crear `services/tax_resolver.py` con clase `TaxResolver(env, company)`.
    - Métodos: `resolve(tasa, factor, iva_presente) -> account.tax`.
    - Mantiene el caché interno por instancia.
    - El wizard crea una instancia en `action_create_purchase_order` y la pasa a cada línea.

13. **[F3-02]** Crear `services/lot_stock_resolver.py` con clase `LotStockResolver(env, company_id)`.
    - Método: `preload(lot_names: list[str])` — ejecuta una sola query.
    - Método: `find(product, lot_name) -> stock.lot | False`.
    - Método: `ensure(product, lot_name, expiration_date) -> stock.lot` — crea si no existe.
    - Elimina el patrón N+1 en `_do_parse_pdf` y `_do_populate_addenda_lots`.

14. **[F3-03]** Crear `services/purchase_order_builder.py` con clase `PurchaseOrderBuilder(env, wizard)`.
    - Recibe el wizard ya en estado `review`.
    - Método `build() -> purchase.order`: crea la OC, escribe los impuestos post-creación, adjunta archivos y postea el mensaje chatter.
    - El wizard llama `PurchaseOrderBuilder(self.env, self).build()`.

15. **[F3-04]** Añadir `AddendaParserRegistry` con decorador `@register` como se describe en §3.2.

---

### Fase 4: Mejoras de Robustez del Parser (Prioridad: Media-Baja)

**Objetivo:** Hacer el parseo más robusto ante datos inesperados.

16. **[F4-01]** Soportar múltiples Traslados por Concepto en `cfdi_parser.py`. Extraer una lista de traslados (`tasa_iva`, `importe_iva`, `factor_iva`, `impuesto`) en lugar de solo el primer IVA.

17. **[F4-02]** Detectar y registrar nodos `cfdi:Retenciones` en `CFDIDocument` (campo `retenciones: list`). No es necesario procesarlos en la OC de inmediato — basta con registrar su presencia como `parse_warnings`.

18. **[F4-03]** Añadir soporte básico para IEPS (Impuesto 003) en el wizard. Si una línea tiene IEPS, emitir un aviso al usuario para revisión manual.

19. **[F4-04]** Reemplazar el truncado de fecha `(root.get('Fecha') or '')[:10]` por un parseo robusto con `datetime.fromisoformat()` en un bloque try/except.

20. **[F4-05]** Considerar migrar `xml.etree.ElementTree` a `lxml.etree` para mejor manejo de namespaces, validación de schema SAT y rendimiento en archivos grandes. Requiere añadir `lxml` como dependencia en `__manifest__.py`.

---

### Fase 5: Mejoras de UX y Observabilidad (Prioridad: Baja)

**Objetivo:** Mejorar la experiencia del operador y la trazabilidad de problemas.

21. **[F5-01]** Añadir `@api.onchange('target_company_id')` en el wizard para notificar al usuario que cambiar la compañía destino después del parseo puede invalidar la resolución de impuestos.

22. **[F5-02]** Agregar campo `cfdi_version` al wizard (o solo a `CFDIDocument`) para mostrar la versión del CFDI al usuario en la vista de revisión.

23. **[F5-03]** Exponer el proveedor PDF activo (`provider_key`) como campo readonly en la vista del wizard durante el estado `review`, para facilitar el diagnóstico cuando el parseo falla.

24. **[F5-04]** Agregar validación de duplicados de UUID CFDI: antes de crear la OC, verificar si ya existe una OC con el mismo UUID en `partner_ref` o en un campo dedicado. Emitir advertencia (no bloqueo) si se detecta duplicado.

25. **[F5-05]** Considerar agregar un campo `import_log_ids` (One2many a un modelo ligero) o aprovechar el chatter del wizard para registrar cada decisión del motor de matching (proveedor, producto, impuesto). Actualmente esta información se pierde al cerrar el wizard.

---

## 5. Métricas de Éxito del Plan

| Métrica | Estado Actual | Objetivo Post-Fase 3 |
|---------|--------------|----------------------|
| Líneas en wizard principal | ~1 100 | < 400 |
| Queries por factura de 50 líneas (addenda) | ~200 | < 15 |
| Archivos con RFC hardcodeado | 4 | 1 (known_rfcs.py) |
| Código duplicado (limpieza_lote + regex) | 2 archivos | 0 (shared utils) |
| Tests de servicios isolados | 0 | ≥ 5 por servicio nuevo |
| Cobertura de advertencia CFDI no-4.0 | No existe | 100% |

---

## Notas Adicionales sobre Terminología

Regla de negocio aplicada en este documento y en el código:

- ✅ **"A la mano"** → para referirse a existencias físicas en almacén (`stock.quant`, `stock.lot`).
- ❌ ~~"Disponible"~~ → no usar para cantidades físicas en sistema.

Esta regla ya está correctamente implementada en el código actual (ver `_do_populate_addenda_lots`, línea 783: `"A la mano en sistema:"` y línea 818: `"✓ Todos los lotes ya están a la mano."`). El plan de mejoras debe mantener esta convención en todo texto generado dinámicamente.

---

*Documento generado por auditoría estática. No implica modificaciones al código. Listo para ejecución por fases.*
