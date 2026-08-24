# pos_payment_rectifier — v19.0.1.0.0

**Categoría**: Point of Sale | **Licencia**: LGPL-3

## Propósito

Permite a un Gerente rectificar el método de pago de una orden PoS **ya cerrada** cuando el cajero capturó por error, por ejemplo, "Tarjeta de Débito" en vez de "Efectivo".

## Por qué no es un simple "editar y guardar"

Al cerrar una sesión PoS, Odoo agrega todos los pagos de un mismo método en **un solo** `account.payment` por sesión+método (ej. "Combine los pagos con Tarjeta de Débito del ..."), conciliado 1:1 contra todas las órdenes de ese lote. Editar/borrar el `pos.payment` de una sola orden no actualiza ese agregado — y desarmarlo para reconstruirlo afecta a las demás órdenes del mismo lote y arriesga romper una conciliación bancaria real ya hecha.

## Enfoque

1. El `pos.payment` original **nunca se reescribe** — es el historial real de lo que pasó en caja.
2. Se publica un **asiento de reclasificación** independiente que mueve el monto entre la cuenta puente del método erróneo (`pos.payment.method.outstanding_account_id`) y la cuenta real del método correcto (`account.journal.default_account_id`, ej. la Caja de Efectivo). No toca ni desconcilia el agregado de la sesión.
3. Cada rectificación queda en `pos.payment.rectification.log` — modelo permanente (no transient), de solo lectura desde la UI, con motivo obligatorio.
4. Si la cuenta puente del método erróneo ya fue emparejada contra una línea real de estado de cuenta bancario para esa sesión, el log se marca `needs_review` para que un contable revise la conciliación bancaria del lote — el asiento igual se publica porque es independiente y no rompe nada.

## Modelos

- `pos.payment.rectification.log` — log de auditoría permanente.
- `pos.payment.rectifier.wizard` (transient) — formulario de rectificación.
- `pos.order` (extensión) — botón "Rectificar Método de Pago" (solo `state in done/invoiced/paid`) + smart button con el conteo de rectificaciones.

## Seguridad

Grupo `pos_payment_rectifier.group_pos_rectification_manager` (implica `point_of_sale.group_pos_manager` + `account.group_account_manager`) — es el único grupo con acceso al wizard y al log.

## Notas técnicas

- Nombres de campo confirmados por introspección ORM real contra `medicinedepot-test-34521568` (no supuestos): `pos.payment.account_move_id`, `pos.payment.method.outstanding_account_id`, `account.payment.pos_session_id`/`pos_payment_method_id`, `account.journal.default_account_id`.
- Ver diagnóstico completo en `docs/audits/2026-07-06_pos_payment_method_rectification.md`.
