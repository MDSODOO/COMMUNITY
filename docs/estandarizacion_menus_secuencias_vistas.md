# Guía y Matriz de Estandarización: Menús, Vistas, Acciones y Secuencias (Odoo 19)

**Proyecto:** Medicine Depot Sureste — Migración Odoo 19 Community  
**Fecha de Auditoría:** Agosto 2026  
**Responsable:** Arquitecto UI/UX y Desarrollador Senior Odoo 19  
**Base de Datos / Servidor Dev:** `medicinedepot_dev` en Ionos (Docker `medicinedepot_dev_odoo`)

---

## 1. Resumen Ejecutivo y Diagnóstico Global

Se realizó una auditoría estática y dinámica exhaustiva sobre los **42 módulos personalizados** que integran el ecosistema de Medicine Depot en Odoo 19.

### Principales Hallazgos:
1. **Árbol de Menús y Barra de Aplicaciones:**
   - Existía duplicidad de menú raíz en **Farmacovigilancia** (`md_pharma_regulatory` y `medicine_depot_portal` creaban sendos menús raíz independientes).
   - El módulo `md_asset_devices` contaba con un menú raíz sin barra de submenús superior (`Dispositivos`, `Mantenimiento`, `Suscripciones`, `Tareas`, `Configuración`), lo cual limitaba la navegación dentro de la app.
   - Menús transaccionales y de reporte en Ventas, Compras, Inventario y Contabilidad requerían ordenamiento secuencial y estandarización de jerarquía.

2. **Nomenclatura de XML IDs y Vistas Odoo 19:**
   - Diversos módulos conservaban identificadores con sufijos legados `_tree` (ej. `device_management_view_tree`, `md_mail_account_view_tree`, `view_stock_scrap_batch_tree`) en lugar del estándar moderno `_list`.
   - Varios XML IDs de vistas y acciones no utilizaban el prefijo canónico `view_<model>_<type>` o `action_<model>`.

3. **Secuencias (`ir.sequence`) y Generación de Folios:**
   - Modelos críticos como `device.management` (Activos IT) y `device.maintenance` (Mantenimientos) dependían de captura manual o no generaban folios secuenciales auditables en su método `create()`.
   - Módulos como `mds_raffle_campaign`, `medicine_depot_scrap_batch`, `medicine_depot_portal`, `local_ai_connector` y `mds_helpdesk` cuentan con secuencias operativas que han sido verificadas e integradas al estándar.

---

## 2. Convención Estricta de Nomenclatura

Para garantizar mantenibilidad, evitar colisiones en `ir.model.data` y respetar el estándar oficial de Odoo 19:

| Elemento | Convención XML ID | Ejemplo |
| :--- | :--- | :--- |
| **Vistas Lista** | `view_<model_underscored>_list` | `view_device_management_list`, `view_stock_scrap_batch_list` |
| **Vistas Formulario** | `view_<model_underscored>_form` | `view_device_management_form`, `view_raffle_campaign_form` |
| **Vistas Kanban** | `view_<model_underscored>_kanban` | `view_device_management_kanban`, `view_mds_helpdesk_ticket_kanban` |
| **Vistas Búsqueda** | `view_<model_underscored>_search` | `view_device_management_search`, `view_md_telegram_channel_search` |
| **Vistas Calendario/Pivot/Graph** | `view_<model_underscored>_<type>` | `view_device_maintenance_calendar`, `view_client_cashback_report_pivot` |
| **Acciones de Ventana** | `action_<model_underscored>` | `action_device_management`, `action_device_maintenance`, `action_md_mail_account` |
| **Menús** | `menu_<modulo>_<nombre>` o `menu_<entidad>` | `menu_md_asset_devices_root`, `menu_device_management_dispositivos` |
| **Secuencias** | `seq_<model_underscored>` | `seq_device_management`, `seq_device_maintenance`, `seq_mds_helpdesk_ticket` |

---

## 3. Estructura Canónica del Árbol de Menús por Aplicación

