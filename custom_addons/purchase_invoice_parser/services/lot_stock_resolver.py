import logging

_logger = logging.getLogger(__name__)


class LotStockResolver:
    """
    Resuelve stock.lot en batch para evitar el patrón N+1.

    Uso:
        resolver = LotStockResolver(env, company_id)
        resolver.preload(product_ids, lot_names)   # 1 query total
        lot = resolver.find(product, lot_name)      # lookup O(k) en memoria
        lot = resolver.ensure(product, lot_name, expiration_date)  # crea si no existe
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
        normalized = (value or '').strip()
        if not normalized:
            return ''
        if normalized.isdigit():
            return normalized.lstrip('0') or '0'
        return normalized.upper()

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
        """
        Búsqueda robusta con conversión a global (patrón multiempresa).

        1. Busca lote global (company_id = False) — usa ese si existe.
        2. Si no existe global pero hay uno empresa-específico, lo convierte.
        3. Si no existe en ningún lado, retorna False.

        Esto evita el ValidationError de unicidad en entornos multiempresa
        donde el mismo lote/producto se importa desde varias sucursales.
        """
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
                # Reintentar buscar uno que pudo haber sido creado concurrentemente
                retry_lot = StockLot.search([
                    ('product_id', '=', product.id),
                    ('name', '=ilike', lot_name_stripped),
                    ('company_id', '=', False),
                ], limit=1)
                if retry_lot:
                    return self._cache_lot(retry_lot)
                raise

        # Paso 3: No existe en ningún lado
        return False

    def find(self, product, lot_name):
        """
        Busca un lote por producto y nombre.
        Intenta: exact case-insensitive → código compacto (strip ceros a la izq).
        Retorna el lote o False.
        """
        if not product or not lot_name:
            return False
        lot_name = lot_name.strip()
        if not lot_name:
            return False
        lot_name_lower = lot_name.lower()

        if self._preloaded:
            product_lots = self._by_product.get(product.id, [])
            for name, lot in product_lots:
                if name.lower() == lot_name_lower:
                    return self._cache_lot(self._as_global_lot(lot))
            compact = self._compact(lot_name)
            if compact:
                for name, lot in product_lots:
                    if self._compact(name) == compact:
                        return self._cache_lot(self._as_global_lot(lot))
            return False

        # Sin preload: búsqueda directa (comportamiento anterior)
        existing = self._search_db_lot(product, lot_name, '=ilike')
        if existing:
            return existing
        compact = self._compact(lot_name)
        if compact and compact != lot_name:
            candidates = self._search_db_lot(product, compact, '=ilike')
            if candidates:
                return candidates
        return False

    def ensure(self, product, lot_name, expiration_date=False):
        """Devuelve el lote existente o lo crea (patrón get-or-create multiempresa).

        Búsqueda en tres capas:
        1. Caché en memoria (O(k), evita N+1 tras preload).
        2. BD robusta: busca global, convierte empresa-específico, o crea nuevo.
        3. Maneja race conditions con savepoint.
        """
        has_expiry = 'expiration_date' in self.env['stock.lot']._fields
        lot_name_stripped = (lot_name or '').strip()

        if not product or not lot_name_stripped:
            return False

        # Capa 1: Caché en memoria
        existing = self.find(product, lot_name_stripped)
        if existing:
            if expiration_date and has_expiry and not existing.expiration_date:
                existing.sudo().expiration_date = expiration_date
            return existing

        # Capa 2: Búsqueda robusta en BD (global, empresa-específico, o nuevo)
        db_lot = self._find_or_convert_to_global(product, lot_name_stripped)
        if db_lot:
            if expiration_date and has_expiry and not db_lot.expiration_date:
                db_lot.sudo().expiration_date = expiration_date
            return self._cache_lot(db_lot)

        # Capa 3: Crear nuevo lote global si no existe en ningún lado
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
            # Reintentar búsqueda robusta: pudo haber sido creado por otro proceso
            retry_lot = self._find_or_convert_to_global(product, lot_name_stripped)
            if retry_lot:
                return self._cache_lot(retry_lot)
            raise

        return self._cache_lot(new_lot)
