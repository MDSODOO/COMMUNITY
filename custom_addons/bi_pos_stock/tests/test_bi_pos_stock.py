# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase

class TestBiPosStock(TransactionCase):
    def setUp(self):
        super(TestBiPosStock, self).setUp()
        # Setup de datos de prueba
        self.pos_config = self.env['pos.config'].create({
            'name': 'Test POS Config',
            'session_sequence_id': self.env.ref('point_of_sale.sequence_pos_session').id,
        })

    def test_pos_custom_screen_entrypoint(self):
        """Test para el método pos_custom_screen_entrypoint"""
        # Arrange
        config_id = self.pos_config.id

        # Act
        response = request.get(f"/pos/ui/{config_id}/stock")

        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/pos/ui/{config_id}", response.headers['Location'])

    def test_pos_custom_screen_entrypoint_with_query_string(self):
        """Test para el método pos_custom_screen_entrypoint con query string"""
        # Arrange
        config_id = self.pos_config.id
        query_string = "test=value"

        # Act
        response = request.get(f"/pos/ui/{config_id}/stock?{query_string}")

        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/pos/ui/{config_id}?{query_string}", response.headers['Location'])

    def test_pos_custom_screen_entrypoint_with_multiple_paths(self):
        """Test para el método pos_custom_screen_entrypoint con múltiples rutas"""
        # Arrange
        config_id = self.pos_config.id

        paths = [
            f"/pos/ui/{config_id}/stock",
            f"/pos/ui/{config_id}/low-stock",
            f"/pos/ui/{config_id}/ecommerce-orders"
        ]

        for path in paths:
            # Act
            response = request.get(path)

            # Assert
            self.assertEqual(response.status_code, 302)
            self.assertIn(f"/pos/ui/{config_id}", response.headers['Location'])