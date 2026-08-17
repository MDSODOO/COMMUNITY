# Auditoría de Workflow y UX Funcional — Módulo `md_asset_devices` (Odoo 19)

**Fecha de auditoría:** 17 de agosto de 2026
**Entorno auditado:** Servidor Ionos (`medicinedepot-odoo19-migration`, BD: `medicinedepot_dev`, contenedor `medicinedepot_dev_odoo`)
**Módulo:** `md_asset_devices` (`custom_addons/md_asset_devices`)
**Versión antes de la auditoría:** `19.0.1.3.0` → **Versión resultante:** `19.0.1.5.0` (primera ronda `19.0.1.4.0` + segunda ronda de la hoja de ruta, ambas el mismo día)
**Enfoque:** fricciones de flujo de trabajo y UX funcional (no visual) — automatización de estados, contextos/defaults, validaciones de negocio, trazabilidad.

---

## 1. Resumen Ejecutivo

| Aspecto | Detalle |
|---|---|
| **Estado general del módulo** | Sólido. La capa visual (kanban, form, decoraciones, ribbons, badges de vencidos) ya estaba bien resuelta — no se encontraron problemas estéticos que abordar. |
| **Modelos auditados** | `device.management`, `device.assignment`, `device.inventory`, `device.maintenance`, `device.documentation`, `device.payment`, `device.subscription`, `device.todo` |
| **Automatizaciones ya presentes (correctas, no tocadas)** | `_sync_assignment_summary` (usuario_asignado se sincroniza solo con la asignación activa) y `_sync_maintenance_state` (dispositivo pasa a "Mantenimiento" solo cuando hay un mantenimiento `in_progress`, sin reactivar equipos retirados). |
| **Hallazgos reales de workflow** | 5 (ver sección 3) |
| **Corregidos en esta auditoría (quick wins)** | 5 / 5 |
| **Validación visual en Chrome** | No se pudo completar — el túnel SSH a `localhost:8069` cae en la pantalla de login de Medicine Depot y no hay política para introducir credenciales (regla de seguridad del entorno). Verificación alternativa (explícitamente autorizada por el usuario): `odoo shell` con script de solo lectura + rollback. **16/16 checks OK.** |

---

## 2. Metodología

1. **Inspección estática de código** — lectura completa de los 8 modelos Python, las 6 vistas XML, `ir.model.access.csv`, `device_management_security.xml`, `ir_cron_data.xml`, `ir_sequence_data.xml` y el manifest, vía `ssh ionos` sobre `/opt/medicinedepot-odoo19-migration/custom_addons/md_asset_devices/`.
2. **Navegación interactiva** — se intentó vía Claude in Chrome contra el túnel SSH (`localhost:8069`); bloqueada por el login del portal (ver arriba). Se documenta como limitación, no se insistió (no se introducen credenciales por política).
3. **Verificación funcional alternativa** — script Python ejecutado con `odoo shell -d medicinedepot_dev --no-http`, todo dentro de una transacción con `env.cr.rollback()` final (nunca `commit()` intermedio — lección aprendida en la auditoría de `md_cashback_report`, donde un `commit()` a mitad de script dejó una factura de prueba posteada en la base real). Verificado con SQL directo que no quedaron residuos (`REGISTROS_TEST_AUDIT: 0`).
4. **Aplicación de quick wins** — parches directos en código + `docker restart` (obligatorio para cambios `.py`) + `-u md_asset_devices`.

---

## 3. Hallazgos y Correcciones

### 3.1 (a) Automatización de estados

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| H1 | Al **retirar** un dispositivo (`action_retire_device`), las asignaciones activas no se cerraban automáticamente. El campo `usuario_asignado` quedaba "fantasma": un empleado seguía apareciendo como responsable de un equipo dado de baja indefinidamente. | Alta | ✅ Corregido |
| H2 | `mantenimiento_vencido_count`, `documentos_vencidos_count` y `suscripciones_vencidas_count` son campos `store=True` cuyo cómputo depende de `date.today()`, no de un campo editado. Odoo solo recalcula un compute `store=True` cuando cambia alguna de sus dependencias declaradas — como "hoy" no es una dependencia real, un mantenimiento que se vuelve vencido **de un día para otro** no actualiza su badge hasta que algún campo relacionado se edite. Esto afecta directamente a los badges rojos del kanban y del smart button, que son la señal visual principal de "algo necesita atención". | Alta (silenciosa) | ✅ Corregido |