### 3.1. Activos e Infraestructura IT (`md_asset_devices`, `md_asset_fleet`)
- **Menú Raíz:** `menu_md_asset_devices_root` ("Activos IT", `sequence=10`)
  - **Dispositivos:** `menu_device_management_dispositivos` (`action_device_management`, `seq=10`)
  - **Mantenimiento:** `menu_device_management_mantenimiento` (`action_device_maintenance`, `seq=20`)
  - **Suscripciones y Licencias:** `menu_device_management_suscripciones` (`action_device_subscription`, `seq=30`)
  - **Tareas y Pendientes:** `menu_device_management_todos` (`action_device_todo`, `seq=40`)
  - **Documentación:** `menu_device_management_docs` (`action_device_documentation`, `seq=50`)
  - **Pagos / Pólizas:** `menu_device_management_pagos` (`action_device_payment`, `seq=60`)
- **Flotilla (`md_asset_fleet`):** Extiende vistas de `fleet.vehicle` dentro de la app nativa de Flota (`fleet.menu_root`).

### 3.2. Ventas y Punto de Venta (`sale`, `point_of_sale`, módulos MD)
- **Cotizaciones con IA:** `local_ai_connector.menu_image_quote_request` en `sale.sale_menu_root` (`seq=60`).
- **Reportes de Ventas / Cashback:**
  - `md_cashback_report.menu_client_cashback_report` en `sale.menu_sale_report` (`seq=20`).
  - `md_cashback_report.menu_client_cashback_anomaly` en `sale.menu_sale_report` (`seq=21`).
  - `sale_lab_report.menu_ventas_laboratorio` en `sale.menu_sale_report` (`seq=25`).
- **Punto de Venta:**
  - `md_legacy_pos_history.menu_md_pos_order_unified` en `point_of_sale.menu_point_of_sale` (`seq=25`).
  - `md_legacy_pos_history.menu_md_legacy_pos_order` en `point_of_sale.menu_point_of_sale` (`seq=90`).
  - `bi_pos_stock.menu_bi_supplier_snapshot` en `point_of_sale.menu_point_config_product` (`seq=99`).

### 3.3. Compras (`purchase_invoice_parser`, `purchase_vendor_ref`, etc.)
- **Menú Análisis Compras:** `purchase_invoice_parser.menu_purchase_analysis` en `purchase.menu_purchase_root` (`seq=60`):
  - **Notificaciones de Precio:** `menu_price_notifications_list` (`seq=10`).
  - **Reporte de Cambios de Precio:** `menu_price_notification_report_wizard` (`seq=15`).
  - **Costos por Sucursal:** `menu_cost_by_branch_wizard` (`seq=20`).

### 3.4. Inventario y Farmacia (`stock`, `md_lots_management`, `md_pharma_regulatory`, `medicine_depot_scrap_batch`)
- **Lotes y Series:**
  - `md_lots_management.menu_production_lot_customized` en `stock.menu_stock_root` (`seq=10`).
  - `md_lots_management.menu_production_lot_handheld` en `stock.menu_stock_root` (`seq=11`).
- **Bajas y Scrap:**
  - `medicine_depot_scrap_batch.menu_stock_scrap_batch` en `stock.menu_stock_scrap` (`seq=40`).
  - `medicine_depot_scrap_batch.menu_medicine_depot_scrap_history_legacy` en `stock.menu_stock_scrap` (`seq=45`).
  - `medicine_depot_scrap_batch.menu_scrap_summary_2025` en `stock.menu_stock_scrap` (`seq=50`).
- **Configuración Regulatoria e Inventarios:**
  - `md_product_lines.menu_md_product_line` en `stock.menu_stock_config_settings` (`seq=60`).
  - `md_pharma_regulatory.menu_md_regulatory_review` en `stock.menu_stock_config_settings` (`seq=62`).
  - `md_pharma_regulatory.menu_md_active_substance` en `stock.menu_stock_config_settings` (`seq=65`).
  - `md_pharma_regulatory.menu_md_name_abbreviation` en `stock.menu_stock_config_settings` (`seq=66`).
  - `lab_inventory_report.menu_report_lab_inventory` en `stock.menu_warehouse_report` (`seq=100`).

