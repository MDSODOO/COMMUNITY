from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


class FakeResponse:
    """Sustituto de requests.Response: ni un solo test sale a la red."""

    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


OK_PAYLOAD = {"ok": True, "result": {"message_id": 4242}}


@tagged("post_install", "-at_install", "md_telegram")
class TestTelegramQueue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "md_telegram.bot_token", "123456789:TEST-TOKEN"
        )
        cls.channel = cls.env["md.telegram.channel"].create(
            {"name": "Pruebas", "code": "default", "chat_id": "-1001234567890"}
        )
        cls.Message = cls.env["md.telegram.message"]

    # ------------------------------------------------------------------
    # Encolado
    # ------------------------------------------------------------------
    def test_enqueue_no_hace_red(self):
        """Encolar es sólo un INSERT: si tocara la red, el mock saltaría."""
        with patch("odoo.addons.md_telegram_notify.models.telegram_message.requests.post") as post:
            message = self.Message.enqueue("Hola", channel_code="default")
            post.assert_not_called()
        self.assertEqual(message.state, "pending")
        self.assertEqual(message.chat_id, "-1001234567890")

    def test_enqueue_sin_canal_no_revienta(self):
        """Un código inexistente sin canal 'default' no debe romper el negocio."""
        self.channel.unlink()
        message = self.Message.enqueue("Hola", channel_code="inexistente")
        self.assertFalse(message)

    def test_enqueue_respalda_en_default(self):
        message = self.Message.enqueue("Hola", channel_code="codigo_que_no_existe")
        self.assertEqual(message.channel_id, self.channel)

    def test_truncado_a_4096(self):
        message = self.Message.enqueue("x" * 5000, channel_code="default")
        self.assertLessEqual(len(message.body), 4096)
        self.assertTrue(message.body.endswith("[...truncado]"))

    def test_escape_html(self):
        escaped = self.Message.escape("Farmacia <Ácme> & Cía")
        self.assertNotIn("<Ácme>", escaped)
        self.assertIn("&lt;", escaped)

    # ------------------------------------------------------------------
    # Envío
    # ------------------------------------------------------------------
    def test_envio_ok(self):
        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            return_value=FakeResponse(200, OK_PAYLOAD),
        ) as post:
            message.write({"state": "sending"})
            message._send_now()
        self.assertEqual(message.state, "sent")
        self.assertEqual(message.telegram_message_id, "4242")
        self.assertEqual(message.attempts, 1)
        # El payload debe llevar chat_id y parse_mode
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["chat_id"], "-1001234567890")
        self.assertEqual(payload["parse_mode"], "HTML")

    def test_error_de_red_reintenta(self):
        import requests

        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            message.write({"state": "sending"})
            message._send_now()
        self.assertEqual(message.state, "pending", "un fallo de red debe reintentarse")
        self.assertEqual(message.attempts, 1)
        self.assertGreater(message.next_attempt, message.create_date)

    def test_error_permanente_no_reintenta(self):
        """403 = bot expulsado del grupo. Reintentar 5 veces no lo arregla."""
        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            return_value=FakeResponse(403, {"ok": False, "description": "bot was kicked"}),
        ):
            message.write({"state": "sending"})
            message._send_now()
        self.assertEqual(message.state, "failed")
        self.assertEqual(message.attempts, 1)
        self.assertIn("kicked", message.error_message)

    def test_429_respeta_retry_after(self):
        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            return_value=FakeResponse(
                429, {"ok": False, "description": "Too Many Requests", "parameters": {"retry_after": 90}}
            ),
        ):
            message.write({"state": "sending"})
            message._send_now()
        self.assertEqual(message.state, "pending")
        delay = (message.next_attempt - message.create_date).total_seconds()
        self.assertGreaterEqual(delay, 85, "debe esperar el retry_after que pide Telegram")

    def test_agota_intentos(self):
        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            return_value=FakeResponse(500, {"ok": False, "description": "server error"}),
        ):
            for _i in range(5):
                message.write({"state": "sending", "next_attempt": message.create_date})
                message._send_now()
        self.assertEqual(message.state, "failed")
        self.assertEqual(message.attempts, 5)

    # ------------------------------------------------------------------
    # Casos propios de un GRUPO
    # ------------------------------------------------------------------
    def test_migracion_a_supergrupo_se_autocorrige(self):
        """El fallo más silencioso: el grupo pasa a supergrupo y cambia el ID."""
        message = self.Message.enqueue("Hola", channel_code="default")
        otro = self.Message.enqueue("Pendiente del mismo grupo", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            return_value=FakeResponse(
                400,
                {
                    "ok": False,
                    "description": "Bad Request: group chat was upgraded to a supergroup chat",
                    "parameters": {"migrate_to_chat_id": -1009876543210},
                },
            ),
        ):
            message.write({"state": "sending"})
            message._send_now()

        self.assertEqual(self.channel.chat_id, "-1009876543210", "el canal debe adoptar el ID nuevo")
        self.assertEqual(message.state, "pending", "debe reintentarse, no darse por perdido")
        self.assertEqual(message.chat_id, "-1009876543210")
        self.assertEqual(otro.chat_id, "-1009876543210", "los demás pendientes migran también")

    def test_bot_expulsado_archiva_el_canal(self):
        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            return_value=FakeResponse(
                403, {"ok": False, "description": "Forbidden: bot was kicked from the group chat"}
            ),
        ):
            message.write({"state": "sending"})
            message._send_now()
        self.assertEqual(message.state, "failed")
        self.assertFalse(self.channel.active, "el canal debe archivarse para que se vea el problema")

    def test_tope_por_chat_en_cada_pasada(self):
        """20 msg/min por grupo es el límite de Telegram: no lo provocamos."""
        for i in range(25):
            self.Message.enqueue("Mensaje %s" % i, channel_code="default")
        # _select_batch_ids en vez de _claim_batch: este último commitea, y
        # dentro de un test el commit está vetado.
        ids = self.Message._select_batch_ids()
        self.assertEqual(len(ids), 15, "el lote debe respetar MAX_PER_CHAT_PER_RUN")
        self.assertEqual(
            self.Message.search_count([("state", "=", "pending")]), 25,
            "el resto sigue en cola para la pasada siguiente",
        )

    def test_thread_id_va_en_el_payload(self):
        """Grupos con Temas activados: el mensaje debe caer en su tema."""
        self.channel.message_thread_id = "42"
        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            return_value=FakeResponse(200, OK_PAYLOAD),
        ) as post:
            message.write({"state": "sending"})
            message._send_now()
        self.assertEqual(post.call_args.kwargs["json"]["message_thread_id"], "42")

    def test_sin_token_falla_sin_red(self):
        self.env["ir.config_parameter"].sudo().set_param("md_telegram.bot_token", "")
        message = self.Message.enqueue("Hola", channel_code="default")
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post"
        ) as post:
            message.write({"state": "sending"})
            message._send_now()
            post.assert_not_called()
        self.assertEqual(message.state, "failed")


