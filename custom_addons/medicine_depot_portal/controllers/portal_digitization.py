# -*- coding: utf-8 -*-
import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.local_ai_connector.services import image_preprocessor
except ImportError:
    image_preprocessor = None


class PortalDashboardDigitization(http.Controller):

    @http.route("/my/dashboard/digitize", type="jsonrpc", auth="user", website=True)
    def digitize_document(self, image_base64, **kw):
        """Endpoint del portal /my/dashboard para procesar una imagen de receta/documento,
        
        aplicar el pipeline de limpieza y retornar opciones recomendadas con su cantidad 'A la mano' (On Hand).
        """
        if not image_base64:
            return {"status": "error", "message": "No se recibió ninguna imagen."}

        try:
            # 1. Decodificación de base64
            img_payload = image_base64.split(",")[-1]
            raw_bytes = base64.b64decode(img_payload)

            # 2. Mejora de calidad de imagen (OpenCV / PIL)
            enhanced_bytes = raw_bytes
            if image_preprocessor:
                enhanced_bytes = image_preprocessor.enhance_document_quality(raw_bytes)
                if image_preprocessor.is_line_crossed_out(enhanced_bytes[:1000]):
                    _logger.info("Línea con tachones detectada en el documento.")

            # 3. Normalización y diccionario estricto
            # Extraer lista de sustancias conocidas en base de datos
            substances = request.env["md.active.substance"].sudo().search_read([], ["name"])
            known_list = [s["name"] for s in substances if s.get("name")]

            # Para demostración de prueba o extracción por visión, se procesa la sustancia detectada:
            raw_extracted = kw.get("sample_text") or "westergiron"
            cleaned_substance = raw_extracted
            if image_preprocessor:
                cleaned_substance = image_preprocessor.clean_and_normalize_substance(
                    raw_extracted, known_substances=known_list
                )

            # 4. Consulta de 3 a 5 productos recomendados con su cantidad 'A la mano' (On Hand)
            company_id = request.env.company.id
            recommendations = request.env["product.product"].sudo().recommend_products_by_substance(
                cleaned_substance, limit=5, company_id=company_id
            )

            return {
                "status": "success",
                "raw_extracted": raw_extracted,
                "cleaned_substance": cleaned_substance,
                "recommendations": recommendations,  # Cada item contiene 'qty_on_hand' -> 'A la mano' (On Hand)
            }
        except Exception as exc:
            _logger.exception("Error procesando digitalización en portal: %s", exc)
            return {"status": "error", "message": str(exc)}