### 3.5. Farmacovigilancia Unificada (`md_pharma_regulatory`, `medicine_depot_portal`)
- **Menú Raíz Canónico:** `md_pharma_regulatory.menu_md_pharma_root` ("Farmacovigilancia", `seq=90`).
  - **Reportes de Farmacovigilancia:** `medicine_depot_portal.menu_medicine_depot_pharmacovigilance_report` (`action_medicine_depot_pharmacovigilance_report`, `seq=10`).
  - **Revisión Regulatoria PLM:** `menu_md_regulatory_review_pharma` (`action_md_regulatory_review`, `seq=20`).
  - **Configuración Regulatoria:** `menu_md_pharma_config` (`seq=50`):
    - Sustancias Activas (`action_md_active_substance`, `seq=10`).
    - Diccionario de Abreviaturas (`action_md_name_abbreviation`, `seq=20`).

### 3.6. Campañas de Rifas (`mds_raffle_campaign`)
- **Menú Raíz:** `mds_raffle_campaign.menu_raffle_root` ("Rifas", `seq=60`):
  - **Campañas:** `menu_raffle_campaign` (`action_raffle_campaign`, `seq=10`).
  - **Folios:** `menu_raffle_ticket` (`action_raffle_ticket`, `seq=20`).
  - **Reglas de Premiación:** `menu_raffle_rule` (`action_raffle_rule`, `seq=30`).

### 3.7. Soporte y Helpdesk (`mds_helpdesk`)
- **Menú Tickets:** `mds_helpdesk.menu_mds_helpdesk_root` en `project.menu_main_pm` (`seq=15`).
- **Equipos de Soporte:** `mds_helpdesk.menu_mds_helpdesk_teams` en `project.menu_project_config` (`seq=50`).

### 3.8. Comunicaciones y Correo (`md_mail_client`, `md_mail_accounts`, `md_telegram_notify`)
- **Menú Correo:** `md_mail_client.menu_md_mail_client_root` ("Correo", `seq=10`).
  - **Cuentas IMAP/SMTP:** `md_mail_accounts.menu_md_mail_account_root` (`seq=20`).
- **Telegram (Ajustes):** `md_telegram_notify.menu_md_telegram_root` en `base.menu_administration` (`seq=90`):
  - Ajustes (`seq=10`), Canales (`seq=20`), Cola de Mensajes (`seq=30`).

---

## 4. Matriz de Secuencias (`ir.sequence`) y Métodos `create()`

| Módulo | Modelo | Código de Secuencia | Prefijo | Relleno | Campo Destino | Método `create()` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`md_asset_devices`** | `device.management` | `device.management` | `DEV/%(year)s/` | 5 | `codigo_dispositivo` | Asignación automática si viene vacío o `'/'` |
| **`md_asset_devices`** | `device.maintenance` | `device.maintenance` | `MNT/%(year)s/` | 5 | `name` (Referencia) | Asignación automática si viene vacío o `'/'` |
| **`local_ai_connector`** | `local.ai.image.quote.request` | `local.ai.image.quote.request` | `AIQ-` | 5 | `name` | Nativo en `create()` |
| **`mds_helpdesk`** | `mds.helpdesk.ticket` | `mds.helpdesk.ticket` | `MDS-TICK-` | 4 | `code` | Nativo en `create()` |
| **`medicine_depot_portal`** | `medicine.depot.pharmacovigilance.report` | `medicine.depot.pharmacovigilance.report` | `PV/%(year)s/%(month)s/` | 4 | `name` | Nativo en `create()` |
| **`medicine_depot_scrap_batch`** | `stock.scrap.batch` | `stock.scrap.batch` | `SB%(y)s%(month)s-` | 4 | `name` | Nativo en `create()` |
| **`mds_raffle_campaign`** | `raffle.ticket` | Dinámica por campaña | `<CAMP_CODE>-R-` / `<CAMP_CODE>-B-` | 6 | `name` | Generación por campaña en `create()` |

---

## 5. Plan de Ejecución Módulo por Módulo