**H1 — Fix:** `action_retire_device` ahora marca como `devuelto` (con `fecha_devolucion = today`) todas las asignaciones activas del dispositivo al retirarlo, reutilizando el flujo existente de `device.assignment.write()` que ya sincroniza `usuario_asignado`/`departamento` en el dispositivo.

**H2 — Fix:** nuevo cron diario `cron_device_refresh_alert_counts` (06:00) que fuerza `_compute_alert_counts()` sobre todos los dispositivos, garantizando que los contadores de vencido reflejen la fecha real aunque no haya habido ninguna edición.

### 3.2 (b) Contextos y valores por defecto

**Sin hallazgos.** Todos los sub-modelos (`inventory_ids`, `assignment_ids`, `maintenance_ids`, `documentation_ids`, `payment_ids`, `subscription_ids`) ya reciben `context="{'default_device_id': id}"` en sus listas embebidas, y los métodos `action_view_*` propagan `context={'default_device_id': self.id}` en las acciones de ventana. Un formulario hijo abierto desde cualquier smart button o tab hereda correctamente el dispositivo padre.

### 3.3 (c) Restricciones y validaciones de negocio

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| H3 | No existía ningún bloqueo que impidiera crear/activar una **asignación** (`estado='activa'`) sobre un dispositivo en `maintenance` o `retired`. Un usuario podía asignarse un equipo que está físicamente en el taller o ya dado de baja. | Alta | ✅ Corregido |
| H4 | `ir.model.access.csv`: el grupo **Manager** de `device.subscription` tenía `perm_create=0`, inconsistente con el resto de managers del módulo (Dispositivo, Inventario, Asignación, Mantenimiento, Documentación y Pagos sí pueden crear). Un gerente de TI podía ver y editar suscripciones existentes pero **no dar de alta una licencia nueva** — tenía que escalar a un Admin para algo rutinario. | Media (bloqueo operativo) | ✅ Corregido |

**H3 — Fix:** nueva `@api.constrains('device_id', 'estado')` en `device.assignment` (`_check_device_available_for_assignment`) que rechaza con `ValidationError` cualquier asignación `activa` cuyo dispositivo no esté en estado `active`. Mensaje explícito con el estado actual del equipo.

**H4 — Fix:** `access_device_subscription_manager` ahora tiene `perm_create=1`, alineado con el resto de managers.

### 3.4 (d) Smart Buttons y trazabilidad

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| H5 | `device.assignment` (el historial de "quién tiene este equipo") era el único sub-modelo del dispositivo **sin** smart button, sin contador y sin vista propia registrada — solo era visible embebido en la pestaña "Inventario A la mano". No había forma de saltar directo al historial de asignaciones, ni de abrirlo desde el menú de la app, a diferencia de Mantenimientos, Documentos, Pagos, Suscripciones y Tareas, que sí tienen su acceso directo. | Media | ✅ Corregido |

**H5 — Fix:** nuevo campo `assignment_count` + `action_view_assignments()` en `device.management`, smart button "Asignaciones" (ícono `fa-user`) agregado al `button_box` (primero de la fila, es el dato operativo más consultado), y nuevo `views/device_assignment_views.xml` con list/form propios (antes no existía ninguna vista standalone para el modelo).

---

## 4. Quick Wins Aplicados — Detalle Técnico

| Archivo | Cambio |
|---|---|
| `models/device_assignment.py` | + `_check_device_available_for_assignment` (constraint H3) |
| `models/device_management.py` | `action_retire_device` con cascada a `devuelto` (H1); + `assignment_count` / `_compute_assignment_count` / `action_view_assignments` (H5) |
| `views/device_management_views.xml` | + botón inteligente "Asignaciones" en `button_box` (H5) |
| `views/device_assignment_views.xml` | **Nuevo archivo** — list + form de `device.assignment` (H5) |
| `security/ir.model.access.csv` | `access_device_subscription_manager`: `perm_create` 0→1 (H4) |
| `data/ir_cron_data.xml` | + `cron_device_refresh_alert_counts`, diario 06:00 (H2) |
| `__manifest__.py` | versión `19.0.1.3.0` → `19.0.1.4.0`; registrado `device_assignment_views.xml`; changelog en descripción |
| `CHANGELOG.md` | entrada `2026-08-17` con el detalle de los 5 fixes |

