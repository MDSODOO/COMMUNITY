from urllib.parse import urlparse

from odoo.http import request

_ALLOWED_ORIGIN_DOMAINS = [
    'medicinedepot.com.mx',
    'www.medicinedepot.com.mx',
    'localhost',
]


def validate_origin():
    """Validate Origin/Referer header to prevent CSRF on public endpoints.

    Public routes with csrf=False are vulnerable to cross-site request
    forgery.  For browser-based clients the Origin (or Referer) header
    reliably identifies the origin site.  If the header is absent (native
    app, curl, …) the request is allowed through.

    Returns a JSON error response if the origin is not allowed, or None.
    """
    http_request = request.httprequest
    origin = http_request.headers.get('Origin')
    if not origin:
        origin = http_request.headers.get('Referer', '')
    if not origin:
        return None

    parsed = urlparse(origin)
    hostname = parsed.hostname or ''

    current_host = http_request.host.split(':')[0]
    if hostname and hostname == current_host:
        return None

    for domain in _ALLOWED_ORIGIN_DOMAINS:
        if hostname == domain or hostname.endswith('.' + domain):
            return None

    return request.make_json_response(
        {'success': False, 'message': 'Origen no permitido'},
        status=403,
    )
