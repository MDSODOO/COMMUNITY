from odoo import http, _
from odoo.http import request

from odoo.addons.custom_shop_qty_selector.controllers.main import (
    resolve_warehouse,
    lot_filtered_stock_qty_map,
)


class CartBarcodeScannerController(http.Controller):

    def _qty_a_la_mano(self, product, warehouse_id):
        """Cantidad 'A la mano' (On Hand) para un product.product, con el
        mismo criterio que el resto del sitio: sucursal/almacen del cliente
        B2B via resolve_warehouse(), y solo lotes vigentes (>6 meses de
        caducidad) para productos trackeados por lote/serie.
        """
        if not product.is_storable:
            return None  # servicio/consumible: sin limite de existencia fisica
        if product.tracking in ('lot', 'serial'):
            return lot_filtered_stock_qty_map(product, warehouse_id).get(product.id, 0)
        return max(0, int(product.with_context(warehouse_id=warehouse_id).free_qty or 0))

    @http.route(
        '/shop/cart/scan_barcode',
        type='jsonrpc',
        auth='user',
        methods=['POST'],
        website=True,
    )
    def scan_barcode_add_to_cart(self, barcode, quantity=1, **kwargs):
        """Recibe un codigo de barras leido por camara, valida 'A la mano'
        (On Hand) y agrega la cantidad al carrito activo.

        auth='user': solo clientes B2B ya autenticados/aprobados pueden
        escanear. Mismo gate que resolve_warehouse(), que ya trata al
        visitante publico como sin acceso a datos de existencia fisica
        (custom_shop_qty_selector/controllers/main.py).
        """
        barcode = (barcode or '').strip()
        if not barcode:
            return {'success': False, 'error_code': 'invalid_barcode',
                    'message': _('Codigo de barras vacio o invalido.')}

        try:
            quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            quantity = 1

        # Sin sudo(): que aplique el ACL normal del portal + el dominio de
        # catalogo del sitio (sale_ok / website_published), igual que el
        # add_to_cart nativo de website_sale.
        product = request.env['product.product'].search([
            ('barcode', '=', barcode),
            ('sale_ok', '=', True),
            ('website_published', '=', True),
        ], limit=1)
        if not product or not product._is_add_to_cart_allowed():
            return {'success': False, 'error_code': 'not_found',
                    'message': _('No se encontro ningun producto con ese codigo de barras.')}

        warehouse_id = resolve_warehouse()
        if warehouse_id is None:
            return {'success': False, 'error_code': 'not_approved',
                    'message': _('Tu cuenta no tiene acceso a existencia "A la mano" (On Hand).')}

        qty_on_hand = self._qty_a_la_mano(product, warehouse_id)

        if qty_on_hand is not None and qty_on_hand <= 0:
            return {'success': False, 'error_code': 'no_stock',
                    'message': _('No hay piezas "A la mano" (On Hand) para "%s".', product.display_name)}

        order_sudo = request.cart or request.website._create_cart()
        # El limite "A la mano" aplica al TOTAL en el carrito, no solo a lo
        # que se esta agregando ahora: si el cliente escanea el mismo
        # producto dos veces, la segunda pasada debe sumarse a lo que ya
        # tiene en el carrito antes de comparar contra qty_on_hand. Sin esto,
        # Odoo (_cart_add) igual lo rechaza por su cuenta pero con un warning
        # en ingles que no respeta el termino "A la mano" (bug real detectado
        # probando: "You ask for 4 X but only 3 is available").
        existing_line = order_sudo.order_line.filtered(
            lambda l: l.product_id.id == product.id and not l.display_type
        )
        qty_already_in_cart = sum(existing_line.mapped('product_uom_qty'))
        total_requested = qty_already_in_cart + quantity

        if qty_on_hand is not None and total_requested > qty_on_hand:
            return {
                'success': False,
                'error_code': 'insufficient_stock',
                'message': _(
                    'Solo hay %(qty)s "A la mano" (On Hand) para "%(name)s"'
                    ' (ya tienes %(in_cart)s en tu carrito).',
                    qty=qty_on_hand, name=product.display_name, in_cart=int(qty_already_in_cart),
                ),
                'qty_on_hand': qty_on_hand,
            }

        values = order_sudo.with_context(skip_cart_verification=True)._cart_add(
            product_id=product.id,
            quantity=quantity,
        )
        if values.get('warning'):
            # Defensa en profundidad: si Odoo igual genera un warning (p.ej.
            # una condicion de carrera con otro cliente vaciando existencia
            # entre nuestro chequeo y el _cart_add), NUNCA se reenvia el
            # texto nativo de Odoo al usuario porque no respeta el termino
            # obligatorio "A la mano" y suele venir en ingles.
            return {
                'success': False,
                'error_code': 'cart_warning',
                'message': _(
                    'No se pudo agregar "%s": ya no hay suficiente "A la mano" (On Hand).',
                    product.display_name,
                ),
            }

        order_sudo._verify_cart_after_update()

        return {
            'success': True,
            'product_id': product.id,
            'product_name': product.display_name,
            'added_qty': values.get('added_qty', quantity),
            'qty_on_hand': qty_on_hand,
            'cart_quantity': order_sudo.cart_quantity,
            'amount_total': order_sudo.amount_total,
            'currency_symbol': order_sudo.currency_id.symbol,
        }
