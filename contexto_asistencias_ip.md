# 🛡️ Contexto Técnico y Plan de Refactorización: Asistencias por IP (`hr_attendance_ip_autologin`)

## 1. Resumen de Arquitectura Actual

El módulo `hr_attendance_ip_autologin` implementa un control de asistencias automático basado en la IP pública de la sucursal.

### Componentes Clave:
- **Controlador (`controllers/main.py`)**:
  - Hereda `web.controllers.home.Home.web_login` para interceptar inicios de sesión web interactivos (`login_success == True`).
  - Hereda `web.controllers.session.Session.logout` para registrar el `check-out` automático antes de destruir la sesión.
- **Modelo de Sucursal (`res_company` & `hr_attendance_authorized_ip`)**:
  - Relación `One2many` entre `res.company` (1 compañía = 1 sucursal) e `hr.attendance.authorized.ip`.
  - Soporta direcciones IP estáticas individuales (ej. `189.203.10.5`) o rangos CIDR (ej. `189.203.10.0/24`) validados con la librería `ipaddress`.
- **Lógica de Check-in / Check-out (`models/hr_employee.py`)**:
  - `_auto_checkin_by_ip(user_id, remote_ip)`: Busca todos los registros `hr.employee` ligados al `res.users` (soporte multi-compañía), evalúa las IPs autorizadas de la sucursal de cada empleado y ejecuta `_attendance_action_change()` si coincide y su estado es `checked_out`.
  - `_auto_checkout_by_session(user_id)`: Cierra las asistencias abiertas al hacer logout explícito.
  - `_cron_auto_checkout_abandoned_sessions()`: Cron que cierra asistencias sin `check_out` cuyo heartbeat (`mail.presence.last_poll`) haya superado el tiempo de inactividad (por defecto 8 horas).

---

## 2. Vulnerabilidades y Puntos de Mejora Identificados

1. **Captura de IP y Proxy Spoofing**:
   - Actualmente se usa `request.httprequest.remote_addr`. Si Odoo opera tras proxies reversos (Nginx/Caddy/Docker bridge) y `proxy_mode = True`, es fundamental asegurar que la IP real provenga de la cabecera `X-Forwarded-For` confiable y no sea manipulable por el cliente.
2. **Notificación en UI (Experiencia de Usuario)**:
   - El check-in actual ocurre en backend sin retroalimentación visual al usuario. Si el usuario ingresa desde una IP no autorizada, no recibe una alerta explícita explicando por qué su asistencia no se marcó automáticamente.
3. **Manejo de Redes NAT Compartidas / Dinámicas**:
   - Las sucursales con IPs dinámicas o enlaces redundantes (Failover WAN) requieren soporte para múltiples rangos o dominios DDNS.
4. **Validación IPv6**:
   - Aunque `ipaddress.ip_network` soporta IPv6, se debe garantizar la normalización de la dirección provista por la cabecera HTTP.

---

## 3. Prompt de Instrucciones para Claude Code

```markdown
Actúa como un Desarrollador Senior de Odoo 19 (Python/OWL) y Especialista en Seguridad.

Conéctate vía SSH (`ssh ionos`) y refactoriza el módulo `hr_attendance_ip_autologin` en `/opt/medicinedepot-odoo19-migration/custom_addons/hr_attendance_ip_autologin/`.

### 🎯 Tareas de Refactorización:

1. **Seguridad y Extracción de IP (`controllers/main.py` y `models/hr_employee.py`)**:
   - Implementa un helper seguro `_get_client_ip(request)` que lea correctamente la IP pública real considerando `X-Forwarded-For` y `proxy_mode`.
   - Agrega logs estructurados advirtiendo intentos de login desde IPs no autorizadas.

2. **Feedback Visual en UI (Toast Notifications)**:
   - Al completar el login exitoso (`web_login`), si se registra la asistencia automáticamente, inyecta un parámetro temporal en la sesión para que el cliente web muestre una notificación Toast en la esquina superior derecha:
     - 🟢 **Éxito**: *"Asistencia registrada automáticamente en Sucursal [Nombre]"*.
     - 🟡 **IP no autorizada**: *"Conectado desde IP no registrada ([IP]). La asistencia no fue marcada automáticamente."*

3. **Actualización de Módulo**:
   ```bash
   docker exec medicinedepot_dev_odoo odoo -d medicinedepot_dev --db_host=db --db_port=5432 --db_user=odoo --db_password='<DB_PASSWORD_REDACTED>' -u hr_attendance_ip_autologin --stop-after-init --no-http
   docker restart medicinedepot_dev_odoo
   ```

4. **Verificación QA**:
   - Ejecuta la prueba de Playwright `tests/e2e/attendance_ip_audit.spec.ts` para verificar la captura de la cabecera `X-Forwarded-For`.
```