1. **`md_asset_devices`**:
   - Crear `data/ir_sequence_data.xml` con `device.management` y `device.maintenance`.
   - Modificar `models/device_management.py` para soporte de secuencia en `codigo_dispositivo` (default `'/'`).
   - Modificar `models/device_maintenance.py` agregando campo `name` con default `'/'` y secuencia en `create()`.
   - Estandarizar XML IDs de vistas (`view_device_management_list`, `view_device_maintenance_list`, etc.), acciones y submenús.
   - Actualizar `__manifest__.py` para incluir `data/ir_sequence_data.xml`.

2. **`md_pharma_regulatory` y `medicine_depot_portal`**:
   - Estandarizar el menú de Farmacovigilancia para que los reportes de `medicine_depot_portal` se alojen bajo el menú raíz `md_pharma_regulatory.menu_md_pharma_root`, evitando menú raíz duplicado.

3. **`md_mail_accounts`**:
   - Estandarizar XML IDs de vistas (`view_md_mail_account_list`, `view_md_mail_account_form`, etc.) y acción (`action_md_mail_account`).

4. **`md_asset_fleet`**:
   - Estandarizar XML IDs de vistas (`view_fleet_vehicle_form_md_employee`, `view_fleet_vehicle_list_md_employee`).

5. **`medicine_depot_scrap_batch` & `purchase_invoice_parser`**:
   - Estandarizar XML IDs de vistas lista (`view_stock_scrap_batch_list`, `view_purchase_price_notification_list`).

6. **Despliegue y Verificación en Ionos**:
   - Sincronizar vía `rsync` hacia `/opt/medicinedepot-odoo19-migration/custom_addons/`.
   - Actualizar módulos con `odoo -d medicinedepot_dev -u <modulos> --no-http --stop-after-init`.
   - Ejecutar pruebas automáticas en Odoo shell validando creación de registros y asignación de folios secuenciales.

---

## 6. Resultados de Verificación y Estado Final (100% Conforme)

### 6.1. Actualización de Módulos en Ionos Dev (`medicinedepot_dev`)
- **Comando ejecutado:**
  ```bash
  docker exec -i medicinedepot_dev_odoo odoo -d medicinedepot_dev -u md_asset_devices,md_asset_fleet,md_pharma_regulatory,medicine_depot_portal,md_mail_accounts,medicine_depot_scrap_batch,purchase_invoice_parser,md_lots_management,hr_attendance_ip_autologin,lot_selection,md_telegram_notify --no-http --stop-after-init
  ```
- **Resultado:** Código de salida `0` (Exitoso). Todos los módulos y sus vistas se actualizaron sin errores de XML o dependencias circulares. Vistas y acciones huérfanas/renombradas fueron purgadas automáticamente por el ORM.

### 6.2. Pruebas Automatizadas de Secuencias en Odoo Shell
Se ejecutó una batería de pruebas unitarias/E2E en el shell de Odoo (`medicinedepot_dev`) verificando la generación automática de folios:
- `device.management`: Generación de folios `DEV/2026/0000X` validada al 100%.
- `device.maintenance`: Generación de folios `MNT/2026/0000X` validada al 100%.
- `local.ai.image.quote.request`: Generación de folios `AIQ-0005X` validada al 100%.
- `mds.helpdesk.ticket`: Generación de códigos `MDS-TICK-000X` validada al 100%.
- `medicine.depot.pharmacovigilance.report`: Generación de folios `PV/2026/08/000X` validada al 100%.
- `stock.scrap.batch`: Generación de folios `SB2608-000X` validada al 100%.

### 6.3. Jerarquía y Árbol Canónico de Menús
- Menú raíz unificado de **Farmacovigilancia** (`md_pharma_regulatory.menu_md_pharma_root`) integrando reportes del portal, revisión regulatoria PLM y configuración.
- Menú raíz de **Activos IT** (`md_asset_devices.menu_md_asset_devices_root`) con su barra completa de 6 submenús activos (`Dispositivos`, `Mantenimientos`, `Suscripciones`, `Tareas`, `Documentación`, `Pagos`).
- Todas las vistas de lista utilizan la etiqueta estándar `<list>` de Odoo 19 y nomenclatura homogénea `view_<model>_<type>`.

