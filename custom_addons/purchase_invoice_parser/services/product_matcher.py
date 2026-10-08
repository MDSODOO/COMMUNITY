import logging

_logger = logging.getLogger(__name__)


class ProductMatcher:
    """
    Estrategia de matching para conceptos CFDI:
    1. Barcode exacto (NoIdentificacion suele ser EAN-13)
    2. Referencia interna (default_code)
    3. Código de proveedor en product.supplierinfo
    4. Nombre ilike (fallback — requiere revisión manual)
    """

    BRUDIFARMA_RFC = 'BRU971010227'

    def __init__(self, env):
        self.env = env

    @staticmethod
    def _normalize_code(value):
        return (value or '').strip()

    def _search_default_code(self, code):
        Product = self.env['product.product']
        normalized = self._normalize_code(code)
        if not normalized:
            return Product.browse()

        # Intento exacto y fallback sin ceros a la izquierda para referencias
        # internas heredadas de proveedores externos.
        candidates = [normalized]
        compact = normalized.lstrip('0')
        if compact and compact != normalized:
            candidates.append(compact)

        for candidate in candidates:
            product = Product.search(
                [('default_code', '=ilike', candidate)],
                limit=1,
            )
            if product:
                return product
        return Product.browse()

    def _search_supplierinfo_code(self, code, partner_id):
        if not partner_id:
            return None

        normalized = self._normalize_code(code)
        if not normalized:
            return None

        candidates = [normalized]
        compact = normalized.lstrip('0')
        if compact and compact != normalized:
            candidates.append(compact)

        for candidate in candidates:
            sinfo = self.env['product.supplierinfo'].search([
                ('partner_id', '=', partner_id),
                ('product_code', '=ilike', candidate),
            ], limit=1)
            if sinfo and sinfo.product_id:
                return sinfo.product_id
        return None

    def find_product(
        self,
        no_identificacion=None,
        descripcion=None,
        partner_id=None,
        supplier_rfc=None,
    ):
        """Retorna (product, confidence, method)."""
        Product = self.env['product.product']
        supplier_rfc = (supplier_rfc or '').upper().strip()
        code = self._normalize_code(no_identificacion)

        if code:
            if supplier_rfc == self.BRUDIFARMA_RFC:
                product = self._search_default_code(code)
                if product:
                    return product, 0.99, 'brudifarma_default_code'

                product = self._search_supplierinfo_code(code, partner_id)
                if product:
                    return product, 0.96, 'brudifarma_supplierinfo_code'

                product = Product.search([('barcode', '=', code)], limit=1)
                if product:
                    return product, 0.9, 'brudifarma_barcode_fallback'

                # Para BRUDIFARMA preferimos no caer a nombre cuando sí hubo
                # código pero no match determinista; evita asignaciones erróneas.
                return None, 0.0, 'brudifarma_unresolved_code'
            else:
                product = Product.search([('barcode', '=', code)], limit=1)
                if product:
                    return product, 1.0, 'barcode_exact'

                product = self._search_default_code(code)
                if product:
                    return product, 0.95, 'default_code'

                product = self._search_supplierinfo_code(code, partner_id)
                if product:
                    return product, 0.95, 'supplierinfo_code'

        if descripcion:
            product = Product.search([
                ('name', 'ilike', descripcion[:30]),
                ('purchase_ok', '=', True),
            ], limit=1)
            if product:
                return product, 0.6, 'name_ilike'

        return None, 0.0, 'unresolved'
