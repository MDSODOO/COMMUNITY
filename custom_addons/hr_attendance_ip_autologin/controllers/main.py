import logging

from odoo.http import request, route
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session

_logger = logging.getLogger(__name__)


class HomeIPAutoCheckin(Home):
    """Intercepta /web/login (heredado sin cambiar la ruta) para intentar un
    check-in automático justo después de un login interactivo exitoso.

    No se sobrescribe res.users.authenticate/_check_credentials: en Odoo 19
    hay varias rutas de autenticación (password, OAuth/SSO, 2FA, API keys) y
    no todas pasan por el mismo método -- este controlador solo cubre el
    login web clásico via formulario, que es el caso de uso pedido
    ("el empleado abre sesión en el navegador desde la sucursal").
    """

    @route()
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)

        # request.params['login_success'] solo es True cuando este mismo
        # request acaba de autenticar por POST -- distingue un login real de
        # una simple recarga de /web/login con una sesion ya existente.
        if request.params.get("login_success") and request.session.uid:
            try:
                request.env["hr.employee"].sudo()._auto_checkin_by_ip(
                    request.session.uid, request.httprequest.remote_addr
                )
            except Exception:
                # Nunca bloquear el login por un fallo de esta funcionalidad
                # accesoria.
                _logger.exception(
                    "hr_attendance_ip_autologin: fallo al intentar el "
                    "check-in automatico por IP"
                )

        return response


class SessionAutoCheckout(Session):
    """Intercepta /web/session/logout (la ruta real que dispara el botón
    "Cerrar sesión" del menú de usuario -- NO /web/session/destroy, que es
    jsonrpc y la usan otros flujos como auth_timeout).

    OJO: Session.logout() llama primero a request.session.clear() (borra
    el uid) y solo después al hook oficial ir.http._post_logout() -- para
    ese momento request.env ya es el usuario público. Por eso el checkout
    debe correr ANTES de llamar a super().logout(), leyendo
    request.session.uid mientras todavía existe.
    """

    @route()
    def logout(self, redirect="/odoo"):
        user_id = request.session.uid
        if user_id:
            try:
                request.env["hr.employee"].sudo()._auto_checkout_by_session(user_id)
            except Exception:
                # Nunca bloquear el logout por un fallo de esta funcionalidad
                # accesoria (mismo criterio que _auto_checkin_by_ip).
                _logger.exception(
                    "hr_attendance_ip_autologin: fallo al intentar el "
                    "check-out automatico por logout explicito"
                )
        return super().logout(redirect=redirect)
