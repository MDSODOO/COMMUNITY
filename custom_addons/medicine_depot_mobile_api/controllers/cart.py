# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from ..utils.token_helper import mobile_auth_required


def _serialize_cart(order):
    return {
        'id': order.id,
        'state': order.state,
        'amount_untaxed': order.amount_untaxed,
        'amount_tax': order.amount_tax,
        'amount_total': order.amount_total,
        'lines': [{
            'id': line.id,
            'product_id': line.product_id.product_tmpl_id.id,
            'product_name': line.product_id.display_name,
            'qty': line.product_uom_qty,
            'price_unit': line.price_unit,
            'price_subtotal': line.price_subtotal,
        } for line in order.order_line],
    }


def _empty_cart():
    return {
        'id': None, 'state': 'draft', 'amount_untaxed': 0.0,
        'amount_tax': 0.0, 'amount_total': 0.0, 'lines': [],
    }


def _get_active_cart(env, partner):
    return env['sale.order'].sudo().search([
        ('partner_id', '=', partner.id),
        ('state', '=', 'draft'),
        ('x_mobile_cart', '=', True),
    ], limit=1, order='id desc')


def _get_or_create_active_cart(env, user):
    order = _get_active_cart(env, user.partner_id)
    if order:
        return order
    return env['sale.order'].sudo().create({
        'partner_id': user.partner_id.id,
        'x_mobile_cart': True,
        'origin': 'Medicine Depot Mobile App',
    })


class MobileCartController(http.Controller):

    @http.route('/api/mobile/v1/cart', type='http', auth='public', methods=['GET'], csrf=False)
    @mobile_auth_required
    def get_cart(self, user=None, **kw):
        order = _get_active_cart(request.env, user.partner_id)
        return request.make_json_response(_serialize_cart(order) if order else _empty_cart())

    @http.route('/api/mobile/v1/cart/lines', type='http', auth='public', methods=['POST'], csrf=False)
    @mobile_auth_required
    def set_line(self, user=None, **kw):
        """Fija la cantidad absoluta de un producto en el carrito (no
        incrementa) -- idempotente ante reintentos del cliente móvil.
        product_id se refiere a product.template (mismo id que devuelve
        /catalog/products), se resuelve internamente a la variante."""
        env = request.env
        body = request.get_json_data() or {}
        try:
            product_tmpl_id = int(body.get('product_id'))
            qty = float(body.get('qty'))
        except (TypeError, ValueError):
            return request.make_json_response({'error': 'invalid_product_or_qty'}, status=400)
        if qty < 0:
            return request.make_json_response({'error': 'invalid_qty'}, status=400)

        template = env['product.template'].sudo().browse(product_tmpl_id)
        if not template.exists() or not template.sale_ok or not template.active:
            return request.make_json_response({'error': 'product_not_found'}, status=404)
        product = template.product_variant_id
        if not product:
            return request.make_json_response({'error': 'product_not_found'}, status=404)

        order = _get_or_create_active_cart(env, user)
        line = order.order_line.filtered(lambda l: l.product_id.id == product.id)
        if qty == 0:
            line.unlink()
        elif line:
            line.product_uom_qty = qty
        else:
            env['sale.order.line'].sudo().create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': qty,
            })
        return request.make_json_response(_serialize_cart(order))

    @http.route('/api/mobile/v1/cart/confirm', type='http', auth='public', methods=['POST'], csrf=False)
    @mobile_auth_required
    def confirm(self, user=None, **kw):
        env = request.env
        order = _get_active_cart(env, user.partner_id)
        if not order or not order.order_line:
            return request.make_json_response({'error': 'empty_cart'}, status=400)
        try:
            order.action_confirm()
        except Exception as exc:
            return request.make_json_response({'error': 'confirm_failed', 'detail': str(exc)}, status=400)
        return request.make_json_response(_serialize_cart(order))
