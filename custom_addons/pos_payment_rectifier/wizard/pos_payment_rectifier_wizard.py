# -*- coding: utf-8 -*-
# Part of Medicine Depot. See LICENSE file for full copyright and licensing details.

"""
Rectifica el método de pago de una orden PoS ya cerrada (ej. capturado como
"Tarjeta de Débito" cuando en realidad el cliente pagó en Efectivo).

Por qué no se edita/borra ``pos.payment`` directamente (contexto real,
confirmado por introspección ORM en la BD de pruebas
medicinedepot-test-34521568):

  Al cerrar una sesión PoS, Odoo NO crea un ``account.payment`` por cada
  ``pos.payment``. Por cada método de pago usado en la sesión crea UN
  ``account.payment`` agregado (ej. "Combine los pagos con Tarjeta de
  Débito del ...") que:
    - Debita la cuenta puente del método (``pos.payment.method.
      outstanding_account_id``, ej. "102.01.98 Recibos abiertos").
    - Acredita la cuenta de clientes PoS (``destination_account_id``,
      ej. "105.01.02 National customers (PoS)"), conciliada 1:1 contra
      TODAS las órdenes de esa sesión+método, no solo una.

  Desconciliar y reconstruir ese agregado para corregir una sola orden
  afectaría a todas las demás órdenes del mismo lote, con riesgo real de
  romper una conciliación bancaria ya hecha contra el estado de cuenta.

Enfoque de este wizard (no destructivo):
  1. El historial de ``pos.payment`` de la orden queda intacto — nunca se
     reescribe lo que realmente pasó en caja.
  2. Se publica un asiento de reclasificación independiente que mueve el
     monto entre la cuenta puente del método erróneo y la cuenta real del
     método correcto (``journal.default_account_id`` para Efectivo). Este
     asiento no toca ni desconcilia el agregado de la sesión.
  3. Se registra todo en ``pos.payment.rectification.log`` (auditoría
     permanente, no transient).
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosPaymentRectifierWizard(models.TransientModel):
    _name = 'pos.payment.rectifier.wizard'
    _description = 'Rectificar Método de Pago de una Orden PoS'

    order_id = fields.Many2one(
        'pos.order', string='Orden PoS', required=True,
        default=lambda self: self.env.context.get('default_order_id'),
    )
    company_id = fields.Many2one(related='order_id.company_id', string='Compañía')
    currency_id = fields.Many2one(related='order_id.currency_id', string='Moneda')

    wrong_payment_id = fields.Many2one(
        'pos.payment', string='Pago a corregir', required=True,
        domain="[('pos_order_id', '=', order_id)]",
    )
    old_payment_method_id = fields.Many2one(
        related='wrong_payment_id.payment_method_id', string='Método original',
    )
    amount = fields.Monetary(related='wrong_payment_id.amount', string='Monto')

    new_payment_method_id = fields.Many2one(
        'pos.payment.method', string='Método correcto', required=True,
        domain="[('company_id', '=', company_id), ('id', '!=', old_payment_method_id)]",
    )
    journal_id = fields.Many2one(
        'account.journal', string='Diario del asiento de reclasificación', required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )
    reason = fields.Text(string='Motivo', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self.env['pos.order'].browse(res.get('order_id'))
        if order and 'journal_id' not in res:
            general_journal = self.env['account.journal'].search([
                ('type', '=', 'general'), ('company_id', '=', order.company_id.id),
            ], limit=1)
            res['journal_id'] = general_journal.id
        return res

    def _get_account_for_method(self, method):
        """Cuenta 'dinero' de un método de pago: puente (Tarjeta/Transferencia)
        o cuenta real de caja (Efectivo, vía el diario)."""
        account = method.outstanding_account_id or method.journal_id.default_account_id
        if not account:
            raise UserError(_(
                'El método de pago "%s" no tiene una cuenta puente '
                '(outstanding_account_id) ni una cuenta por defecto en su diario. '
                'Configúrala antes de rectificar.'
            ) % method.name)
        return account

    def _session_aggregate_already_bank_matched(self, order, method, account):
        """Detecta si el account.payment agregado de sesión+método ya fue
        emparejado contra una línea real de estado de cuenta bancario — en
        ese caso no bloqueamos (nuestro asiento es independiente), pero
        marcamos el log para que un contable revise la conciliación bancaria
        del lote de ese día."""
        aggregate = self.env['account.payment'].sudo().search([
            ('pos_session_id', '=', order.session_id.id),
            ('pos_payment_method_id', '=', method.id),
        ], limit=1)
        if not aggregate or not aggregate.move_id:
            return False
        bridge_lines = aggregate.move_id.line_ids.filtered(lambda l: l.account_id == account)
        return bool(bridge_lines.filtered('statement_line_id'))

    def action_confirm(self):
        self.ensure_one()
        order = self.order_id
        wrong_payment = self.wrong_payment_id
        old_method = self.old_payment_method_id
        new_method = self.new_payment_method_id

        if order.session_id.state != 'closed':
            raise UserError(_(
                'La sesión "%s" de esta orden sigue abierta. Corrige el método '
                'de pago directamente en la sesión de PoS en vez de usar este '
                'asistente — es más simple y no requiere ningún asiento contable.'
            ) % order.session_id.name)

        if new_method == old_method:
            raise UserError(_('El método correcto debe ser distinto al método original.'))

        if not self.reason or not self.reason.strip():
            raise UserError(_('El motivo es obligatorio para dejar el rastro de auditoría.'))

        source_account = self._get_account_for_method(old_method)
        dest_account = self._get_account_for_method(new_method)
        amount = wrong_payment.amount

        needs_review = self._session_aggregate_already_bank_matched(order, old_method, source_account)

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': _('Rectificación PoS %s: %s -> %s (%s)') % (
                order.name, old_method.name, new_method.name, self.reason.strip(),
            ),
            'line_ids': [
                (0, 0, {
                    'account_id': dest_account.id,
                    'debit': amount,
                    'credit': 0.0,
                    'name': _('Rectificación %s: entrada %s') % (order.name, new_method.name),
                }),
                (0, 0, {
                    'account_id': source_account.id,
                    'debit': 0.0,
                    'credit': amount,
                    'name': _('Rectificación %s: salida %s') % (order.name, old_method.name),
                }),
            ],
        })
        move.action_post()

        self.env['pos.payment.rectification.log'].sudo().create({
            'order_id': order.id,
            'old_payment_method_id': old_method.id,
            'new_payment_method_id': new_method.id,
            'amount': amount,
            'reason': self.reason.strip(),
            'reclass_move_id': move.id,
            'state': 'needs_review' if needs_review else 'done',
            'review_note': _(
                'La cuenta puente del método original ya tiene una línea conciliada '
                'contra un estado de cuenta bancario real para esta sesión. Revisa '
                'la conciliación bancaria del lote de "%s" del día — el monto de '
                'esta orden ya no corresponde a ese depósito.'
            ) % old_method.name if needs_review else False,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Asiento de rectificación'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }
