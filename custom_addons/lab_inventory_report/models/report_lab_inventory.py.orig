# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Laboratorios filtrados (regla de negocio inamovible)
_LAB_NAMES = ('SERRAL', 'PERRIGO - QUIFA', 'GELCAPS/PHARMACAPS', 'RAAM')

# Candidatos para el campo Many2one que apunta al modelo Studio x_line
_X_LINE_COL_CANDIDATES = [
    'x_line_id',
    'x_studio_line_id',
    'x_studio_linea_id',
    'x_studio_lnea_id',
]

# Candidatos para la columna "name" dentro de la tabla x_line
_X_LINE_NAME_COL_CANDIDATES = ['name', 'x_name', 'x_studio_name']


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
        - Si x_line existe en la BD
        - Qué campo de product_template se usa para laboratorios
        - Si hay datos A la mano
        """
        _logger.info('ReportLabInventory: iniciando validaciones de dependencias...')
        
        # Verificar campo de laboratorio
        line_col = self._get_x_line_product_col()
        if line_col:
            _logger.info('ReportLabInventory: ✓ Detectado campo de laboratorio en product_template: %s', line_col)
        else:
            _logger.warning(
                'ReportLabInventory: ✗ NO se detectó campo de laboratorio en product_template. '
                'Candidatos buscados: %s. La vista estará vacía hasta que Studio cree este campo.',
                list(_X_LINE_COL_CANDIDATES)
            )
        
        # Verificar tabla x_line
        x_line_exists = self._x_line_table_exists()
        if x_line_exists:
            _logger.info('ReportLabInventory: ✓ Tabla x_line existe en base de datos')
            # Contar registros en x_line
            try:
                self.env.cr.execute('SELECT COUNT(*) FROM x_line')
                count = self.env.cr.fetchone()[0]
                _logger.info('ReportLabInventory: ✓ Tabla x_line contiene %d registros', count)
                if count == 0:
                    _logger.warning(
                        'ReportLabInventory: ⚠️  Tabla x_line existe pero está vacía. '
                        'Agrega laboratorios antes de generar el reporte.'
                    )
            except Exception as e:
                _logger.error('ReportLabInventory: Error al contar registros x_line: %s', e)
        else:
            _logger.warning(
                'ReportLabInventory: ✗ Tabla x_line NO existe en base de datos. '
                'Asegúrate de que el módulo Studio esté instalado y activado.'
            )

    def _get_x_line_product_col(self):
        """Detecta qué columna de product_template apunta al modelo x_line."""
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'product_template'
              AND column_name = ANY(%s)
            LIMIT 1
        """, (list(_X_LINE_COL_CANDIDATES),))
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def _get_x_line_name_col(self):
        """Detecta la columna que almacena el nombre dentro de la tabla x_line."""
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'x_line'
              AND column_name = ANY(%s)
            ORDER BY array_position(%s, column_name)
            LIMIT 1
        """, (list(_X_LINE_NAME_COL_CANDIDATES), list(_X_LINE_NAME_COL_CANDIDATES)))
        row = self.env.cr.fetchone()
        return row[0] if row else 'name'

    def _x_line_table_exists(self):
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'x_line' LIMIT 1
        """)
        return bool(self.env.cr.fetchone())

    # ── init: construye la vista SQL ──────────────────────────────────────

    def init(self):
        # Log diagnóstico antes de procesar
        self._log_startup_info()
        
        line_col = self._get_x_line_product_col()

        if not line_col or not self._x_line_table_exists():
            _logger.warning(
                'ReportLabInventory: creando vista vacía (fallback mode). '
                'Razón: %s. La vista se llenará cuando Studio esté completamente configurado.',
                'x_line no existe' if not self._x_line_table_exists() else 'campo de laboratorio no detectado'
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

        name_col = self._get_x_line_name_col()

        # Construir vista SQL completa
        try:
            _logger.info(
                'ReportLabInventory: creando vista SQL completa usando campo x_line=%s y laboratorios=%s',
                line_col, list(_LAB_NAMES)
            )
            # Usamos identificadores seguros — los nombres de columna vienen de
            # information_schema y están restringidos a los candidatos conocidos.
            self.env.cr.execute(f"""
                CREATE OR REPLACE VIEW report_lab_inventory AS
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY xl.{name_col}, pp.id, sl.id
                    )::integer                  AS id,
                    pp.id                       AS product_id,
                    sl.id                       AS location_id,
                    SUM(sq.quantity)            AS qty_a_la_mano,
                    xl.{name_col}              AS line_name
                FROM stock_quant sq
                JOIN stock_location sl
                    ON sl.id = sq.location_id
                JOIN product_product pp
                    ON pp.id = sq.product_id
                JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id
                JOIN x_line xl
                    ON xl.id = pt.{line_col}
                WHERE
                    xl.{name_col} = ANY(%s)
                    AND sl.usage = 'internal'
                    AND sq.quantity > 0
                GROUP BY
                    xl.{name_col}, pp.id, sl.id
            """, (list(_LAB_NAMES),))
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
