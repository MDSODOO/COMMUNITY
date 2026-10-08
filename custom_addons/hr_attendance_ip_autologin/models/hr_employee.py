import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

ABANDONED_SESSION_TIMEOUT_HOURS_DEFAULT = 8


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _auto_checkin_by_ip(self, user_id, remote_ip):
        """Marca el check-in del empleado si remote_ip coincide con una IP
        autorizada de su sucursal (res.company) y no tiene ya una entrada
        abierta. Se llama desde el controlador de login, con sudo().

        Un mismo res.users puede tener un hr.employee por cada compañía
        (confirmado en esta instancia: el usuario Administrator tiene 6).
        Por eso se recorren TODOS los empleados del usuario y se hace
        check-in en el primero cuya sucursal coincida con la IP -- nunca se
        asume que el primer resultado de una búsqueda sea el correcto.
        """
        if not remote_ip:
            return False

        employees = self.search([("user_id", "=", user_id)])
        for employee in employees:
            if not employee.company_id:
                continue

            authorized_ips = employee.company_id.attendance_authorized_ip_ids.filtered("active")
            if not any(rec._matches(remote_ip) for rec in authorized_ips):
                continue

            if employee.attendance_state != "checked_out":
                # Ya tiene una entrada abierta (o el estado no aplica) --
                # nada que hacer para este empleado.
                continue

            employee._attendance_action_change()
            _logger.info(
                "hr_attendance_ip_autologin: check-in automático para %s "
                "(empleado #%s, IP %s, sucursal %s)",
                employee.user_id.login, employee.id, remote_ip, employee.company_id.name,
            )
            return True

        return False

    @api.model
    def _auto_checkout_by_session(self, user_id):
        """Cierra (check-out) todas las asistencias abiertas de los
        hr.employee ligados a este res.users -- mismo patrón multi-compañía
        que _auto_checkin_by_ip: un res.users puede tener un hr.employee por
        cada sucursal, y el logout debe cerrar el turno en todas donde
        quedó abierto, no solo en la primera.

        attendance_state es un campo compute SIN store=True (verificado en
        hr_attendance/models/hr_employee.py) -- no se puede filtrar en el
        dominio de search (Odoo lanza ValueError: "Cannot convert ... to
        SQL because it is not stored"). Por eso, igual que
        _auto_checkin_by_ip, se buscan todos los empleados del usuario y el
        estado se filtra en Python, no en el dominio.
        """
        employees = self.search([("user_id", "=", user_id)])
        for employee in employees.filtered(lambda e: e.attendance_state == "checked_in"):
            employee._attendance_action_change()
            _logger.info(
                "hr_attendance_ip_autologin: check-out automático por logout "
                "explícito para %s (empleado #%s, sucursal %s)",
                employee.user_id.login, employee.id, employee.company_id.name,
            )
        return bool(employees)

    @api.model
    def _cron_auto_checkout_abandoned_sessions(self):
        """Cierra asistencias abiertas cuya sesión de backend quedó
        abandonada (navegador cerrado sin pasar por logout explícito).

        Señal de "última actividad real": mail.presence.last_poll -- no
        ir.sessions, que no existe en esta instancia de Odoo 19 CE
        (verificado). mail.presence se actualiza vía el heartbeat del bus
        longpolling del cliente web mientras la pestaña del empleado sigue
        abierta.

        Se excluyen a propósito los hr.employee SIN user_id (empleados que
        marcan solo por Quiosco/código de barras, sin sesión de
        backend/bus) -- cerrarlos aquí sería un falso positivo, del mismo
        tipo que el ya documentado para el check-in en redes NAT
        compartidas (ver docs/ATTENDANCE_BASELINE.md). Por la misma razón,
        un empleado sin ningún mail.presence (nunca hubo heartbeat) se deja
        sin tocar en vez de asumir abandono.

        check_out se fija en presence.last_poll (no en "ahora"), para que
        las horas contabilizadas se acerquen al momento real en que el
        navegador dejó de responder -- esto importa si más adelante estos
        registros alimentan alguna validación de fin de turno que cruce
        horarios de personal con conteos físicos "A la mano" (On Hand) de
        almacén (ver nota de extensión futura en ATTENDANCE_BASELINE.md):
        un check_out inflado por el retraso del cron distorsionaría esa
        validación.
        """
        timeout_hours = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "hr_attendance_ip_autologin.abandoned_session_timeout_hours",
                ABANDONED_SESSION_TIMEOUT_HOURS_DEFAULT,
            )
        )
        threshold = fields.Datetime.now() - timedelta(hours=timeout_hours)

        open_attendances = self.env["hr.attendance"].search([
            ("check_out", "=", False),
            ("employee_id.user_id", "!=", False),
        ])
        for attendance in open_attendances:
            presence = self.env["mail.presence"].search(
                [("user_id", "=", attendance.employee_id.user_id.id)], limit=1
            )
            if not presence or presence.last_poll >= threshold:
                continue  # sigue activo, o nunca hubo heartbeat -- no tocar

            if presence.last_poll <= attendance.check_in:
                # last_poll mas viejo (o igual) que el propio check_in --
                # la señal no dice nada util sobre esta asistencia en
                # particular (p.ej. el heartbeat nunca se refresco desde
                # antes de este check-in). Cerrar aqui violaria la
                # validacion de hr.attendance (check_out no puede ser
                # anterior a check_in) y no hay un valor mejor que
                # "ahora" para ofrecer -- se deja para una corrida futura
                # en vez de adivinar.
                _logger.warning(
                    "hr_attendance_ip_autologin: se omite asistencia #%s de %s "
                    "-- last_poll (%s) no es posterior a check_in (%s)",
                    attendance.id, attendance.employee_id.user_id.login,
                    presence.last_poll, attendance.check_in,
                )
                continue

            try:
                attendance.write({"check_out": presence.last_poll})
            except Exception:
                # Un registro problematico no debe abortar el lote --
                # los demas empleados abandonados de esta corrida deben
                # cerrarse igual.
                _logger.exception(
                    "hr_attendance_ip_autologin: fallo al cerrar la "
                    "asistencia #%s por abandono de sesión", attendance.id,
                )
                continue

            _logger.info(
                "hr_attendance_ip_autologin: check-out automático por "
                "abandono de sesión para %s (asistencia #%s, último "
                "heartbeat %s)",
                attendance.employee_id.user_id.login, attendance.id, presence.last_poll,
            )
