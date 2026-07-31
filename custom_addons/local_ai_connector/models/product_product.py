# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def recommend_products_by_substance(self, substance_name, limit=5, company_id=None):
        """Retorna entre 3 y 5 recomendaciones de productos por sustancia activa,
        
        incluyendo el precio y la cantidad física 'A la mano' (On Hand) por sucursal.
        """
        if not substance_name:
            return []

        ctx = dict(self.env.context)
        if company_id:
            ctx["allowed_company_ids"] = [company_id]

        substance_clean = substance_name.strip()
        domain = [
            ("qty_available", ">", 0),  # Solo productos con unidades físicamente 'A la mano' (On Hand)
            "|", "|",
            ("active_substance_ids.name", "=ilike", f"%{substance_clean}%"),
            ("name", "=ilike", f"%{substance_clean}%"),
            ("product_line_id.name", "=ilike", f"%{substance_clean}%"),
        ]

        products = self.with_context(ctx).search(domain, limit=limit)
        results = []
        for p in products:
            results.append({
                "product_id": p.id,
                "display_name": p.display_name,
                "barcode": p.barcode or "",
                "list_price": p.list_price,
                "qty_on_hand": p.qty_available,  # Cantidad física 'A la mano' (On Hand)
                "uom_name": p.uom_id.name if p.uom_id else "",
                "image_url": f"/web/image/product.product/{p.id}/image_128",
                "active_substances": p.active_substance_ids.mapped("name"),
            })

        return results
