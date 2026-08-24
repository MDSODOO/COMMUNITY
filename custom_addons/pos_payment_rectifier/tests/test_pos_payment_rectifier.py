# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPosPaymentRectifier(TransactionCase):
    """
    Fixture mínima: no levanta un pos.config/sesión reales de punta a punta
    (evita el overhead de un flujo PoS completo). Construye directamente los
    registros pos.session/pos.order/pos.payment con los campos que el
    wizard efectivamente lee, y fuerza session.state='closed' vía sudo,
    igual que haría una sesión cerrada de verdad.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.card_account = cls.env['account.account'].create({
            'name': 'Recibos abiertos (test)',
            'code': 'TEST.102.98',
            'account_type': 'asset_current',
        })
        cls.cash_account = cls.env['account.account'].create({
            'name': 'Caja (test)',
            'code': 'TEST.101.01',
            'account_type': 'asset_cash',
        })
        cls.misc_journal = cls.env['account.journal'].create({
            'name': 'Miscelánea (test)',
            'code': 'MISCT',
            'type': 'general',
        })
        cls.cash_journal = cls.env['account.journal'].create({
            'name': 'Caja PoS (test)',
            'code': 'CJT',
            'type': 'cash',
            'default_account_id': cls.cash_account.id,
        })
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Banco Tarjeta (test)',
            'code': 'BNKT',
            'type': 'bank',
        })

        cls.card_method = cls.env['pos.payment.method'].create({
            'name': 'Tarjeta de Débito (test)',
            'is_cash_count': False,
            'journal_id': cls.bank_journal.id,
            'outstanding_account_id': cls.card_account.id,
        })
        cls.cash_method = cls.env['pos.payment.method'].create({
            'name': 'Efectivo (test)',
            'is_cash_count': True,
            'journal_id': cls.cash_journal.id,
        })

        cls.pos_config = cls.env['pos.config'].create({
            'name': 'PoS Rectifier Test',
            'payment_method_ids': [(6, 0, [cls.card_method.id, cls.cash_method.id])],
        })
        cls.session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        # Simula una sesión ya cerrada — no ejecutamos el flujo completo de
        # cierre (que generaría los account.payment agregados reales).
        cls.session.sudo().write({'state': 'closed'})

        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Rectifier Test'})
        cls.order = cls.env['pos.order'].create({
            'session_id': cls.session.id,
            'partner_id': cls.partner.id,
            'amount_total': 100.0,
            'amount_tax': 0.0,
            'amount_paid': 100.0,
            'amount_return': 0.0,
            'lines': [],
        })
        cls.payment = cls.env['pos.payment'].create({
            'pos_order_id': cls.order.id,
            'payment_method_id': cls.card_method.id,
            'amount': 100.0,
            'session_id': cls.session.id,
        })

    def _make_wizard(self, **overrides):
        vals = {
            'order_id': self.order.id,
            'wrong_payment_id': self.payment.id,
            'new_payment_method_id': self.cash_method.id,
            'journal_id': self.misc_journal.id,
            'reason': 'Cajero capturó Tarjeta por error, cliente pagó Efectivo (test).',
        }
        vals.update(overrides)
        return self.env['pos.payment.rectifier.wizard'].create(vals)

    def test_get_account_for_method_uses_outstanding_account(self):
        wizard = self._make_wizard()
        self.assertEqual(wizard._get_account_for_method(self.card_method), self.card_account)

    def test_get_account_for_method_falls_back_to_journal_default(self):
        wizard = self._make_wizard()
        self.assertEqual(wizard._get_account_for_method(self.cash_method), self.cash_account)

    def test_get_account_for_method_raises_when_unconfigured(self):
        broken_journal = self.env['account.journal'].create({
            'name': 'Sin cuenta (test)', 'code': 'NOACC', 'type': 'cash',
        })
        broken_method = self.env['pos.payment.method'].create({
            'name': 'Método sin cuenta (test)', 'is_cash_count': True, 'journal_id': broken_journal.id,
        })
        wizard = self._make_wizard()
        with self.assertRaises(UserError):
            wizard._get_account_for_method(broken_method)

    def test_confirm_blocks_when_session_still_open(self):
        self.session.sudo().write({'state': 'opened'})
        wizard = self._make_wizard()
        with self.assertRaises(UserError):
            wizard.action_confirm()
        self.session.sudo().write({'state': 'closed'})

    def test_confirm_blocks_same_method(self):
        wizard = self._make_wizard(new_payment_method_id=self.card_method.id)
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_confirm_blocks_empty_reason(self):
        wizard = self._make_wizard(reason='   ')
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_confirm_posts_reclass_move_and_log(self):
        wizard = self._make_wizard()
        wizard.action_confirm()

        log = self.env['pos.payment.rectification.log'].search([('order_id', '=', self.order.id)])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.state, 'done')
        self.assertEqual(log.amount, 100.0)
        self.assertEqual(log.old_payment_method_id, self.card_method)
        self.assertEqual(log.new_payment_method_id, self.cash_method)

        move = log.reclass_move_id
        self.assertEqual(move.state, 'posted')
        debit_line = move.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = move.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, self.cash_account)
        self.assertEqual(credit_line.account_id, self.card_account)
        self.assertEqual(debit_line.debit, 100.0)
        self.assertEqual(credit_line.credit, 100.0)

        # El pos.payment original NUNCA se reescribe.
        self.assertEqual(self.payment.payment_method_id, self.card_method)
        self.assertEqual(self.payment.amount, 100.0)
