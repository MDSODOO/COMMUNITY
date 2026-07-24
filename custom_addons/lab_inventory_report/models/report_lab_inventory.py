# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Laboratorios filtrados (regla de negocio inamovible)
_LAB_NAMES = ('SERRAL', 'PERRIGO - QUIFA', 'GELCAPS/PHARMACAPS', 'RAAM')

# Candidatos para el campo Many2one en product_template que apunta al modelo
# md.product.line (tabla md_product_line). Se detecta vía information_schema
# en lugar de asumirlo, por si en algún entorno el campo tuviera otro nombre.
# El nombre real confirmado en BD es 'product_line_id'.
_PRODUCT_LINE_COL_CANDIDATES = ['product_line_id']

# Mapeo de cada laboratorio de negocio (_LAB_NAMES) a los nombres reales que
# existen hoy en md_product_line. El modelo legado Studio `x_line` combinaba
# pares de laboratorios en un solo registro (p.ej. "PERRIGO - QUIFA",
# "GELCAPS/PHARMACAPS"), mientras que md_product_line los tiene separados en
# una jerarquía padre/hijo (PERRIGO -> QUIFA, GELCAPS -> PHARMACAPS), con los
# productos poblados únicamente en los hijos (QUIFA, PHARMACAPS) además de
# RAAM y SERRAL directos. Este mapeo preserva los 4 grupos de negocio
# originales sin tocar vistas/filtros que ya usan esos 4 valores exactos.
_LAB_GROUP_SOURCE_NAMES = {
    'SERRAL': ('SERRAL',),
    'RAAM': ('RAAM',),
    'PERRIGO - QUIFA': ('PERRIGO', 'QUIFA'),
    'GELCAPS/PHARMACAPS': ('GELCAPS', 'PHARMACAPS'),
}


