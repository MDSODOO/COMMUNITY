# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import tagged, TransactionCase

from ..services import ollama_client
from ..services.inventory_nl_resolver import resolve_inventory_query

# Tag obligatorio: sin 'post_install' el test corre antes de que ciertos
# datos base terminen de cargar y falla de formas dificiles de diagnosticar
# (leccion aprendida en md_lots_management este mismo proyecto).
@tagged('post_install', '-at_install')
class TestInventoryNlResolver(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'PARACETAMOL 500MG C/20 TAB (TEST)',
            'barcode': 'TEST-PARACETAMOL-500',
            'type': 'consu',
            'is_storable': True,
        })
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.env['stock.quant']._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 42.0,
        )

    def _mock_response(self, producto_mencionado, aclaracion_necesaria=False):
        return {
            'producto_mencionado': producto_mencionado,
            'aclaracion_necesaria': aclaracion_necesaria,
        }

    def test_pregunta_resuelta_devuelve_a_la_mano_real(self):
        with patch.object(ollama_client, 'generate_structured',
                           return_value=self._mock_response('PARACETAMOL 500MG C/20 TAB (TEST)')):
            result = resolve_inventory_query(self.env, 'cuanto paracetamol hay a la mano?')

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['product_id'], self.product.id)
        self.assertEqual(result['on_hand'], 42.0)
        self.assertIn('A la mano', result['message'])
        # La regla de terminologia tambien aplica al resultado final que ve
        # el usuario, no solo al prompt.
        for termino_prohibido in ('Disponible', 'disponible', 'Stock', 'stock', 'Existencias', 'existencias'):
            self.assertNotIn(termino_prohibido, result['message'])

    def test_pregunta_ambigua_pide_aclaracion(self):
        with patch.object(ollama_client, 'generate_structured',
                           return_value=self._mock_response(None, aclaracion_necesaria=True)):
            result = resolve_inventory_query(self.env, 'hay medicinas?')

        self.assertEqual(result['status'], 'clarify')
        self.assertIsNone(result['product_id'])

    def test_producto_no_encontrado(self):
        with patch.object(ollama_client, 'generate_structured',
                           return_value=self._mock_response('PRODUCTO-QUE-NO-EXISTE-XYZ')):
            result = resolve_inventory_query(self.env, 'cuanto hay de producto-que-no-existe-xyz?')

        self.assertEqual(result['status'], 'not_found')

    def test_ollama_no_responde_no_rompe_devuelve_error_controlado(self):
        with patch.object(ollama_client, 'generate_structured',
                           side_effect=ollama_client.OllamaError('timeout simulado')):
            result = resolve_inventory_query(self.env, 'cuanto paracetamol hay?')

        self.assertEqual(result['status'], 'error')
        self.assertIn('error', result)

    def test_multiples_coincidencias_pide_aclaracion(self):
        self.env['product.product'].create({
            'name': 'PARACETAMOL 500MG C/20 TAB (TEST) VARIANTE',
            'type': 'consu',
            'is_storable': True,
        })
        with patch.object(ollama_client, 'generate_structured',
                           return_value=self._mock_response('PARACETAMOL 500MG C/20 TAB (TEST)')):
            result = resolve_inventory_query(self.env, 'cuanto paracetamol hay?')

        self.assertEqual(result['status'], 'clarify')
