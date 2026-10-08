import logging
import re

_logger = logging.getLogger(__name__)


class LotStockResolver:
    """
    Resuelve stock.lot en batch para evitar el patrón N+1 con soporte de matching
    fuzzy inteligente (normalización de prefijos LOTE/LT/L-, ceros a la izquierda y caracteres especiales).

    Uso:
        resolver = LotStockResolver(env, company_id)
        resolver.preload(product_ids, lot_names)   # 1 query total
        lot = resolver.find(product, lot_name)      # lookup O(k) en memoria con fallback fuzzy
        lot = resolver.ensure(product, lot_name, expiration_date)  # crea o hereda caducidad
    """

    def __init__(self, env, company_id):
        self.env = env
        self.company_id = company_id
        self._by_product = {}  # {product_id: [(name_stripped, lot_record)]}
        self._preloaded = False

    def preload(self, product_ids, lot_names=None):
        """
        Pre-carga todos los lotes de los productos dados en una sola query.
        lot_names es ignorado intencionalmente: se traen todos para permitir
        matching por código compacto sin queries adicionales.
        """
        if not product_ids:
            return
        StockLot = self.env['stock.lot'].sudo().with_context(active_test=False)
        lots = StockLot.search([
            ('product_id', 'in', list(product_ids)),
        ])
        self._by_product = {}
        for lot in lots:
            lot = self._as_global_lot(lot)
            pid = lot.product_id.id
            if pid not in self._by_product:
                self._by_product[pid] = []
            self._by_product[pid].append((lot.name.strip(), lot))
        self._preloaded = True

    @staticmethod
    def _compact(value):
        """
        Normaliza códigos de lotes eliminando prefijos habituales (LOTE, LT, L-, #, etc.),
        ceros a la izquierda, guiones, barras y espacios para comparación robusta.
        """
        normalized = (value or '').strip().upper()
        if not normalized:
            return ''
        # Remover prefijos comunes de facturas mexicanas
        normalized = re.sub(r'^(?:LOTE|LT|LOT|L|NO|NUM|#|LOTE:)\s*[-:]*\s*', '', normalized, flags=re.IGNORECASE)
        # Remover caracteres de puntuación separadores
        normalized = re.sub(r'[\s\-_\/\\\.:,]', '', normalized)
        if normalized.isdigit():
            return normalized.lstrip('0') or '0'
        return normalized

    def _as_global_lot(self, lot):
        if not lot or not lot.company_id:
            return lot

        StockLot = self.env['stock.lot'].sudo().with_context(active_test=False)
        global_lot = StockLot.search([
            ('name', '=', (lot.name or '').strip()),
            ('product_id', '=', lot.product_id.id),
            ('company_id', '=', False),
        ], limit=1)
        if global_lot:
            return global_lot

        try:
            with self.env.cr.savepoint():
                lot.sudo().write({'company_id': False})
            return lot
        except Exception:
            _logger.exception(
                "No se pudo convertir el lote %s del producto %s a global.",
                lot.name,
                lot.product_id.display_name,
            )
            global_lot = StockLot.search([
                ('name', '=', (lot.name or '').strip()),
                ('product_id', '=', lot.product_id.id),
                ('company_id', '=', False),
            ], limit=1)
            if global_lot:
                return global_lot
            raise

    def _cache_lot(self, lot):
        if not lot:
            return lot
        pid = lot.product_id.id
        if pid not in self._by_product:
            self._by_product[pid] = []
        if lot.id not in [cached_lot.id for _name, cached_lot in self._by_product[pid]]:
            self._by_product[pid].append((lot.name.strip(), lot))
        return lot

    def _search_db_lot(self, product, lot_name, operator='='):
        StockLot = self.env['stock.lot'].sudo().with_context(active_test=False)
        lot = StockLot.search([
            ('product_id', '=', product.id),
            ('name', operator, lot_name),
        ], limit=1)
        return self._cache_lot(self._as_global_lot(lot)) if lot else False

    def _find_or_convert_to_global(self, product, lot_name):
        if not product or not lot_name:
            return False

        lot_name_stripped = (lot_name or '').strip()
        if not lot_name_stripped:
            return False

        StockLot = self.env['stock.lot'].sudo().with_context(active_test=False)

        # Paso 1: Buscar lote global (company_id = False)
        global_lot = StockLot.search([
            ('product_id', '=', product.id),
            ('name', '=ilike', lot_name_stripped),
            ('company_id', '=', False),
        ], limit=1)
        if global_lot:
            return self._cache_lot(global_lot)

        # Paso 2: Buscar lote empresa-específico y convertir a global
        company_lot = StockLot.search([
            ('product_id', '=', product.id),
            ('name', '=ilike', lot_name_stripped),
            ('company_id', '!=', False),
        ], limit=1)
        if company_lot:
            try:
                with self.env.cr.savepoint():
                    company_lot.sudo().write({'company_id': False})
                return self._cache_lot(company_lot)
            except Exception:
                _logger.exception(
                    "No se pudo convertir el lote %s del producto %s a global.",
                    lot_name_stripped,
                    product.display_name,
                )
                retry_lot = StockLot.search([
                    ('product_id', '=', product.id),
                    ('name', '=ilike', lot_name_stripped),
                    ('company_id', '=', False),
                ], limit=1)
                if retry_lot:
                    return self._cache_lot(retry_lot)
                raise

        return False

    def find(self, product, lot_name):
        """
        Busca un lote por producto y nombre aplicando coincidencia jerárquica:
        1. Exact case-insensitive.
        2. Código compacto (remueve prefijos LOTE/LT/L-, guiones y ceros a la izq).
        3. Contención fuzzy para códigos de longitud >= 4.
        """
        if not product or not lot_name:
            return False
        lot_name = lot_name.strip()
        if not lot_name:
            return False
        lot_name_lower = lot_name.lower()
        compact_target = self._compact(lot_name)

        if self._preloaded:
            product_lots = self._by_product.get(product.id, [])
            # 1. Exact match
            for name, lot in product_lots:
                if name.lower() == lot_name_lower:
                    return self._cache_lot(self._as_global_lot(lot))
            # 2. Compact match
            if compact_target:
                for name, lot in product_lots:
                    if self._compact(name) == compact_target:
                        return self._cache_lot(self._as_global_lot(lot))
            # 3. Fuzzy substring match (solo para códigos con longitud >= 4)
            if compact_target and len(compact_target) >= 4:
                for name, lot in product_lots:
                    comp_name = self._compact(name)
                    if comp_name and len(comp_name) >= 4 and (compact_target in comp_name or comp_name in compact_target):
                        return self._cache_lot(self._as_global_lot(lot))
            return False

        # Sin preload: búsqueda directa en base de datos
        existing = self._search_db_lot(product, lot_name, '=ilike')
        if existing:
            return existing
        if compact_target and compact_target != lot_name:
            candidates = self._search_db_lot(product, compact_target, '=ilike')
            if candidates:
                return candidates
        return False

    def ensure(self, product, lot_name, expiration_date=False):
        """Devuelve el lote existente o lo crea (patrón get-or-create multiempresa con herencia de caducidad)."""
        has_expiry = 'expiration_date' in self.env['stock.lot']._fields
        lot_name_stripped = (lot_name or '').strip()

        if not product or not lot_name_stripped:
            return False

        # Capa 1: Búsqueda en memoria con matching fuzzy/compacto
        existing = self.find(product, lot_name_stripped)
        if existing:
            if expiration_date and has_expiry and not existing.expiration_date:
                existing.sudo().expiration_date = expiration_date
            return existing

        # Capa 2: Búsqueda robusta en BD
        db_lot = self._find_or_convert_to_global(product, lot_name_stripped)
        if db_lot:
            if expiration_date and has_expiry and not db_lot.expiration_date:
                db_lot.sudo().expiration_date = expiration_date
            return self._cache_lot(db_lot)

        # Capa 3: Crear nuevo lote global
        lot_vals = {
            'name': lot_name_stripped,
            'product_id': product.id,
            'company_id': False,
        }
        if has_expiry:
            lot_vals['expiration_date'] = expiration_date or False

        try:
            with self.env.cr.savepoint():
                new_lot = self.env['stock.lot'].sudo().create(lot_vals)
        except Exception:
            _logger.exception(
                "No se pudo crear el lote global %s para el producto %s.",
                lot_name_stripped,
                product.display_name,
            )
            retry_lot = self._find_or_convert_to_global(product, lot_name_stripped)
            if retry_lot:
                return self._cache_lot(retry_lot)
            raise

        return self._cache_lot(new_lot)
