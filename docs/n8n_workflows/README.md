# Guía de Importación de Flujos n8n para Odoo 19

Este directorio contiene los flujos de automatización (Workflows) de n8n diseñados para la instancia de Odoo 19 de MedicineDepot.

## Archivos de Flujos

- `01_healthcheck_odoo.json`: Monitoreo del estado de Odoo (Ping a `/web/health`).
- `02_conciliacion_inventario.json`: Alertas de inventarios bajo el umbral mínimo.
- `03_alertas_lotes_vencimiento.json`: Alertas para lotes próximos a caducar.
- `04_sync_ordenes_compra.json`: Recepción de webhooks para sincronización de órdenes B2B.
- `05_reporte_ventas_diario.json`: Generación del reporte de cierre de ventas del día.
- `07_deteccion_duplicados_proveedores.json`: Detección semanal de res.partner duplicados por VAT/RFC (alerta para revisión manual, no auto-merge).
- `08_conciliacion_bancaria.json` [ESQUELETO, inactivo]: Webhook que recibe transacciones bancarias ya parseadas (journal_id + transactions[]), crea las líneas en account.bank.statement.line en Odoo (contabiliza automáticamente) y sugiere matches contra facturas abiertas por monto+partner_hint (nunca auto-concilia). Falta conectar la fuente real (email/portal del banco) al webhook.
- `09_backlog_ordenes_compra_draft.json`: Digest semanal de órdenes de compra en borrador con más de 7 días, agrupadas por comprador.
- `10_backlog_pickings_atascados.json`: Digest semanal de recepciones/entregas atascadas en estado 'assigned', agrupadas por tipo.
- `11_calidad_catalogo.json`: Reporte semanal de productos vendibles con datos incompletos (precio $0, sin categoría, sin SKU/barcode).
- `12_afiliacion_notificacion.json`: Webhook llamado por Odoo (`controllers/portal.py`, metodo `afiliacion()`) al recibir una solicitud nueva; notifica a Telegram con checklist de documentos.
- `13_afiliacion_documentos_pendientes.json`: Digest diario de clientes afiliados con documentos aun sin adjuntar.
- `14_conciliacion_bancaria_resumen.json`: Resumen semanal de transacciones bancarias por conciliar por diario (14 diarios reales creados 2026-08-13), version ligera via Telegram del dashboard de conciliacion de Odoo Enterprise (no disponible en esta instancia Community).
- `15_alertas_anomalias_cashback.json`: Auditoría y alertas semanales de inconsistencias en el esquema de descuento cashback (2% factura + 5% devolución), identificando facturas con 0% descuento u omisiones que ponen en riesgo la bonificación mensual.

## Variables de Entorno Requeridas

Para que estos flujos funcionen correctamente, n8n debe ejecutarse con las siguientes variables de entorno:

- `ODOO_URL`: URL base de la instancia Odoo (ej. `https://odoo.bodegademedicamentos.com`)
- `ODOO_DB`: Nombre de la base de datos (ej. `medicinedepot_dev`)
- `TELEGRAM_BOT_TOKEN`: Token provisto por el BotFather.
- `TELEGRAM_CHAT_ID`: ID del chat/canal donde se enviarán las alertas.

## Instrucciones de Importación

1. Asegúrate de tener n8n instalado y en ejecución (`npm install -g n8n` o vía Docker).
2. Abre la interfaz web de n8n en tu navegador (usualmente `http://localhost:5678`).
3. Ve a la sección de **Workflows** en el panel izquierdo.
4. Para cada archivo `.json` de esta carpeta:
   - Haz clic en la flecha al lado de "Add Workflow" en la esquina superior derecha.
   - Selecciona **"Import from File"**.
   - Sube el archivo `.json` correspondiente.
5. Una vez importado, asegúrate de configurar/validar las credenciales requeridas si aplica, y de **Activar (Active: toggle ON)** los flujos que usen un nodo *Schedule* o *Webhook*.

## Recomendaciones

- Se sugiere habilitar y probar primero el flujo `01_healthcheck_odoo.json`.
- Verifica los logs en la pestaña **Executions** de n8n para confirmar que las conexiones XML-RPC y de Telegram están funcionando correctamente.
