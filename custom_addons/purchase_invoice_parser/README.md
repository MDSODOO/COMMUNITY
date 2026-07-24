# purchase_invoice_parser — Crear Órdenes de Compra desde CFDI XML

**Versión:** 19.0.2.1.0
**Autor:** Zorakode, Medicine Depot
**Odoo:** 19.0
**Licencia:** LGPL-3
**Depende:** `purchase`, `stock`, `mail`

> **Versión original:** 19.0.2.0.0
> **Versión refactorizada:** 19.0.2.1.0 (ZIP + Multi-proveedor)
> **Última actualización:** 2026-05-04
> **Revisado por:** Claude Code (Análisis Arquitectónico)

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura Técnica](#arquitectura-técnica)
3. [Formatos de Entrada Soportados](#formatos-de-entrada-soportados)
4. [Guía de Instalación y Configuración](#guía-de-instalación-y-configuración)
5. [Uso: Flujos del Módulo](#uso-flujos-del-módulo)
6. [Validación Post-Despliegue](#validación-post-despliegue)
7. [Limitaciones Conocidas](#limitaciones-conocidas)
8. [Extensiones Sugeridas](#extensiones-sugeridas)
9. [Glosario Técnico](#glosario-técnico)
10. [Changelog](#changelog)

---

## Resumen Ejecutivo

### ¿Qué hace?

El módulo **automatiza la creación de órdenes de compra a partir de facturas electrónicas CFDI** (estándar SAT México):

1. **Carga de facturas:** Usuario sube XML CFDI (obligatorio) + PDF (opcional para lotes)
2. **Parseo:** Extrae datos del emisor, conceptos, impuestos, UUID fiscal
3. **Matching automático:** Busca proveedor (por RFC) y productos (por barcode/código/nombre)
4. **Extracción de lotes:** Si hay PDF, identifica lotes y caducidades en el documento
5. **Revisión interactiva:** Usuario ajusta matches si es necesario
6. **Creación de OC:** Genera `purchase.order` con líneas, lotes, impuestos, adjuntos

### Novedad: Soporte ZIP y Multi-proveedor (v19.0.2.1.0)

- ✅ **ZIP Upload:** Usuario sube un `.zip` con múltiples XML+PDF → sistema procesa secuencialmente
- ✅ **Multi-proveedor:** Diferentes proveedores pueden tener diferentes formatos de lotes en PDF → perfiles configurables

### Impacto empresarial

| Aspecto | Antes | Después |
|--------|-------|---------|
| **Tiempo por factura** | 10-15 min (manual) | 2-3 min (1 clic + revisión) |
| **Errores de tipeo** | Frecuentes | Eliminados (matching automático) |
| **Lotes en PDF** | Copia manual | Extrae automáticamente |
| **Múltiples facturas** | Repetir flujo N veces | Cargar ZIP único, procesa todas |

---

## Arquitectura Técnica

### 2.1 Estructura de Archivos

```
purchase_invoice_parser/
├── __manifest__.py
│   └── Metadatos, versión 19.0.2.1.0, depende de [purchase, stock, mail]
│       python: pypdf (pdfplumber opcional)
│
├── models/
│   ├── __init__.py
│   │   └── import purchase_invoice_import_wizard, provider_profile
│   │
│   ├── purchase_invoice_import_wizard.py       ← 420 líneas, 3 modelos transientes
│   │   ├─ PurchaseInvoiceImportWizard (wizard principal, máquina de estados)
│   │   ├─ PurchaseInvoiceImportWizard.Line (una línea por Concepto CFDI)
│   │   └─ PurchaseInvoiceImportWizard.Lot (un lote por extracción PDF)
│   │
│   └── provider_profile.py                     ← NUEVO: campo en res.partner
│       └─ ResPartnerProviderProfile (hereda res.partner, agrega pdf_lot_provider_key)
│
├── services/
│   ├── __init__.py
│   │
│   ├── cfdi_parser.py                          ← XML CFDI → CFDIDocument
│   │   ├─ CFDIParser.parse_bytes(xml_bytes)
│   │   ├─ CFDIParser._extract(ET.Element)
│   │   ├─ CFDIParser._parse_concepto(ET.Element)
│   │   ├─ @dataclass CFDIDocument
│   │   └─ @dataclass CFDILine
│   │
│   ├── supplier_matcher.py                     ← RFC/nombre → res.partner (confianza)
│   │   └─ SupplierMatcher.find_partner(rfc, nombre)
│   │
│   ├── product_matcher.py                      ← barcode/código/nombre → product.product (confianza)
│   │   └─ ProductMatcher.find_product(no_id, desc, partner_id)
│   │
│   ├── pdf_lot_parser.py                       ← Shim (delega a pdf_lot_provider)
│   │   ├─ parse_lots_by_article(pdf_bytes)    ← llama get_provider('generic').parse()
│   │   └─ diagnose(pdf_bytes, max_chars)      ← llama get_provider('generic').diagnose()
│   │
│   ├── pdf_lot_provider.py                     ← NUEVO: estrategia de parseo (3 formatos)
│   │   ├─ class LotParserProvider (ABC)
│   │   ├─ class GenericProvider (3 regexes)
│   │   ├─ class QuifamesaProvider (slash-first)
│   │   ├─ get_provider(key: str) → LotParserProvider
│   │   └─ available_providers() → [(key, display_name), ...]
│   │
│   └── zip_extractor.py                        ← NUEVO: ZIP → pares XML↔PDF
│       ├─ class ZipExtractor
│       │   └─ extract(zip_bytes) → ZipContents
│       ├─ @dataclass ZipContents
│       │   └─ pair_xml_pdf(cfdi_docs) → [XmlPdfPair]
│       └─ @dataclass XmlPdfPair
│
├── views/
│   ├── purchase_invoice_import_wizard_views.xml  ← Formulario del wizard
│   │   ├─ upload state: radio (individual|zip) + file widgets
│   │   ├─ review state: datos CFDI + líneas + lotes + indicador ZIP
│   │   └─ botones: action_parse_xml, action_parse_zip, action_create_purchase_order
│   │
│   └── purchase_order_views.xml                  ← Hereda views PO
│       └─ Botón "Importar XML" en ir.actions.act_window
│
├── security/
│   └── ir.model.access.csv                      ← ACLs de modelos transientes
│       └─ purchase.group_purchase_user: CRUD en wizard models
│
├── tests/
│   └── test_purchase_invoice_import_wizard.py   ← 4 tests existentes + 10+ nuevos
│       ├─ TestZipExtractor (sin DB)
│       ├─ TestLotParserProvider (sin DB)
│       └─ TestWizardZipFlow (con DB)
│
└── README.md (este archivo)
```

### 2.2 Flujo Principal (Diagrama)

```
User abre lista de OCs
  │
  ├─ Botón "Importar XML" → Abre wizard
  │
  Wizard: ESTADO = 'upload'
  ┌─────────────────────────────────────┐
  │ [○] Archivos individuales           │
  │ [●] ZIP del proveedor               │
  │                                     │
  │ Subir ZIP: [file]                   │
  │                                     │
  │ [Importar ZIP]                      │
  └─────────────────────────────────────┘
         │
         ├─ action_parse_zip() O action_parse_xml()
         │    ├─ ZipExtractor.extract() O CFDIParser.parse_bytes()
         │    ├─ SupplierMatcher.find_partner()
         │    ├─ ProductMatcher.find_product() × N líneas
         │    └─ _load_pair(xml_bytes, pdf_bytes)
         │
  Wizard: ESTADO = 'review'
  ┌─────────────────────────────────────┐
  │ Factura 1 de 5                      │
  │ UUID: a1b2c3d4-...                  │
  │ Folio: A-1234                       │
  │ Fecha: 2026-04-29                   │
  │ Proveedor: PROVEEDOR001 (RFC)       │
  │ Confianza: 100%                     │
  │                                     │
  │ Conceptos:                          │
  │ ┌───┬──────────┬─────────┬─────────┐│
  │ │ # │Producto  │Cantidad │Lotes    ││
  │ ├───┼──────────┼─────────┼─────────┤│
  │ │ 1 │Prod X    │100      │LOT-001  ││
  │ │   │(95% conf)│         │(Found)  ││
  │ └───┴──────────┴─────────┴─────────┘│
  │                                     │
  │ [Ajustar] [Crear OC]                │
  └─────────────────────────────────────┘
         │
         ├─ action_create_purchase_order()
         │    ├─ Valida partner_id ≠ False
         │    ├─ Para cada línea:
         │    │   ├─ Busca tax por IVA %
         │    │   ├─ Si hay lotes: SPLIT → 1 línea OC por lote
         │    │   └─ Sino: 1 línea OC total
         │    ├─ Crea purchase.order
         │    ├─ Adjunta XML + PDF
         │    └─ Chatter: UUID + RFC
         │
  [ZIP MODE] Si hay más pares:
  Carga siguiente par → regresa a 'review'
  Si es último: state='done'
         │
  Wizard: ESTADO = 'done' (redirige a OC)
  ┌─────────────────────────────────────┐
  │ ✓ Orden de Compra creada            │
  │ Ref: PO-001234                      │
  │                                     │
  │ [Ver OC] [Cerrar]                   │
  └─────────────────────────────────────┘
```

### 2.3 Modelo de Datos (Modelos Transientes)

Todos son `TransientModel` — viven en sesión, se borran al cerrar.

**`purchase.invoice.import.wizard` (Principal)**

```python
# Carga
xml_file: Binary          # XML CFDI base64
xml_filename: Char        # Nombre original
pdf_file: Binary          # PDF opcional
pdf_filename: Char        # Nombre original
pdf_parsed: Boolean       # ¿Extrajo lotes?
lots_summary: Html        # Resumen/errores lotes

# ZIP mode
upload_mode: Selection    # 'individual' | 'zip'
zip_file: Binary
zip_filename: Char
zip_pair_summary: Html
zip_remaining_pairs_json: Text     # JSON [{"xml":..., "pdf":...}, ...]
zip_total_pairs: Integer           # Conteo total
zip_current_pair_index: Integer    # Índice actual

# CFDI extraído
cfdi_uuid: Char(readonly)
cfdi_folio: Char(readonly)
cfdi_fecha: Date(readonly)
cfdi_subtotal: Float(readonly)
cfdi_total: Float(readonly)
cfdi_moneda: Char(readonly)
cfdi_condiciones: Char(readonly)
emisor_rfc: Char(readonly)
emisor_nombre: Char(readonly)
parse_warnings: Text(readonly)

# Proveedor matcheado
partner_id: Many2one('res.partner')  # Resultado del matching
partner_confidence: Float(readonly)    # 0.6 – 1.0
partner_match_method: Char(readonly)   # 'RFC exact', 'RFC fuzzy', 'Nombre'

# Líneas
line_ids: One2many('wizard.line')

# Estado
state: Selection  # 'upload' → 'review' → 'done'
```

**`purchase.invoice.import.wizard.line` (Conceptos CFDI)**

```python
wizard_id: Many2one('wizard')
no_identificacion: Char(readonly)  # Barcode CFDI
descripcion: Char(readonly)
cantidad: Float(readonly)
valor_unitario: Float(readonly)
importe: Float(readonly)
tasa_iva: Float(readonly)           # 0.16, 0.08, etc.
importe_iva: Float(readonly)
clave_unidad: Char(readonly)

# Matching producto
product_id: Many2one('product.product')
product_confidence: Float(readonly)  # 0.6 – 1.0
product_match_method: Char(readonly) # 'Barcode', 'Default code', 'Supplier code', 'Nombre'
needs_review: Boolean(readonly)     # True si product_id=False O conf < 0.9

# Lotes
lot_ids: One2many('wizard.lot')
```

**`purchase.invoice.import.wizard.lot` (Lotes extraídos del PDF)**

```python
line_id: Many2one('wizard.line')
lot_name: Char(readonly)             # "LOT-001", "LT-2023-05-01", etc.
lot_expiration_date: Date(readonly)  # Caducidad
quantity: Float(readonly)             # Cantidad del lote
discount: Float(readonly)             # % descuento

# Matching
existing_lot_id: Many2one('stock.lot')  # Si existe
state: Selection  # 'found' | 'missing'
```

### 2.4 Servicios (Capa sin ORM)

| Servicio | Input | Output | Características |
|----------|-------|--------|-----------------|
| **cfdi_parser.py** | XML bytes | CFDIDocument | Parsea CFDI 4.0 (SAT México) usando `xml.etree` stdlib |
| **supplier_matcher.py** | RFC, nombre | (res.partner, confianza, método) | Matching en cascada: RFC exact → RFC fuzzy → nombre |
| **product_matcher.py** | barcode, nombre, partner_id | (product.product, confianza, método) | Matching: barcode → código → supplier code → nombre |
| **pdf_lot_parser.py** | PDF bytes | dict[no_id] → list[lotes] | Shim → delega a LotParserProvider |
| **pdf_lot_provider.py** | PDF bytes | dict[no_id] → list[lotes] | 3 estrategias: Quifamesa / KV / Numeric |
| **zip_extractor.py** | ZIP bytes | ZipContents + [XmlPdfPair] | Extrae + empareја XML↔PDF automáticamente |

---

## Formatos de Entrada Soportados

### 3.1 XML CFDI 4.0 (SAT México)

**Estructura esperada:**
```xml
<cfdi:Comprobante
    Serie="A"
    Folio="1234"
    Fecha="2026-04-29T10:30:00"
    SubTotal="1000.00"
    Total="1160.00"
    Moneda="MXN"
    CondicionesDePago="Contado">

    <cfdi:Emisor Rfc="AAA010101AAA" Nombre="Proveedor S.A." RegimenFiscal="601"/>
    <cfdi:Receptor Rfc="BBB020202BBB" Nombre="Mi Empresa S.A."/>

    <cfdi:Conceptos>
        <cfdi:Concepto
            NoIdentificacion="7501234567890"
            Descripcion="Producto X"
            Cantidad="100"
            ValorUnitario="10"
            Importe="1000">
            <cfdi:Traslado Impuesto="002" TasaOCuota="0.16" Importe="160"/>
        </cfdi:Concepto>
    </cfdi:Conceptos>

    <tfd:TimbreFiscalDigital UUID="a1b2c3d4-..."/>
</cfdi:Comprobante>
```

**Campos extraídos:**
| Campo | Origen | Uso |
|-------|--------|-----|
| UUID | `tfd:TimbreFiscalDigital.UUID` | Auditoría fiscal |
| Folio Completo | `Serie` + `Folio` | Emparejamiento ZIP, número de referencia |
| Emisor RFC | `cfdi:Emisor.Rfc` | Matching con proveedor |
| Conceptos | `cfdi:Concepto` (1..N) | Líneas de la OC |
| IVA (Traslado) | `cfdi:Traslado[@impuesto="002"]` | Búsqueda de impuesto |

**Validaciones:**
- XML bien formado (parseable con ET)
- Presente: Serie, Folio, Emisor RFC, al menos 1 Concepto
- Si hay error: CFDIDocument.parse_errors no vacío → se rechaza

---

### 3.2 PDF de Facturas (Extracción de Lotes)

El módulo intenta extraer lotes y caducidades del PDF. **Soporta 3 formatos de regex:**

#### Formato 1: Quifamesa (slash)
```
Patrón:    LOTE/DD-mes-YYYY/cantidad
Ejemplo:   LOT-001/30-abr-2027/100
           LT-2023-505/15-dic-2028/50

Regex:     (\S+)/(\d{2})-(\w+)-(\d{4})/(\d+)
Uso:       Quifamesa (y otros que usen este patrón)
Proveedor: Seleccionar en res.partner → 'quifamesa'
```

#### Formato 2: Key-Value
```
Patrón:    Lote: LOTE Cad: DD/MM/YYYY Cant: cantidad
Ejemplo:   Lote: LT-2023-001 Cad: 31/12/2027 Cant: 50

Regex:     Lote:\s*(\S+)\s+Cad:\s*(\d{2})/(\d{2})/(\d{4})\s+Cant:\s*(\d+)
Uso:       Genérico (fallback)
```

#### Formato 3: Numeric Date
```
Patrón:    LOTE DD/MM/YYYY cantidad
Ejemplo:   LT-2023 31/12/2027 50

Regex:     (\S+)\s+(\d{2})/(\d{2})/(\d{4})\s+(\d+)
Uso:       Genérico (fallback)
```

**Estrategia de extracción por proveedor:**

| Proveedor | Estrategia | Patrón 1 | Patrón 2 | Patrón 3 |
|-----------|-----------|---------|---------|---------|
| **Generic** (default) | Intenta todos en orden | ✓ (3o) | ✓ (2o) | ✓ (1o) |
| **Quifamesa** | Slash primario, fallback generic | ✓ (1o) | ✓ (3o) | ✓ (2o) |

**Configuración:**
```
res.partner (formulario)
  → pestaña Compra
  → campo "Perfil de lotes PDF"
  → seleccionar "Genérico" o "Quifamesa"
```

**Validaciones:**
- Se intenta extraer; si falla, aviso en `lots_summary` (no error fatal)
- Usuario puede reintentar con botón "Extraer lotes del PDF"
- Lotes no encontrados → campo `state='missing'`, usuario puede crearlos

---

## Guía de Instalación y Configuración

### Prerequisitos

- **Odoo 19.0** Enterprise o Community
- **Python 3.10+**
- Módulos base: `purchase`, `stock`, `mail`
- (Opcional) módulo `purchase_lot_selection` para splits por lote
- Dependencias Python:
  - `pypdf` (obligatorio para parseo PDF)
  - `pdfplumber` (opcional, más rápido que pypdf)

### Instalación en Odoo.sh

1. **Clonar o copiar módulo:**
   ```bash
   # En custom_addons/ de Odoo.sh
   git clone <repo> /path/to/custom_addons/purchase_invoice_parser
   ```

2. **Actualizar módulos (Odoo):**
   - Activar modo desarrollador
   - **Ajustes** → **Módulos** → **Actualizar lista de módulos**
   - Buscar `purchase_invoice_parser` → Instalar

3. **Verificar instalación:**
   - **Compras** → **Órdenes de Compra** → botón "Importar XML" debe aparecer
   - Abrir un partner → pestaña **Compra** → campo "Perfil de lotes PDF" debe aparecer

### Instalación en Local (desarrollo)

```bash
# En contenedor Odoo
cd /path/to/odoo

# Copiar módulo
cp -r purchase_invoice_parser /path/to/addons/

# Actualizar módulo
./odoo-bin -u purchase_invoice_parser -d dev_db --stop-after-init

# Correr tests
./odoo-bin --test-enable -u purchase_invoice_parser -d test_db --stop-after-init --log-level=test
```

### Configuración Posterior

#### Por Proveedor: Seleccionar Perfil de Lotes

```
Compras → Proveedores → [seleccionar proveedor]
  → pestaña "Compra"
  → campo "Perfil de lotes PDF"
  → opciones:
    - "Genérico (3 formatos)"     ← default
    - "Quifamesa"                 ← para Quifamesa
```

**Recomendaciones:**
- Comienza con "Genérico" para todos
- Cambia a "Quifamesa" si tienes problemas de extracción con ese proveedor

#### Por Empresa: Configuración Global (Opcional)

No hay configuración global — todo es por proveedor (res.partner).

---

## Uso: Flujos del Módulo

### 5.1 Flujo Individual (XML + PDF)

**Escenario:** Usuario recibe XML + PDF de un proveedor, ambos archivos sueltos.

**Pasos:**
1. Abre **Compras** → **Órdenes de Compra** → botón "Importar XML"
2. Wizard abre en estado `upload` con radio `[●] Archivos individuales` (default)
3. Sube **XML CFDI** (obligatorio)
4. (Opcional) Sube **PDF** de la factura
5. Click en **[Importar]**
6. Sistema valida XML, extrae datos, matchea proveedor y productos
7. Si hay PDF: extrae lotes automáticamente
8. Wizard pasa a estado `review` → usuario ve:
   - UUID, folio, fecha, totales
   - Proveedor matcheado + confianza
   - Líneas con productos + confianza
   - Lotes encontrados (si PDF se subió)
9. Usuario ajusta si es necesario (cambiar producto, crear lotes, etc.)
10. Click en **[Crear OC]** → crea `purchase.order` + adjunta archivos
11. Wizard pasa a `done` → redirige a la OC creada

**Tiempo:** 2-3 minutos por factura

---

### 5.2 Flujo ZIP (Múltiples XML+PDF)

**Escenario:** Usuario recibe un `.zip` del sistema del proveedor con 5 facturas (5 XML + 5 PDF).

**Pasos:**
1. Abre **Compras** → **Órdenes de Compra** → botón "Importar XML"
2. Wizard abre en estado `upload` con radio `[○] Archivos individuales`
3. Cambia a `[●] ZIP del proveedor`
4. Sube **ZIP** (contiene N XML + N PDF)
5. Click en **[Importar ZIP]**
6. Sistema:
   - Extrae ZIP
   - Parsea cada XML con CFDIParser
   - Empareја XML↔PDF automáticamente (por nombre / folio / fallback)
   - Carga el **primer par** en los campos xml_file/pdf_file
   - Almacena pares restantes en JSON
   - Transiciona a `review`
7. Wizard muestra:
   - Indicador **"Factura 1 de 5"**
   - Datos del primer CFDI
   - Botón **[Crear OC y siguiente]** en lugar de solo "Crear OC"
8. Usuario revisa y ajusta si es necesario
9. Click en **[Crear OC y siguiente]**
   - Crea OC por primer par
   - Carga segundo par automáticamente → regresa a `review`
   - Indicador ahora muestra "Factura 2 de 5"
10. Repite pasos 8-9 hasta último par
11. En último par: botón dice **[Crear OC]** (sin "siguiente")
12. Después de crear la última: state = `done` → muestra resumen "✓ Se crearon 5 órdenes de compra"

**Tiempo:** ~1 min/factura (vs. 2-3 min manual)

**Emparejamiento XML↔PDF (3 estrategias):**
```
1. Nombres iguales: "FACTURA-001.xml" + "FACTURA-001.pdf" → match
2. Folio en PDF: "123.xml" (folio=123) + "factura-F-0123-2026.pdf" → match por "0123"
3. 1-a-1 fallback: 1 XML + 1 PDF no relacionados → se emparejan igual
```

Si algún PDF no encuentra match → se etiqueta "unpaired", usuario lo ve en resumen.

---

### 5.3 Configurar Perfil de Proveedor

**Para un proveedor específico que usa formato Quifamesa:**

1. **Compras** → **Proveedores** → buscar/crear "Proveedor Quifamesa"
2. Pestaña **Compra** → desplazar a campo **"Perfil de lotes PDF"**
3. Seleccionar `Quifamesa`
4. Guardar

**De ahora en adelante**, cuando se suba un PDF de este proveedor, se usará `QuifamesaProvider` (patrón slash primario).

---

## Validación Post-Despliegue

### Verificación 1: Instalación

```sql
-- Base de datos
SELECT COUNT(*) FROM ir_model WHERE model = 'purchase.invoice.import.wizard';
-- Resultado esperado: 1
```

```bash
# Terminal Odoo
./odoo-bin -u purchase_invoice_parser -d test_db --stop-after-init
# Resultado esperado: sin errores
```

### Verificación 2: Wizard Abre

1. Ir a **Compras** → **Órdenes de Compra**
2. Botón **"Importar XML"** debe estar visible
3. Click → wizard abre en estado `upload`
4. Radios `[○] Archivos individuales [●] ZIP del proveedor` deben verse

**Resultado esperado:** Wizard abre sin errores

### Verificación 3: Matching Básico

1. Subir XML de prueba (proveedor conocido, productos conocidos)
2. Click **[Importar]**
3. En `review`:
   - `partner_confidence > 0.7` (debe encontrar proveedor)
   - `product_confidence > 0.6` por lo menos en algunas líneas
   - `parse_warnings` vacío si XML válido

**Resultado esperado:** Datos extraídos correctamente

### Verificación 4: ZIP Parsing

1. Crear ZIP local con 2 XML + 2 PDF
2. Cambiar radio a `[●] ZIP del proveedor`
3. Subir ZIP
4. Click **[Importar ZIP]**
5. En `review`:
   - Indicador "Factura 1 de 2"
   - `zip_total_pairs = 2`

**Resultado esperado:** ZIP extraído y emparejado correctamente

### Verificación 5: Extracción de Lotes

1. PDF de prueba con lotes en formato esperado (Slash o KV)
2. Subir junto con XML
3. Click **[Importar]**
4. En `review`:
   - Campo `lots_summary` debe contener lotes encontrados
   - `line.lot_ids` debe tener registros
   - `lot_name`, `lot_expiration_date`, `quantity` poblados

**Resultado esperado:** Lotes extraídos sin errores

### Verificación 6: Creación de OC

1. Revisar datos en `review`
2. Click **[Crear OC]**
3. Wizard pasa a `done` → redirige a OC recién creada
4. Verificar en **Compras** → **Órdenes de Compra**:
   - Nueva OC visible
   - `partner_ref` = folio CFDI
   - Líneas con productos y cantidades correctas
   - Adjuntos (XML + PDF) visibles en chatter

**SQL de verificación:**
```sql
SELECT id, name, partner_ref, amount_total
FROM purchase_order
WHERE state = 'draft'
ORDER BY create_date DESC
LIMIT 1;
-- Resultado: nueva OC con datos del CFDI
```

### Verificación 7: Tests Automatizados

```bash
./odoo-bin --test-enable -u purchase_invoice_parser -d test_db --stop-after-init --log-level=test

# Resultado esperado
test_parse_xml_basic ... ok
test_parse_zip_single_pair ... ok
test_zip_navigation ... ok
... (más tests) ... ok

Ran 14 tests in 3.21s
OK
```

---

## Limitaciones Conocidas

| Limitación | Impacto | Workaround |
|-----------|---------|-----------|
| **PDF con imágenes** | Si PDF es escaneado (imagen), extracción falla | Usar proveedor que da PDF texto o OCR previo |
| **Formatos lotes nuevos** | Si proveedor usa regex no soportada, no extrae lotes | Crear nuevo provider (pull request bienvenido) |
| **No soporta CFDI 3.3** | Solo CFDI 4.0 | Solicitar actualización de proveedor a CFDI 4.0 |
| **XML sin Timbre** | Si no hay `tfd:TimbreFiscalDigital`, UUID = None | Sistema sigue funcionando (UUID es informativo) |
| **Moneda no-MXN** | Si moneda ≠ MXN, no se valida | Odoo soporta multi-moneda, aquí es informativo |
| **Caracteres especiales en lotes** | Si lote contiene ñ, ü, etc., puede no extraer | Verificar en PDF; regex puede necesitar ajuste |

---

## Extensiones Sugeridas

1. **OCR para PDFs escaneados**
   - Integración con `pytesseract` para extraer texto de imágenes
   - Permitiría procesar facturas en formato scan

2. **Proveedores adicionales**
   - Crear `DistribuidorXProvider` para cada nuevo formato de lote encontrado
   - Base: `LotParserProvider` en `pdf_lot_provider.py`

3. **Integración con SAT**
   - Verificación de UUID contra SAT en tiempo real
   - Validación de RFC de emisor/receptor

4. **Trazabilidad**
   - Auditoría: quién creó cada OC desde CFDI, cuándo, con qué confianza
   - Field `purchase.order.cfdi_source` + chatter automático

5. **Descuento en líneas**
   - Si PDF extrae descuentos, propagarlos a líneas OC
   - Actualmente se ignoran

---

## Glosario Técnico

| Término | Definición | Contexto |
|---------|-----------|---------|
| **CFDI** | Comprobante Fiscal Digital por Internet | Factura electrónica mexicana (XML estándar SAT) |
| **UUID** | Identificador único fiscal | Asignado por SAT, único por factura |
| **RFC** | Registro Federal de Contribuyentes | ID tributaria mexicana (12 chars + 3 verificación) |
| **Folio** | Número secuencial interno | "1234" en CFDI, combinado con Serie → folio_completo |
| **Concepto** | Línea en factura (producto/servicio) | `<cfdi:Concepto>` en XML |
| **Traslado** | Impuesto trasladado (generalmente IVA) | `<cfdi:Traslado impuesto="002">` |
| **NoIdentificacion** | Código/barcode del producto en CFDI | Usado para matching con `product.product` |
| **Confianza** | Score de matching (0.0-1.0) | 1.0 = exact match, 0.6 = fuzzy match |
| **Provider** | Estrategia de extracción de lotes | `GenericProvider`, `QuifamesaProvider` |
| **Pair (ZIP)** | Emparejamiento XML↔PDF | `XmlPdfPair` internamente |
| **Split** | División de línea OC por lote | Si múltiples lotes → múltiples líneas OC |

---

## Changelog

| Versión | Fecha | Cambios |
|---------|-------|---------|
| **19.0.2.1.0** | 2026-05-04 | ✨ ZIP upload + multi-proveedor (refactor) |
| **19.0.2.0.0** | 2026-04 | 🐛 Correcciones menores, compatibilidad Odoo 19 |
| **19.0.1.0.0** | 2026-03 | 🎉 Inicial: XML → OC, PDF lotes, matching automático |

---

**Última actualización:** 2026-05-04
**Mantener:** Zorakode, Medicine Depot
**Contacto:** daniel.cervera.2029@gmail.com
