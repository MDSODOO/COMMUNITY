# account_move_cep_verification — Banxico CEP-SCL

Verificación de Comprobantes Electrónicos de Pago (CEP) para transferencias SPEI usando
**Banxico CEP-SCL**: el servicio oficial gratuito del Banco de México.

> **Costo total: $0 USD** — Sin APIs de pago, sin suscripciones.

---

## Instalación

1. Activar modo desarrollador: `Ajustes > Activar el modo desarrollador`
2. Ir a **Apps > Actualizar lista de apps**
3. Buscar `CEP Verification` e instalar
4. No requiere configuración inicial de claves — listo para usar

---

## Workflow completo

```
1. Usuario selecciona facturas SPEI en Odoo
         ↓
2. Módulo genera archivo .TXT (validación local)
         ↓
3. Usuario descarga .TXT
         ↓
4. Usuario va a https://www.banxico.org.mx/cep-scl/
   y sube el .TXT
         ↓
5. Banxico asigna un token y envía email con ZIP
         ↓
6. Usuario guarda el token en Odoo (trazabilidad)
         ↓
7. Usuario descarga ZIP del email de Banxico
         ↓
8. Usuario sube ZIP en el wizard de Odoo
         ↓
9. Módulo procesa ZIP:
   - Encontrado → verified_manual + adjunta PDF/XML
   - No encontrado → not_found_banxico
         ↓
10. Auditoría completa en cep.verification.log
```

---

## Uso paso a paso

### Desde una factura individual

1. Abrir una **Factura de Proveedor**
2. Cambiar **Tipo de Transferencia** a `SPEI`
3. Llenar los campos:
   - **Clave de Rastreo** (1-30 caracteres alfanuméricos)
   - **Número de Referencia** (hasta 7 dígitos)
   - **Banco Emisor** (código CLABE, ej. `40058`)
   - **Banco Receptor** (código CLABE, ej. `40102`)
   - **Monto de Transferencia**
   - **Fecha de Operación**
4. Clic en **"Verificar CEP en Banxico"**
5. Seguir los 4 pasos del wizard

### Desde múltiples facturas (lote)

En la lista de facturas, seleccionar varias con `Shift+Click` → **Acción > Verificar CEP en Banxico**.

---

## Estados de verificación

| Estado | Descripción |
|---|---|
| `Pendiente` | No se ha iniciado verificación |
| `Verificado Manual` | CEP encontrado y descargado de Banxico |
| `No Encontrado en Banxico` | La clave de rastreo no existe en Banxico |
| `Revisar Manualmente` | Marcado por el usuario para revisión |

---

## Formato del archivo TXT (Banxico CEP-SCL)

El módulo genera el archivo con este formato CSV:

```
Fecha,ClaveRastreo,CodBancoEmisor,CodBancoReceptor,Monto
2025-06-27,11FEF28A36F,40058,40102,1200.50
2025-06-27,BBVA2024060X,40058,40021,5500.00
```

---

## Procesamiento del ZIP de Banxico

Banxico devuelve un ZIP que contiene:
- **PDF** por cada CEP encontrado (ej. `CEP_11FEF28A36F.pdf`)
- **XML** con datos estructurados (ej. `CEP_11FEF28A36F.xml`)

El módulo busca la **clave de rastreo** en el nombre de cada archivo del ZIP para cruzarla
con los movimientos del lote. Los archivos encontrados se adjuntan automáticamente en la factura.

---

## Menú en Odoo

`Contabilidad > CEP / SPEI`
- **Lotes de Verificación** — Seguimiento de cada lote enviado a Banxico
- **Log de Verificaciones** — Auditoría detallada por transferencia

---

## Códigos de banco comunes (CLABE)

| Código | Banco |
|---|---|
| `40002` | BANAMEX |
| `40021` | HSBC |
| `40058` | BBVA |
| `40102` | ABN AMRO |
| `40110` | SCOTIABANK |
| `40127` | AZTECA |
| `90646` | STP |

---

## Troubleshooting

**El ZIP no tiene ningún archivo para mi clave**
→ La transferencia puede no haber sido procesada por Banxico aún. Espera y vuelve a consultar.
También puede ocurrir si la clave de rastreo, banco o monto no coincide exactamente.

**El módulo dice "No encontrado" pero el banco confirma que sí se procesó**
→ Banxico CEP-SCL puede tardar hasta 24h en reflejar transferencias recientes.
Usa "Marcar para Revisión Manual" mientras tanto.

**Error al abrir ZIP**
→ Verifica que el archivo ZIP descargado no esté corrupto. Intenta descargarlo nuevamente del
email de Banxico.

**Cron "CEP-SCL: Recordatorio" ¿qué hace?**
→ Ejecuta diariamente y agrega una nota en los lotes que llevan más de 24h en estado
"Enviado a Banxico" sin que se hayan importado resultados. Visible en el campo "Notas" del lote.