@tagged("post_install", "-at_install", "md_telegram")
class TestPurchaseTrigger(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["md.telegram.channel"].create(
            {"name": "Compras", "code": "compras", "chat_id": "-1009999999999"}
        )
        cls.env["ir.config_parameter"].sudo().set_param("md_telegram.purchase_threshold", "50000")
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor <Test> & Cía"})
        cls.product = cls.env["product.product"].create(
            {"name": "Producto de prueba", "type": "consu", "purchase_ok": True}
        )

    def _make_po(self, price):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (0, 0, {
                        "product_id": self.product.id,
                        "product_qty": 1,
                        "price_unit": price,
                        "name": self.product.name,
                    })
                ],
            }
        )

    def test_sobre_umbral_encola(self):
        order = self._make_po(80000)
        order.button_confirm()
        message = self.env["md.telegram.message"].search(
            [("res_model", "=", "purchase.order"), ("res_id", "=", order.id)]
        )
        self.assertEqual(len(message), 1)
        self.assertEqual(message.channel_id.code, "compras")
        self.assertIn(order.name, message.body)
        # El nombre del proveedor lleva '<' y '&': debe ir escapado o Telegram
        # devolvería 400 al parsear el HTML.
        self.assertIn("&lt;Test&gt;", message.body)

    def test_bajo_umbral_no_encola(self):
        order = self._make_po(100)
        order.button_confirm()
        message = self.env["md.telegram.message"].search(
            [("res_model", "=", "purchase.order"), ("res_id", "=", order.id)]
        )
        self.assertFalse(message)

    def test_umbral_cero_desactiva(self):
        self.env["ir.config_parameter"].sudo().set_param("md_telegram.purchase_threshold", "0")
        order = self._make_po(999999)
        order.button_confirm()
        message = self.env["md.telegram.message"].search(
            [("res_model", "=", "purchase.order"), ("res_id", "=", order.id)]
        )
        self.assertFalse(message)

    def test_confirmacion_no_depende_de_telegram(self):
        """Aunque el envío estalle, la orden queda confirmada."""
        order = self._make_po(80000)
        with patch(
            "odoo.addons.md_telegram_notify.models.telegram_message.requests.post",
            side_effect=Exception("Telegram caído"),
        ):
            order.button_confirm()
        self.assertEqual(order.state, "purchase")
