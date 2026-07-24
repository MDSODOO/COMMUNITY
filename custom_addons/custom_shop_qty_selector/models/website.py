from dateutil.relativedelta import relativedelta

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'
    _description = 'Website (MD stock extensions)'

    def _md_lot_expiration_cutoff(self):
        return fields.Datetime.now() + relativedelta(months=6)

    def _md_branch_warehouse(self):
        """Return the stock.warehouse assigned to the authenticated partner's branch.

        Reads res.partner.x_studio_branch_office (Studio field). Supports
        many2one-to-stock.warehouse and name-based char/selection variants.
        Returns empty recordset when the user is public or the field is absent.
        """
        try:
            from odoo.http import request as http_request  # noqa: PLC0415
            user = http_request and http_request.env and http_request.env.user
            if not user or user._is_public():
                return self.env['stock.warehouse'].browse()
            partner = user.partner_id.sudo()
        except Exception:
            return self.env['stock.warehouse'].browse()

        field = partner._fields.get('x_studio_branch_office')
        if not field:
            return self.env['stock.warehouse'].browse()

        value = partner.x_studio_branch_office
        if not value:
            return self.env['stock.warehouse'].browse()

        Warehouse = self.env['stock.warehouse'].sudo()

        if field.type == 'many2one' and getattr(field, 'comodel_name', '') == 'stock.warehouse':
            return value if value.exists() else Warehouse.browse()

        name = (value.display_name if hasattr(value, 'display_name') else str(value) or '').strip().lower()
        if not name:
            return Warehouse.browse()

        return Warehouse.search([('active', '=', True)]).filtered(
            lambda w: (w.display_name or '').strip().lower() == name
            or (w.name or '').strip().lower() == name
        )[:1]

    def _md_lot_filtered_available_qty(self, product):
        self.ensure_one()
        product = product.sudo().exists()
        if not product:
            return 0.0

        # B2B-only: visitors never see branch stock.
        try:
            from odoo.http import request as http_request  # noqa: PLC0415
            _user = http_request and http_request.env and http_request.env.user
            if not _user or _user._is_public():
                return 0.0
        except Exception:
            pass

        warehouse = self._md_branch_warehouse()
        if not warehouse:
            warehouse = self.sudo().warehouse_id
        if not warehouse:
            warehouse = self.env['stock.warehouse'].sudo().search(
                [('company_id', '=', self.company_id.id)],
                limit=1,
            )

        location_domain = [
            ('usage', '=', 'internal'),
            ('company_id', '=', warehouse.company_id.id if warehouse else self.company_id.id),
        ]
        if warehouse and warehouse.lot_stock_id:
            location_domain.insert(0, ('id', 'child_of', warehouse.lot_stock_id.id))
        location_ids = self.env['stock.location'].sudo().search(location_domain).ids
        if not location_ids:
            return 0.0

        quants = self.env['stock.quant'].sudo().search([
            ('company_id', '=', warehouse.company_id.id if warehouse else self.company_id.id),
            ('product_id', '=', product.id),
            ('location_id', 'in', location_ids),
            ('lot_id', '!=', False),
            ('lot_id.expiration_date', '!=', False),
            ('lot_id.expiration_date', '>', self._md_lot_expiration_cutoff()),
            ('quantity', '>', 0),
        ])

        return max(0.0, sum(max(0.0, q.quantity - q.reserved_quantity) for q in quants))

    def _get_product_available_qty(self, product, **kwargs):
        qty = super()._get_product_available_qty(product, **kwargs)
        if not product or not product.is_storable or product.tracking not in ('lot', 'serial'):
            return qty
        return self._md_lot_filtered_available_qty(product)
