# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from ..services import prompt_templates
from ..services.inventory_nl_resolver import resolve_inventory_query


class LocalAiConnectorController(http.Controller):

    @http.route(
        '/ai/inventory_query',
        type='jsonrpc',
        auth='user',
        methods=['POST'],
    )
    def inventory_query(self, question, **kwargs):
        """Consulta de inventario en lenguaje natural, solo para staff
        autenticado (auth='user') -- no es un endpoint publico. El modelo de
        IA solo identifica el producto mencionado; la cantidad 'A la mano'
        (On Hand) la calcula Odoo de forma determinista, nunca el modelo.
        """
        question = (question or '').strip()
        if not question:
            return {'status': 'error', 'message': 'Escribe una pregunta.'}

        result = resolve_inventory_query(request.env, question)

        request.env['local.ai.query.log'].sudo().log_query(
            user_id=request.env.user.id,
            question=question,
            prompt_version=prompt_templates.INVENTORY_QUERY_VERSION,
            result=result,
        )

        return {
            'status': result['status'],
            'message': result['message'],
        }
