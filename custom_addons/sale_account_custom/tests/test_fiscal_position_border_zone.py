# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase


class TestFiscalPositionBorderZone(TransactionCase):
    """Tests para la anulación de posición fiscal fronteriza cuando la sucursal emisora no es fronteriza."""

    def setUp(self):
        super(TestFiscalPositionBorderZone, self).setUp()
        self.AccountFiscalPosition = self.env['account.fiscal.position']

        self.mx_country = self.env['res.country'].search([('code', '=', 'MX')])
        if not self.mx_country:
            self.mx_country = self.env['res.country'].create({
                'name': 'Mexico',
                'code': 'MX',
            })

        self.company_merida = self.env['res.company'].search([('zip', '=', '97070')])
        if not self.company_merida:
            self.company_merida = self.env['res.company'].create({
                'name': 'Sucursal Mérida',
                'country_id': self.mx_country.id,
                'zip': '97070',
                'street': 'Calle Principal',
                'city': 'Mérida',
                'state_id': self.env['res.country.state'].search([('code', '=', 'MX-YUC')]).id or False,
            })

        self.company_chetumal = self.env['res.company'].search([('zip', '=', '77000')])
        if not self.company_chetumal:
            self.company_chetumal = self.env['res.company'].create({
                'name': 'Sucursal Chetumal',
                'country_id': self.mx_country.id,
                'zip': '77000',
                'street': 'Avenida Fronteriza',
                'city': 'Chetumal',
                'state_id': self.env['res.country.state'].search([('code', '=', 'MX-QRO')]).id or False,
            })

        self.partner_chetumal = self.env['res.partner'].search([('zip', '=', '77000')])
        if not self.partner_chetumal:
            self.partner_chetumal = self.env['res.partner'].create({
                'name': 'Cliente Chetumal',
                'country_id': self.mx_country.id,
                'zip': '77000',
                'street': 'Calle Cliente',
                'city': 'Chetumal',
            })

        self.fp_border_8pct = self.env['account.fiscal.position'].search(
            [('name', 'ilike', 'frontera')]
        )
        if not self.fp_border_8pct:
            self.fp_border_8pct = self.AccountFiscalPosition.create({
                'name': 'Franja Fronteriza IVA 8%',
                'company_id': self.company_chetumal.id,
                'zip_from': '77000',
                'zip_to': '77999',
            })

    def test_border_zone_fiscal_position_cancelled_when_company_not_border(self):
        """Caso 1: Compañía emisora no fronteriza (Mérida 97070) + cliente fronterizo (Chetumal 77000).

        Esperado: La posición fiscal fronteriza se debe anular y devolver None (impuestos nacionales).
        """
        with self.env.company_context({'company_id': self.company_merida.id}):
            result = self.AccountFiscalPosition._get_fiscal_position(
                partner=self.partner_chetumal,
                delivery=self.partner_chetumal
            )

        self.assertFalse(
            result,
            "Se esperaba que la posición fiscal fronteriza se anulara cuando la sucursal emisora "
            "no está en zona fronteriza, pero se devolvió: %s" % result.name if result else None
        )

    def test_border_zone_fiscal_position_preserved_when_company_border(self):
        """Caso 2: Compañía emisora fronteriza (Chetumal 77000) + cliente fronterizo (Chetumal 77000).

        Esperado: La posición fiscal fronteriza se debe preservar (sin cambios respecto a comportamiento estándar).
        """
        with self.env.company_context({'company_id': self.company_chetumal.id}):
            result = self.AccountFiscalPosition._get_fiscal_position(
                partner=self.partner_chetumal,
                delivery=self.partner_chetumal
            )

        self.assertEqual(
            result.id,
            self.fp_border_8pct.id,
            "Se esperaba que la posición fiscal fronteriza se preservara cuando la sucursal emisora "
            "sí está en zona fronteriza, pero se devolvió: %s" % (result.name if result else "None")
        )

    def test_fiscal_position_no_geo_constraint_passthrough(self):
        """Caso 3: Posición fiscal sin restricción geográfica (zip_from/zip_to vacíos).

        Esperado: Se debe devolver la posición sin cambios (passthrough), no es una posición fronteriza.
        """
        fp_national = self.env['account.fiscal.position'].create({
            'name': 'Posición Nacional Estándar',
            'company_id': self.company_merida.id,
        })

        with self.env.company_context({'company_id': self.company_merida.id}):
            result = self.AccountFiscalPosition._get_fiscal_position(
                partner=self.partner_chetumal,
                delivery=self.partner_chetumal
            )

        self.assertTrue(
            result,
            "Se esperaba que la posición sin restricción geográfica se devolviera sin cambios."
        )
