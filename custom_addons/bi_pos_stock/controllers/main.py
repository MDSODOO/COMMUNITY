# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class BiPosStockUiController(http.Controller):
    """Return a valid HTTP response for custom POS screen deep links.

    The stock screens are OWL client routes registered in the POS router. When a
    controlled PWA page is refreshed directly on one of those paths, the browser
    still performs an HTTP navigation to the custom route. Returning a Werkzeug
    redirect keeps the Service Worker from receiving a malformed or rejected
    response while preserving the POS shell as the canonical entry point.
    """

    @http.route(
        [
            "/pos/ui/<int:config_id>/stock",
            "/pos/ui/<int:config_id>/low-stock",
            "/pos/ui/<int:config_id>/ecommerce-orders",
        ],
        type="http",
        auth="user",
        website=False,
        sitemap=False,
    )
    def pos_custom_screen_entrypoint(self, config_id, **kwargs):
        target = "/pos/ui/%s" % config_id
        query_string = request.httprequest.query_string.decode("utf-8")
        if query_string:
            target = "%s?%s" % (target, query_string)
        return request.redirect(target, code=302)
