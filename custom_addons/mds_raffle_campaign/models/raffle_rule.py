from odoo import fields, models


class RaffleRule(models.Model):
    _name = 'raffle.rule'
    _description = 'Regla de Premiación de Rifa'
    _order = 'sequence'

    campaign_id = fields.Many2one('raffle.campaign', string='Campaña', required=True, ondelete='cascade')
    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)

    rule_type = fields.Selection([
        ('amount_line', 'Monto gastado por línea de producto'),
        ('product', 'Compra de producto(s) específico(s)'),
        ('order_source', 'Origen del pedido'),
        ('daily_threshold', 'Umbral diario acumulado por cliente y origen'),
        ('daily_sponsor_line', 'Línea patrocinadora en el día (una vez)'),
        ('daily_sponsor_catalog', 'Producto de catálogo patrocinado en el día (una vez)'),
    ], string='Tipo de Regla', required=True)

    # --- amount_line ---
    product_line_ids = fields.Many2many('md.product.line', string='Líneas de producto')
    min_amount = fields.Monetary(string='Monto mínimo')
    computation_mode = fields.Selection([
        ('fixed', 'Boletos fijos al alcanzar el mínimo'),
        ('multiple', 'Boletos por cada múltiplo del mínimo'),
    ], string='Modo de cálculo', default='fixed')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda s: s.env.company.currency_id)

    # --- product ---
    product_ids = fields.Many2many('product.product', string='Productos')
    min_qty = fields.Float(string='Cantidad mínima', default=1.0)

    # --- order_source ---
    source_type = fields.Selection([
        ('pos', 'Venta física (POS)'),
        ('online_b2b', 'Venta en línea B2B'),
        ('backend', 'Venta manual (backoffice)'),
    ], string='Origen')

    tickets_awarded = fields.Integer(string='Boletos otorgados', default=1)

    def _evaluate(self, order):
        """Devuelve la cantidad de boletos que esta regla otorga para
        `order` (sale.order o pos.order ya confirmado/pagado)."""
        self.ensure_one()
        handler = getattr(self, '_evaluate_%s' % self.rule_type, None)
        return handler(order) if handler else 0

    def _evaluate_amount_line(self, order):
        if not self.product_line_ids:
            return 0
        lines = order.order_line if hasattr(order, 'order_line') else order.lines

        # child_of: una regla sobre la línea padre (ej. "JAYOR") también
        # debe capturar ventas de sus sublíneas ("SENSIMEDICAL", "SKINPROT").
        matching_lines = self.env['md.product.line'].search(
            [('id', 'child_of', self.product_line_ids.ids)]
        )
        amount = sum(
            line.price_subtotal for line in lines
            if line.product_id.product_tmpl_id.product_line_id in matching_lines
        )
        if not self.min_amount or amount < self.min_amount:
            return 0
        if self.computation_mode == 'fixed':
            return self.tickets_awarded
        return int(amount // self.min_amount) * self.tickets_awarded

    def _evaluate_product(self, order):
        if not self.product_ids:
            return 0
        lines = order.order_line if hasattr(order, 'order_line') else order.lines
        qty = sum(
            (line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.qty)
            for line in lines if line.product_id in self.product_ids
        )
        return self.tickets_awarded if qty >= self.min_qty else 0

    def _evaluate_order_source(self, order):
        if order._name == 'pos.order':
            origin = 'pos'
        elif order._name == 'sale.order':
            origin = 'online_b2b' if order.origin_channel == 'b2b_online' else 'backend'
        else:
            origin = False
        return self.tickets_awarded if origin and origin == self.source_type else 0

    # --- Consolidación diaria por cliente ---
    # A diferencia de _evaluate(order), estos evaluadores NO reciben un
    # sale.order/pos.order individual: reciben ya el agregado de un
    # cliente para un día natural (uno o varios folios/pedidos sumados),
    # porque un cliente puede dividir su compra en varios folios el mismo
    # día y aun así debe alcanzar el umbral. La agregación (sumar por
    # partner_id+fecha+origen) la hace el llamador (raffle.campaign o el
    # importador de histórico); la regla solo decide cuántos boletos
    # corresponden al bloque ya agregado.

    def _evaluate_daily_threshold(self, origin, amount):
        """origin: 'pos' (físico) u 'online_b2b'. amount: suma diaria del
        cliente para ese origen. Devuelve boletos: tickets_awarded por
        cada múltiplo completo de min_amount alcanzado."""
        if origin != self.source_type or not self.min_amount or not amount:
            return 0
        return int(amount // self.min_amount) * self.tickets_awarded

    def _evaluate_daily_sponsor_line(self, matched_line_ids):
        """matched_line_ids: ids de md.product.line vendidos ese día por
        el cliente (ya resueltos por el llamador). Otorga tickets_awarded
        UNA sola vez si hay al menos una coincidencia, sin importar
        cuántas líneas/unidades distintas se vendieron."""
        if not self.product_line_ids or not matched_line_ids:
            return 0
        matching = self.env['md.product.line'].search(
            [('id', 'child_of', self.product_line_ids.ids)]
        )
        return self.tickets_awarded if matching & self.env['md.product.line'].browse(matched_line_ids) else 0

    def _evaluate_daily_sponsor_catalog(self, matched_product_ids):
        """matched_product_ids: ids de product.product del catálogo
        patrocinado (PATROCINIO) vendidos ese día por el cliente. Otorga
        tickets_awarded UNA sola vez, igual que la línea patrocinadora."""
        if not self.product_ids or not matched_product_ids:
            return 0
        matched = set(self.product_ids.ids) & set(matched_product_ids)
        return self.tickets_awarded if matched else 0
