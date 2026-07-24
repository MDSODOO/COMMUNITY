# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Desvincula los reportes nativos de pos.session del menú de impresión.

    Después de instalar o actualizar este módulo, cualquier ir.actions.report
    que esté ligado a pos.session (excepto el nuestro) pierde su binding, de
    modo que "Cierre de Caja" es la única opción disponible para los usuarios.
    """
    our_ref = env.ref('bi_pos_stock.action_report_corte_z', raise_if_not_found=False)
    our_id = our_ref.id if our_ref else False

    native_reports = env['ir.actions.report'].search([
        ('model', '=', 'pos.session'),
        ('binding_model_id.model', '=', 'pos.session'),
        ('binding_type', '=', 'report'),
    ])

    unbound = []
    for report in native_reports:
        if our_id and report.id == our_id:
            continue
        report.binding_model_id = False
        unbound.append(report.name)

    if unbound:
        _logger.info(
            'bi_pos_stock: reporte(s) nativos desvinculados de pos.session: %s',
            ', '.join(unbound),
        )
