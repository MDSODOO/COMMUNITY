from odoo.tests.common import TransactionCase
from odoo import fields
from datetime import datetime, timedelta


class TestProductionLotMigration(TransactionCase):
    """Tests unitarios para la migración de Studio → Código puro en stock.lot"""

    @classmethod
    def setUpClass(cls):
        """Configuración inicial para todos los tests."""
        super().setUpClass()

        # Crear producto de prueba
        cls.product = cls.env['product.product'].create({
            'name': 'Producto Test - Lotes',
            'type': 'storable',
            'tracking': 'lot',
        })

        # Crear usuario de prueba
        cls.user_test = cls.env['res.users'].create({
            'name': 'Usuario Test Lotes',
            'login': 'test_lots@example.com',
            'password': 'password123',
            'email': 'test_lots@example.com',
        })

    def setUp(self):
        """Configuración antes de cada test."""
        super().setUp()
        self.ProductionLot = self.env['stock.lot']

    def _get_internal_location(self):
        location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', 'in', [self.env.company.id, False]),
        ], limit=1)
        if location:
            return location
        return self.env['stock.location'].create({
            'name': 'Ubicación Test',
            'usage': 'internal',
            'company_id': self.env.company.id,
        })

    def _create_allowed_company(self, name):
        company = self.env['res.company'].create({'name': name})
        self.env.user.write({'company_ids': [(4, company.id)]})
        return company

    def test_01_creation_with_custom_fields(self):
        """Test 1: Crear lote con campos personalizados"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-001',
            'product_id': self.product.id,
            'estado_lote': 'activo',
            'codigo_proveedor_externo': 'PROV-12345',
            'referencia_compra': 'OC-2026-0001',
        })

        self.assertIsNotNone(lot)
        self.assertEqual(lot.name, 'LOT-2026-001')
        self.assertEqual(lot.product_id.id, self.product.id)
        self.assertEqual(lot.estado_lote, 'activo')
        self.assertEqual(lot.codigo_proveedor_externo, 'PROV-12345')
        self.assertEqual(lot.referencia_compra, 'OC-2026-0001')

    def test_02_campo_qty_a_la_mano_computed(self):
        """Test 2: qty_a_la_mano se computa correctamente"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-002',
            'product_id': self.product.id,
        })

        # Crear ubicación test
        location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not location:
            location = self.env['stock.location'].create({
                'name': 'Ubicación Test',
                'usage': 'internal',
                'company_id': self.env.company.id,
            })

        # Crear quant en la ubicación
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': location.id,
            'lot_id': lot.id,
            'quantity': 100.0,
        })

        # Forzar recomputación y limpiar caché del recordset
        self.env.flush_all()
        lot.invalidate_recordset()

        # Verificar que qty_a_la_mano se calculó
        self.assertGreater(lot.qty_a_la_mano, 0)
        self.assertIn(lot.id, self.ProductionLot.search([
            ('qty_a_la_mano', '>', 0),
        ]).ids)

    def test_03_usuario_creacion_automatico(self):
        """Test 3: El campo usuario_creacion se asigna automáticamente"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-003',
            'product_id': self.product.id,
        })

        # Verificar que se asignó el usuario actual
        self.assertIsNotNone(lot.usuario_creacion)
        self.assertEqual(lot.usuario_creacion.id, self.env.user.id)

    def test_04_fecha_entrada_default(self):
        """Test 4: fecha_entrada tiene fecha default"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-004',
            'product_id': self.product.id,
        })

        # Verificar que tiene fecha de entrada
        self.assertIsNotNone(lot.fecha_entrada)
        # Debe estar cerca de ahora (dentro de 1 minuto)
        tiempo_diff = datetime.now() - lot.fecha_entrada.replace(tzinfo=None)
        self.assertLess(tiempo_diff.total_seconds(), 60)

    def test_05_validacion_fechas_vencimiento(self):
        """Test 5: Validar que fecha_vencimiento_estimado <= expiration_date"""
        fecha_hoy = fields.Date.today()
        fecha_futura = fecha_hoy + timedelta(days=30)
        fecha_mas_futura = fecha_hoy + timedelta(days=60)

        lot = self.ProductionLot.create({
            'name': 'LOT-2026-005',
            'product_id': self.product.id,
            'expiration_date': fecha_futura,
            'fecha_vencimiento_estimado': fecha_hoy,
        })

        # Esto debe cumplirse sin error
        self.assertEqual(lot.expiration_date, fecha_futura)
        self.assertEqual(lot.fecha_vencimiento_estimado, fecha_hoy)

        # Intentar asignar fecha estimada mayor que oficial debe fallar
        with self.assertRaises(Exception):
            lot.write({
                'fecha_vencimiento_estimado': fecha_mas_futura,
                'expiration_date': fecha_futura,
            })

    def test_06_estado_lote_valores_válidos(self):
        """Test 6: El estado del lote solo acepta valores válidos"""
        estados_válidos = ['activo', 'pausado', 'agotado', 'descontinuado']

        for estado in estados_válidos:
            lot = self.ProductionLot.create({
                'name': f'LOT-ESTADO-{estado}',
                'product_id': self.product.id,
                'estado_lote': estado,
            })
            self.assertEqual(lot.estado_lote, estado)

    def test_07_notas_calidad(self):
        """Test 7: Las notas de calidad se guardan correctamente"""
        notas = 'Lote inspeccionado, sin defectos visibles. Almacenado en área refrigerada.'
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-007',
            'product_id': self.product.id,
            'notas_calidad': notas,
        })

        self.assertEqual(lot.notas_calidad, notas)

    def test_08_referencias_externas(self):
        """Test 8: Códigos de proveedor y referencias de compra"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-008',
            'product_id': self.product.id,
            'codigo_proveedor_externo': 'EXT-99999',
            'referencia_compra': 'FACT-2026-5555',
        })

        self.assertEqual(lot.codigo_proveedor_externo, 'EXT-99999')
        self.assertEqual(lot.referencia_compra, 'FACT-2026-5555')

    def test_09_búsqueda_por_estado(self):
        """Test 9: Búsqueda de lotes por estado_lote"""
        # Crear varios lotes con diferentes estados
        for i, estado in enumerate(['activo', 'activo', 'agotado']):
            self.ProductionLot.create({
                'name': f'LOT-SEARCH-{i}',
                'product_id': self.product.id,
                'estado_lote': estado,
            })

        # Buscar lotes activos
        lotes_activos = self.ProductionLot.search([
            ('estado_lote', '=', 'activo')
        ])

        self.assertEqual(len(lotes_activos), 2)

        # Buscar lotes agotados
        lotes_agotados = self.ProductionLot.search([
            ('estado_lote', '=', 'agotado')
        ])

        self.assertEqual(len(lotes_agotados), 1)

    def test_10_busqueda_por_codigo_proveedor(self):
        """Test 10: Búsqueda de lotes por código de proveedor"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-010',
            'product_id': self.product.id,
            'codigo_proveedor_externo': 'SEARCHABLE-CODE',
        })

        resultado = self.ProductionLot.search([
            ('codigo_proveedor_externo', '=', 'SEARCHABLE-CODE')
        ])

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.id, lot.id)

    def test_11_auditoría_timestamps(self):
        """Test 11: Verificar que timestamps de auditoría se registran"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-011',
            'product_id': self.product.id,
        })

        # create_date debe estar poblado
        self.assertIsNotNone(lot.create_date)
        self.assertIsNotNone(lot.create_uid)

        # Modificar el lote
        lot.write({'estado_lote': 'pausado'})

        # write_date debe actualizarse
        self.assertIsNotNone(lot.write_date)
        self.assertIsNotNone(lot.write_uid)

    def test_12_permisos_lectura(self):
        """Test 12: Verificar que los permisos de lectura funcionan"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-012',
            'product_id': self.product.id,
        })

        # Usuario básico debe poder leer
        usuario_basico = self.env['res.users'].create({
            'name': 'Usuario Básico',
            'login': 'basic_user@example.com',
        })

        lot_leido = self.ProductionLot.with_user(usuario_basico).search([
            ('id', '=', lot.id)
        ])

        # Usuario interno básico tiene perm_read=1 en ir.model.access.csv — debe poder leer
        self.assertEqual(len(lot_leido), 1)
        self.assertEqual(lot_leido.id, lot.id)

    def test_13_compute_fecha_ultima_modificacion(self):
        """Test 13: fecha_ultima_modificacion refleja write_date del lote"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-013',
            'product_id': self.product.id,
        })

        # fecha_ultima_modificacion es related de write_date: deben coincidir
        self.assertEqual(lot.fecha_ultima_modificacion, lot.write_date)
        self.assertIsNotNone(lot.fecha_ultima_modificacion)

        # Después de un write, write_date se actualiza y el related también
        lot.write({'estado_lote': 'pausado'})
        lot.invalidate_recordset()
        self.assertEqual(lot.fecha_ultima_modificacion, lot.write_date)
        self.assertGreaterEqual(lot.fecha_ultima_modificacion, lot.create_date)

    def test_14_qty_a_la_mano_sin_quants(self):
        """Test 14: qty_a_la_mano debe ser 0 si no hay quants"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-014',
            'product_id': self.product.id,
        })

        # Sin quants, debe ser 0
        self.assertEqual(lot.qty_a_la_mano, 0)

    def test_15_búsqueda_lotes_vencidos(self):
        """Test 15: Búsqueda de lotes vencidos"""
        fecha_hoy = fields.Date.today()
        fecha_ayer = fecha_hoy - timedelta(days=1)
        fecha_mañana = fecha_hoy + timedelta(days=1)

        # Lote vencido
        lot_vencido = self.ProductionLot.create({
            'name': 'LOT-VENCIDO',
            'product_id': self.product.id,
            'expiration_date': fecha_ayer,
        })

        # Lote vigente
        lot_vigente = self.ProductionLot.create({
            'name': 'LOT-VIGENTE',
            'product_id': self.product.id,
            'expiration_date': fecha_mañana,
        })

        # Buscar vencidos
        lotes_vencidos = self.ProductionLot.search([
            ('expiration_date', '<', fecha_hoy)
        ])

        self.assertTrue(lot_vencido.id in lotes_vencidos.ids)
        self.assertFalse(lot_vigente.id in lotes_vencidos.ids)

    def test_16_active_default_true(self):
        """Test 16: Los lotes se crean con active=True por defecto"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-016',
            'product_id': self.product.id,
        })

        self.assertTrue(lot.active)

    def test_17_archivar_lote(self):
        """Test 17: Archivar un lote cambia active=False y lo oculta de búsquedas normales"""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-017',
            'product_id': self.product.id,
        })

        # Archivar
        lot.write({'active': False})
        lot.invalidate_recordset()

        self.assertFalse(lot.active)

        # La búsqueda normal no debe encontrar el lote archivado
        resultado = self.ProductionLot.search([('name', '=', 'LOT-2026-017')])
        self.assertEqual(len(resultado), 0)

        # Con active_test=False sí debe encontrarlo
        resultado_completo = self.ProductionLot.with_context(active_test=False).search([
            ('name', '=', 'LOT-2026-017')
        ])
        self.assertEqual(len(resultado_completo), 1)
        self.assertFalse(resultado_completo.active)

    def test_18_get_or_create_con_lote_archivado(self):
        """Test 18: get-or-create retorna lote archivado sin crear duplicado"""
        lot_original = self.ProductionLot.create({
            'name': 'LOT-2026-018',
            'product_id': self.product.id,
        })
        lot_original.write({'active': False})

        # Intentar crear un lote con los mismos datos debe retornar el archivado
        resultado = self.ProductionLot.create([{
            'name': 'LOT-2026-018',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        }])

        # Debe ser el mismo registro, no uno nuevo
        self.assertEqual(resultado.id, lot_original.id)

        # No debe haber duplicados en la base
        todos = self.ProductionLot.with_context(active_test=False).search([
            ('name', '=', 'LOT-2026-018'),
            ('product_id', '=', self.product.id),
        ])
        self.assertEqual(len(todos), 1)

    def test_19_creation_updates_a_la_mano(self):
        """Test 19: Crear lote con cantidad actualiza A la mano"""
        location = self._get_internal_location()

        lot = self.ProductionLot.create({
            'name': 'LOT-2026-019',
            'product_id': self.product.id,
            'cantidad_entrada_a_la_mano': 12.0,
            'ubicacion_destino_id': location.id,
        })

        quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('lot_id', '=', lot.id),
            ('location_id', '=', location.id),
        ], limit=1)
        self.env.flush_all()
        quant.invalidate_recordset()
        lot.invalidate_recordset()
        self.assertEqual(quant.quantity, 12.0)
        self.assertEqual(lot.qty_a_la_mano, 12.0)

    def test_20_wizard_updates_a_la_mano_notification(self):
        """Test 20: El wizard actualiza A la mano y devuelve notificación"""
        location = self._get_internal_location()
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-020',
            'product_id': self.product.id,
        })

        wizard = self.env['md.lot.a.la.mano.wizard'].create({
            'lot_id': lot.id,
            'cantidad_entrada_a_la_mano': 7.0,
            'ubicacion_destino_id': location.id,
        })
        action = wizard.action_apply_a_la_mano()

        quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('lot_id', '=', lot.id),
            ('location_id', '=', location.id),
        ], limit=1)
        self.env.flush_all()
        quant.invalidate_recordset()
        self.assertEqual(quant.quantity, 7.0)
        self.assertEqual(action['tag'], 'display_notification')
        self.assertEqual(
            action['params']['message'],
            'La cantidad A la mano ha sido actualizada correctamente '
            'para el lote LOT-2026-020',
        )

    def test_21_get_or_create_increments_a_la_mano(self):
        """Test 21: get-or-create incrementa A la mano"""
        location = self._get_internal_location()
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-021',
            'product_id': self.product.id,
            'cantidad_entrada_a_la_mano': 5.0,
            'ubicacion_destino_id': location.id,
        })

        same_lot = self.ProductionLot.create({
            'name': 'LOT-2026-021',
            'product_id': self.product.id,
            'cantidad_entrada_a_la_mano': 3.0,
            'ubicacion_destino_id': location.id,
        })

        quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id),
            ('lot_id', '=', lot.id),
            ('location_id', '=', location.id),
        ], limit=1)
        self.env.flush_all()
        quant.invalidate_recordset()
        self.assertEqual(same_lot.id, lot.id)
        self.assertEqual(quant.quantity, 8.0)

    def test_22_global_product_creates_global_lot_even_with_company(self):
        """Test 22: producto global crea lote global aunque llegue una compañía."""
        company = self._create_allowed_company('Compañía B Test Lotes 22')

        lot = self.ProductionLot.create({
            'name': 'LOT-2026-022',
            'product_id': self.product.id,
            'company_id': company.id,
        })

        self.assertFalse(lot.company_id)

    def test_23_company_product_creates_global_lot(self):
        """Test 23: producto de compañía también crea lote global."""
        company = self._create_allowed_company('Compañía B Test Lotes 23')
        product = self.env['product.product'].create({
            'name': 'Producto Test - Lotes Compañía',
            'type': 'storable',
            'tracking': 'lot',
            'company_id': company.id,
        })

        lot = self.ProductionLot.create({
            'name': 'LOT-2026-023',
            'product_id': product.id,
            'company_id': self.env.company.id,
        })

        self.assertFalse(lot.company_id)

    def test_24_global_lot_visible_from_other_company_context(self):
        """Test 24: lote global visible usando otra compañía activa."""
        company = self._create_allowed_company('Compañía B Test Lotes 24')
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-024',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })

        lot_from_other_company = self.ProductionLot.with_company(company).search([
            ('id', '=', lot.id),
        ])

        self.assertEqual(lot_from_other_company.id, lot.id)

    def test_25_create_multi_reuses_pending_global_lot(self):
        """Test 25: create multi reutiliza el lote global dentro del mismo lote."""
        lots = self.ProductionLot.create([
            {
                'name': 'LOT-2026-025',
                'product_id': self.product.id,
            },
            {
                'name': 'LOT-2026-025',
                'product_id': self.product.id,
            },
        ])

        stored_lots = self.ProductionLot.with_context(active_test=False).search([
            ('name', '=', 'LOT-2026-025'),
            ('product_id', '=', self.product.id),
        ])

        self.assertEqual(lots.ids[0], lots.ids[1])
        self.assertEqual(len(stored_lots), 1)
        self.assertFalse(stored_lots.company_id)

    def test_26_move_line_lot_name_uses_existing_global_lot(self):
        """Test 26: lot_name se resuelve contra el lote global existente."""
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-026',
            'product_id': self.product.id,
        })

        vals = self.env['stock.move.line']._md_assign_existing_global_lot_vals({
            'lot_name': 'LOT-2026-026',
            'product_id': self.product.id,
        })

        self.assertEqual(vals['lot_id'], lot.id)

    def test_27_company_id_default_and_write_remain_global(self):
        """Test 27: company_id no toma la compañía activa por defecto."""
        defaults = self.ProductionLot.default_get(['company_id'])
        lot = self.ProductionLot.create({
            'name': 'LOT-2026-027',
            'product_id': self.product.id,
        })
        company = self._create_allowed_company('Compañía B Test Lotes 27')
        lot.write({'company_id': company.id})

        self.assertFalse(defaults.get('company_id'))
        self.assertFalse(lot.company_id)