No se tocó ningún archivo fuera de `custom_addons/md_asset_devices/` — el resto del repo local tenía cambios previos sin commitear de otro módulo (`bi_pos_stock`) que no forman parte de esta tarea y se dejaron intactos.

---

## 5. Verificación

Script `odoo shell` (transacción con rollback, sin `commit()`), 16/16 checks OK:

1. Cron `cron_device_refresh_alert_counts` registrado y activo.
2. `device.subscription` Manager con `perm_create=True`.
3. Vistas `view_device_assignment_form`/`view_device_assignment_list` existen.
4. `assignment_count` inicial en 0 para un dispositivo nuevo.
5. `action_view_assignments()` retorna un `ir.actions.act_window` válido apuntando a `device.assignment`.
6. `assignment_count` sube a 1 tras crear una asignación activa; `usuario_asignado` se sincroniza en el dispositivo.
7. Crear una asignación `activa` sobre un dispositivo en `maintenance` → `ValidationError` (H3).
8. Retirar un dispositivo con una asignación activa → la asignación pasa a `devuelto` con `fecha_devolucion`, y `usuario_asignado` del dispositivo se limpia (H1).
9. Crear una asignación `activa` sobre un dispositivo `retired` → `ValidationError` (H3).
10. `get_view()` del form principal: botón y campo del smart button presentes en el arch.
11. `get_view()` de `device.assignment` en modo lista: renderiza sin error.

Confirmado por SQL directo que la transacción de prueba no dejó residuos (`REGISTROS_TEST_AUDIT: 0`).

`docker restart medicinedepot_dev_odoo` + `-u md_asset_devices` sin errores ni warnings del módulo propio (197/197 módulos cargados).

### 5.1 Segunda ronda (mismo día) — hoja de ruta

Tras revisar este documento, se pidió continuar con 3 de los pendientes de la sección 6 original. Los tres quedaron corregidos y verificados (6/6 checks OK, mismo patrón de rollback):

- **H6 — Misma validación para mantenimientos.** Nueva `@api.constrains('device_id')` en `device.maintenance` (`_check_device_not_retired`): bloquea programar un mantenimiento nuevo sobre un dispositivo `retired`. `action_completar` se ajustó para no agendar el seguimiento automático (`proximo_mantenimiento`) si el dispositivo fue retirado mientras el mantenimiento seguía abierto — sin este ajuste, cerrar un mantenimiento heredado de antes del retiro habría reventado con la nueva constraint.
- **H7 — Menú standalone de Asignaciones.** Nuevo `action_device_assignment` + `menu_device_management_asignaciones` (Activos IT ▶ Asignaciones) + `view_device_assignment_search` (filtros Activas/Devueltas, agrupar por usuario/estado/dispositivo, `search_default_activas=1`). Permite a RRHH ver "qué tiene cada empleado" sin entrar dispositivo por dispositivo.
- **H8 — Limpieza de `ir.rule` muerta.** Se eliminó `device_subscription_credentials_rule` del XML; al correr `-u` Odoo la borró automáticamente de la base (`Deleting ... ir.rule (device_subscription_credentials_rule)` en el log), confirmando que no quedó huérfana. Se dejó un comentario en su lugar explicando que la protección real de `usuario`/`contrasena` es el `groups=` a nivel de campo.

Verificación (odoo shell, rollback, 6/6 OK): regla eliminada, acción/menú/búsqueda de asignaciones existen, bloqueo de mantenimiento en dispositivo retirado lanza `ValidationError`, y `action_completar` sobre un mantenimiento cuyo dispositivo se retiró mientras estaba `in_progress` no intenta crear el seguimiento (0 registros creados, sin excepción).

Versión final: **`19.0.1.5.0`**.

---

## 6. Hoja de Ruta — Pendientes Restantes

- **`device.payment` sin acción rápida "Marcar pagado".** Hoy se marca con el toggle del campo `pagado` en la lista embebida, lo cual funciona pero no dispara ningún efecto secundario (ej. no hay hook para conciliar contra la factura vinculada en `invoice_id`). No es un bloqueo, es una oportunidad de automatización futura si el volumen de pagos crece.
- **Validación visual en Chrome pendiente.** Si se habilita un usuario de prueba con sesión ya iniciada en el perfil de Chrome usado por Claude, o se resuelve el acceso sin credenciales manuales, vale la pena repetir el recorrido completo (creación → folio secuencial → asignación → mantenimiento → retiro) para confirmar visualmente lo que aquí se validó por `odoo shell`.
