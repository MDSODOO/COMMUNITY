# Estrategia RPA con n8n para Odoo 19

## Mapa de procesos candidatos a RPA
1. **Healthcheck Odoo**: Monitoreo continuo del estado de la instancia y notificaciones a Telegram en caso de caída.
2. **Conciliación de inventarios**: Alertas diarias de inventario bajo mínimos, comunicando con el equipo vía Telegram.
3. **Alertas de lotes por vencer**: Revisión de las fechas de caducidad de lotes para informar a los responsables y mitigar pérdidas.
4. **Sincronización de órdenes de compra (B2B)**: Alertas y validaciones automáticas de nuevas órdenes de compra significativas.
5. **Reporte diario de ventas**: Digest automatizado al final del día sobre las ventas ejecutadas.

## Endpoints XML-RPC Disponibles
- **Autenticación**: `http://localhost:8069/xmlrpc/2/common`
- **Operaciones CRUD (Object)**: `http://localhost:8069/xmlrpc/2/object`
- Alternativa JSON-RPC: `http://localhost:8069/web/dataset/call_kw`
- Healthcheck: `http://localhost:8069/web/health`

## Triggers y nodos por flujo
- **Trigger**: Se utilizarán los nodos Schedule (Cron) para los procesos que requieren revisión periódica, y Webhook para interacciones iniciadas desde Odoo u otros sistemas externos.
- **Nodos HTTP Request**: Para comunicación con los endpoints XML-RPC de Odoo.
- **Nodos Code**: Para el formateo y tratamiento de datos extraídos (ej: filtrado y formateo para reportes en Telegram).
- **Notificaciones (Telegram Bot API)**: Informes automáticos para mantener a los equipos al día.

## Arquitectura de Integración
n8n correrá gestionado independientemente, pero utilizará las variables de entorno para apuntar a la URL de Odoo, el token de Telegram y credenciales (usuario, base de datos, API key) para la comunicación segura.