class ReportLabInventory(models.Model):
    _name = 'report.lab.inventory'
    _description = 'Reporte: Laboratorios a la mano por sucursal'
    _auto = False
    _rec_name = 'product_id'
    _order = 'line_name, product_id'

    product_id = fields.Many2one(
        'product.product', string='Producto', readonly=True,
    )
    location_id = fields.Many2one(
        'stock.location', string='Sucursal', readonly=True,
    )
    qty_a_la_mano = fields.Float(
        string='A la mano', readonly=True, digits=(16, 2),
    )
    # Selection (no Char) para permitir filtros y agrupaciones nativas por
    # laboratorio en Odoo 19. Las claves coinciden con los nombres físicos
    # devueltos por la vista SQL (restringidos a _LAB_NAMES en el WHERE).
    line_name = fields.Selection(
        selection=[(name, name) for name in _LAB_NAMES],
        string='Línea / Laboratorio', readonly=True,
    )

    # ── helpers para detectar columnas dinámicas ──────────────────────────

    def _log_startup_info(self):
        """Log información de diagnóstico detallada al cargar el modelo.

        Ayuda a identificar rápidamente problemas de configuración:
        - Si md_product_line existe en la BD
        - Qué campo de product_template se usa para laboratorios
        - Si hay datos A la mano
        """
        _logger.info('ReportLabInventory: iniciando validaciones de dependencias...')

        # Verificar campo de laboratorio
        line_col = self._get_product_line_col()
        if line_col:
            _logger.info('ReportLabInventory: ✓ Detectado campo de laboratorio en product_template: %s', line_col)
        else:
            _logger.warning(
                'ReportLabInventory: ✗ NO se detectó campo de laboratorio en product_template. '
                'Candidatos buscados: %s. La vista estará vacía hasta que md_product_lines esté completamente configurado.',
                list(_PRODUCT_LINE_COL_CANDIDATES)
            )

        # Verificar tabla md_product_line
        product_line_exists = self._product_line_table_exists()
        if product_line_exists:
            _logger.info('ReportLabInventory: ✓ Tabla md_product_line existe en base de datos')
            # Contar registros en md_product_line
            try:
                self.env.cr.execute('SELECT COUNT(*) FROM md_product_line')
                count = self.env.cr.fetchone()[0]
                _logger.info('ReportLabInventory: ✓ Tabla md_product_line contiene %d registros', count)
                if count == 0:
                    _logger.warning(
                        'ReportLabInventory: ⚠️  Tabla md_product_line existe pero está vacía. '
                        'Agrega laboratorios antes de generar el reporte.'
                    )
            except Exception as e:
                _logger.error('ReportLabInventory: Error al contar registros md_product_line: %s', e)
        else:
            _logger.warning(
                'ReportLabInventory: ✗ Tabla md_product_line NO existe en base de datos. '
                'Asegúrate de que el módulo md_product_lines esté instalado.'
            )

    def _get_product_line_col(self):
        """Detecta qué columna de product_template apunta a md.product.line."""
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'product_template'
              AND column_name = ANY(%s)
            LIMIT 1
        """, (list(_PRODUCT_LINE_COL_CANDIDATES),))
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def _product_line_table_exists(self):
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'md_product_line' LIMIT 1
        """)
        return bool(self.env.cr.fetchone())

    # ── init: construye la vista SQL ──────────────────────────────────────

    def init(self):
        # Log diagnóstico antes de procesar
        self._log_startup_info()

        line_col = self._get_product_line_col()

        if not line_col or not self._product_line_table_exists():
            _logger.warning(
                'ReportLabInventory: creando vista vacía (fallback mode). '
                'Razón: %s. La vista se llenará cuando md_product_lines esté completamente configurado.',
                'md_product_line no existe' if not self._product_line_table_exists() else 'campo de laboratorio no detectado'
            )
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW report_lab_inventory AS
                SELECT
                    1::integer          AS id,
                    NULL::integer       AS product_id,
                    NULL::integer       AS location_id,
                    0.0::float8         AS qty_a_la_mano,
                    NULL::text          AS line_name
                WHERE FALSE
            """)
            _logger.info('ReportLabInventory: vista vacía creada exitosamente (fallback mode)')
            return

        # Construir vista SQL completa
        try:
            _logger.info(
                'ReportLabInventory: creando vista SQL completa usando campo product_line=%s y laboratorios=%s',
                line_col, list(_LAB_NAMES)
            )

            # Tabla de mapeo nombre-fuente -> laboratorio de negocio, pasada
            # como VALUES parametrizado (nada de interpolación de datos de
            # usuario, solo constantes del módulo).
            lab_map_rows = []
            lab_map_params = []
            for lab_name, source_names in _LAB_GROUP_SOURCE_NAMES.items():
                for source_name in source_names:
                    lab_map_rows.append('(%s, %s)')
                    lab_map_params.extend([source_name, lab_name])
            lab_map_values_sql = ', '.join(lab_map_rows)

            # Usamos identificadores seguros — el nombre de columna viene de
            # information_schema y está restringido a los candidatos conocidos.
            self.env.cr.execute(f"""
                CREATE OR REPLACE VIEW report_lab_inventory AS
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY lab_map.line_name, pp.id, sl.id
                    )::integer                  AS id,
                    pp.id                       AS product_id,
                    sl.id                       AS location_id,
                    SUM(sq.quantity)::float8    AS qty_a_la_mano,
                    lab_map.line_name           AS line_name
                FROM stock_quant sq
                JOIN stock_location sl
                    ON sl.id = sq.location_id
                JOIN product_product pp
                    ON pp.id = sq.product_id
                JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id
                JOIN md_product_line xl
                    ON xl.id = pt.{line_col}
                JOIN (VALUES {lab_map_values_sql}) AS lab_map(source_name, line_name)
                    ON lab_map.source_name = xl.name
                WHERE
                    sl.usage = 'internal'
                    AND sq.quantity > 0
                GROUP BY
                    lab_map.line_name, pp.id, sl.id
            """, tuple(lab_map_params))
            _logger.info('ReportLabInventory: vista SQL completa creada exitosamente')
        except Exception as e:
            _logger.error(
                'ReportLabInventory: ERROR al crear vista SQL: %s. '
                'Creando vista vacía como fallback.',
                str(e)
            )
            # Fallback a vista vacía si hay error SQL
            self.env.cr.execute("""
                CREATE OR REPLACE VIEW report_lab_inventory AS
                SELECT
                    1::integer          AS id,
                    NULL::integer       AS product_id,
                    NULL::integer       AS location_id,
                    0.0::float8         AS qty_a_la_mano,
                    NULL::text          AS line_name
                WHERE FALSE
            """)
            raise

    # ── cron mensual ──────────────────────────────────────────────────────

    @api.model
    def _cron_generate_monthly_report(self):
        """Acción planificada: se ejecuta el último día de cada mes.

        Base lista para la lógica de envío (correo / adjunto PDF o Excel).
        Registra información detallada en los logs para auditoría.
        """
        import datetime
        hoy = datetime.date.today()
        _logger.info(
            'ReportLabInventory: iniciando generación de concentrado mensual para %s', hoy
        )

        try:
            records = self.search([])
            _logger.info(
                'ReportLabInventory: ✓ Concentrado generado exitosamente. '
                '%d filas encontradas para los laboratorios %s.',
                len(records), list(_LAB_NAMES),
            )

            # ── Punto de extensión: agregar aquí la lógica de envío por correo
            # o generación de adjunto Excel/PDF.
            # Ejemplo:
            #   report_action = self.env.ref('lab_inventory_report.action_report_lab_pdf')
            #   pdf, _ = report_action._render_qweb_pdf(records.ids)
            #   ...enviar por mail...

            return True
        except Exception as e:
            _logger.error(
                'ReportLabInventory: ✗ ERROR generando concentrado mensual: %s',
                str(e), exc_info=True
            )
            return False


class ReportLabInventoryPDF(models.AbstractModel):
    _name = 'report.lab_inventory_report.report_lab_inventory_pdf'
    _description = 'QWeb PDF: Laboratorios A la mano'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['report.lab.inventory'].browse(docids)
        docs = docs.sorted(
            key=lambda record: (
                record.line_name or '',
                record.product_id.display_name or '',
                record.location_id.display_name or '',
            )
        )
        lab_names = []
        location_names = []

        for record in docs:
            if record.line_name and record.line_name not in lab_names:
                lab_names.append(record.line_name)
            if record.location_id and record.location_id.display_name not in location_names:
                location_names.append(record.location_id.display_name)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'report.lab.inventory',
            'docs': docs,
            'lab_company': self.env.company.sudo(),
            'lab_names': lab_names,
            'location_names': location_names,
            'report_generated_at': fields.Datetime.context_timestamp(
                self, fields.Datetime.now()
            ),
            'report_row_count': len(docs),
            'total_a_la_mano': sum(docs.mapped('qty_a_la_mano')),
        }
