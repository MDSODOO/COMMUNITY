# Descarga Masiva de XML del SAT — `l10n_mx_sat_download`

## Módulo para Odoo 19 Enterprise (Python 3.12)

### Descripción General

Módulo personalizado que permite la descarga masiva de archivos XML (CFDI)
directamente desde el Web Service del SAT (Servicio de Administración
Tributaria de México) utilizando la e.firma (FIEL).

Compatible con **Odoo.sh** y diseñado para respetar los timeouts del
entorno cloud mediante procesamiento asíncrono por cron jobs.

---

### Requisitos Previos

#### Dependencias del Sistema (requirements.txt para Odoo.sh)

```
cryptography>=42.0
pyOpenSSL>=24.0
lxml>=5.0
requests>=2.31
python-dateutil>=2.8
```

> **Nota:** `lxml`, `requests` y `python-dateutil` ya están preinstaladas
> en Odoo.sh. Las únicas dependencias **nuevas** son `cryptography` y
> `pyOpenSSL`.

#### Módulos de Odoo Requeridos

- `account` (Contabilidad)
- `l10n_mx_edi` (Localización mexicana EDI)

#### Archivos de la FIEL

Se necesitan los tres componentes de la e.firma del contribuyente:
- Archivo `.cer` (Certificado X.509 en formato DER)
- Archivo `.key` (Llave privada PKCS#8 cifrada en DER)
- Contraseña de la llave privada

**IMPORTANTE:** Debe ser la FIEL (Firma Electrónica Avanzada), NO el CSD
(Certificado de Sello Digital). El módulo valida automáticamente que el
certificado tenga los atributos `digitalSignature` y `nonRepudiation`
en su KeyUsage.

---

### Instalación en Odoo.sh

1. Clonar/copiar la carpeta `l10n_mx_sat_download/` en el directorio de
   módulos personalizados del repositorio de Odoo.sh.

2. Agregar las dependencias al `requirements.txt` en la raíz del
   repositorio:
   ```
   cryptography>=42.0
   pyOpenSSL>=24.0
   ```

3. Hacer commit y push. Odoo.sh instalará las dependencias
   automáticamente.

4. Desde Odoo: **Aplicaciones** → Actualizar lista de módulos →
   Buscar "Descarga Masiva" → Instalar.

---

### Configuración

#### 1. Cargar la FIEL

Ir a **Ajustes** → **Empresas** → seleccionar empresa →
pestaña **FIEL (Descarga SAT)**.

Cargar:
- Certificado (.cer)
- Llave Privada (.key)
- Contraseña

Presionar **Validar FIEL** para confirmar que es válida y que es una
FIEL (no un CSD).

#### 2. Permisos de Usuario

El módulo define dos grupos de seguridad:
- **SAT Descarga Masiva: Usuario** — Puede crear solicitudes y ver XMLs.
- **SAT Descarga Masiva: Administrador** — Acceso completo + eliminar.

Asignar desde **Ajustes** → **Usuarios** → pestaña de permisos.

---

### Uso

#### Descarga Rápida (Wizard)

1. Ir a **Contabilidad** → **Descarga SAT** → **Nueva Descarga Rápida**
2. Seleccionar empresa, tipo (Recibidos/Emitidos), rango de fechas
3. Click en **Solicitar Descarga**
4. El sistema crea la solicitud y la envía al SAT automáticamente

#### Solicitudes de Descarga

El menú **Contabilidad** → **Descarga SAT** → **Solicitudes de Descarga**
muestra todas las solicitudes con su estado:

| Estado         | Significado                                        |
|----------------|----------------------------------------------------|
| Borrador       | Pendiente de enviar al SAT                         |
| Autenticando   | Esperando procesamiento por el cron                |
| Solicitado     | Solicitud enviada, esperando que SAT la procese    |
| Verificando    | El cron está comprobando si el paquete está listo  |
| Descargando    | Descargando ZIPs y extrayendo XMLs                 |
| Completado     | Todos los XMLs fueron descargados y almacenados    |
| Error          | Ocurrió un error (ver detalle en el formulario)    |

**El cron se ejecuta cada 10 minutos.** Procesa hasta 5 solicitudes por
ciclo en cada etapa del flujo.

#### Documentos XML Descargados

**Contabilidad** → **Descarga SAT** → **Documentos XML**

Cada XML descargado se almacena con los datos parseados del CFDI:
- UUID, tipo, fechas, montos, moneda
- RFC y nombre del emisor/receptor
- Detección automática del contacto (res.partner) por RFC
- Detección de duplicados por UUID

Acciones disponibles por documento:
- **Buscar Factura**: Busca una factura existente por UUID y la vincula
- **Crear Factura**: Genera un `account.move` con líneas y impuestos
- **Ignorar**: Marca como irrelevante
- **Reabrir**: Regresa a estado pendiente

---

### Arquitectura Técnica

#### Estructura de Archivos

```
l10n_mx_sat_download/
├── __init__.py
├── __manifest__.py
├── data/
│   └── ir_cron_data.xml
├── lib/                           # Python puro — sin dependencias de Odoo
│   ├── __init__.py
│   ├── sat_webservice.py          # FIEL + 4 operaciones SOAP del SAT
│   └── cfdi_parser.py             # Parser de CFDI 3.3 / 4.0 → dataclasses
├── models/
│   ├── __init__.py
│   ├── res_company.py             # Extensión: campos FIEL
│   ├── sat_download_request.py    # Máquina de estados async
│   └── sat_xml_document.py        # Almacén intermedio XML → account.move
├── security/
│   ├── ir.model.access.csv
│   └── sat_download_security.xml
├── views/
│   ├── res_company_views.xml
│   ├── sat_download_request_views.xml
│   ├── sat_xml_document_views.xml
│   └── sat_download_menuitem.xml
└── wizards/
    ├── __init__.py
    ├── sat_download_wizard.py
    └── sat_download_wizard_views.xml
```

#### Flujo del Web Service del SAT

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────────┐
│   Usuario    │────>│  Odoo (Botón /   │────>│ sat.download.request  │
│  (Wizard)    │     │  Wizard)         │     │  state = 'draft'      │
└─────────────┘     └──────────────────┘     └───────────┬───────────┘
                                                         │
                           CRON (cada 10 min)            │
                    ┌────────────────────────────────────┘
                    │
              ┌─────▼──────┐
              │ Autenticar  │ → FIEL + SOAP → Token (5 min)
              │ (paso 1)    │
              └─────┬───────┘
                    │
              ┌─────▼──────────────┐
              │ SolicitaDescarga   │ → IdSolicitud
              │ (paso 2)           │
              └─────┬──────────────┘
                    │
              ┌─────▼──────────────────────┐
              │ VerificaSolicitudDescarga   │ ← Polling hasta estado=3
              │ (paso 3 — múltiples veces) │
              └─────┬──────────────────────┘
                    │
              ┌─────▼──────────────────┐
              │ DescargarSolicitud     │ → ZIP (Base64) → XMLs
              │ (paso 4)              │
              └─────┬──────────────────┘
                    │
              ┌─────▼──────────────┐
              │ sat.xml.document   │ → Almacenamiento intermedio
              │ (N registros)      │
              └─────┬──────────────┘
                    │
              ┌─────▼──────────────┐
              │ account.move       │ → Crear / Conciliar factura
              │ (factura proveedor)│
              └────────────────────┘
```

#### Modelo de Datos

**sat.download.request** — Solicitud de descarga
- Campos de parámetros: empresa, fechas, tipo
- Campos de respuesta SAT: ID solicitud, estado, paquetes
- Relación 1:N con sat.xml.document
- Máquina de estados gestionada por cron

**sat.xml.document** — Documento XML descargado
- Archivo XML binario como attachment
- Datos parseados del CFDI (UUID, RFC, montos, fechas)
- Estado de procesamiento (pending → matched/created/ignored)
- Relación M:1 con sat.download.request
- Relación M:1 con account.move

#### Clase FIEL (lib/sat_webservice.py)

Independiente de Odoo, usa solo `cryptography` y `lxml`:
- Carga certificado DER → X.509 (`cryptography.x509`)
- Carga llave privada DER → RSA (`cryptography.hazmat`)
- Extrae RFC del subject (OID 2.5.4.45 UniqueIdentifier)
- Extrae número de serie (serial hex → dígitos pares)
- Valida vigencia y tipo (FIEL vs CSD por KeyUsage)
- Firma RSA-SHA1 (autenticación) y RSA-SHA256 (operaciones)

#### Parser CFDI (lib/cfdi_parser.py)

Devuelve dataclasses tipados (`CfdiData`, `CfdiConcepto`, `CfdiTax`,
etc.) a partir de un XML raw. Soporta:
- CFDI 3.3 y 4.0
- Todos los tipos: I, E, T, N, P
- Conceptos con impuestos trasladados y retenidos
- Complemento de pagos 1.0 y 2.0
- Timbre Fiscal Digital

---

### Consideraciones de Seguridad

- La llave privada (.key) y la contraseña solo son visibles para
  usuarios del grupo `base.group_system` (administrador técnico).
- Los campos binarios de la FIEL se almacenan como attachments de Odoo,
  que en Odoo.sh se cifran en reposo.
- Las reglas de registro (ir.rule) garantizan aislamiento multi-compañía.
- Las llamadas al SAT usan HTTPS con verificación de certificado SSL.

---

### Limitaciones Conocidas

1. **Límites del SAT:** El servicio del SAT tiene límites de solicitudes
   por periodo y por contribuyente. Consultar la documentación oficial.
2. **Token de 5 minutos:** El token de autenticación tiene vigencia de
   5 minutos. Cada paso del cron se re-autentica antes de operar.
3. **Timeout Odoo.sh:** El cron procesa máximo 5 solicitudes por ciclo
   para no exceder el timeout de workers (típicamente 120-300 segundos).
4. **Mapeo de impuestos:** El mapeo de impuestos SAT → Odoo depende de
   que los impuestos estén configurados correctamente en la contabilidad.
   Si no se encuentra un impuesto, se registra una advertencia en las
   notas del documento.
5. **Complemento de Pagos:** El tipo 'P' (Pagos) se parsea pero la
   creación automática de registros de pago en Odoo requiere extensión
   adicional.

---

### Extensiones Sugeridas

- **Conciliación automática por cron nocturno:** Un cron que recorra
  todos los `sat.xml.document` en estado `pending` y ejecute
  `action_batch_match()`.
- **Mapeo de productos:** Vincular `ClaveProdServ` del SAT con
  `product.product` de Odoo para auto-completar las líneas.
- **Integración con queue_job (OCA):** Para mayor robustez en el
  procesamiento asíncrono, reemplazar el patrón de cron por la cola
  de trabajos.
- **Dashboard:** Vista Kanban con KPIs de XMLs pendientes, conciliados,
  y creados por periodo.
