"""Odoo Shell helper para auditar y limpiar lotes globales duplicados.

Uso desde la raíz del proyecto:
    odoo-bin shell -d DB -c odoo.conf
    exec(open('md_lots_management/scripts/audit_merge_global_lots.py').read())

Para aplicar los cambios seguros detectados:
    APPLY_DUPLICATE_LOT_CLEANUP = True
    exec(open('md_lots_management/scripts/audit_merge_global_lots.py').read())
"""

from collections import defaultdict


apply_cleanup = bool(globals().get('APPLY_DUPLICATE_LOT_CLEANUP', False))
Lot = env['stock.lot'].sudo().with_context(active_test=False)
MoveLine = env['stock.move.line'].sudo().with_context(active_test=False)
Quant = env['stock.quant'].sudo().with_context(active_test=False)

lots = Lot.search([], order='product_id, name, company_id, create_date, id')
groups = defaultdict(lambda: Lot.browse())
for lot in lots:
    if lot.name and lot.product_id:
        key = (lot.product_id.id, lot.name.strip())
        groups[key] = groups[key] | lot

report = {
    'apply': apply_cleanup,
    'groups_found': 0,
    'keepers_globalized': [],
    'archived_lots': [],
    'skipped_lots': [],
}


def _safe_write_global(lot):
    if not apply_cleanup:
        return True, False
    try:
        with env.cr.savepoint():
            lot.write({'company_id': False})
        return True, False
    except Exception as error:
        return False, str(error)


def _safe_archive(lot):
    if not apply_cleanup:
        return True, False
    try:
        with env.cr.savepoint():
            lot.write({'active': False})
        return True, False
    except Exception as error:
        return False, str(error)


def _lot_ref_counts(lot):
    return {
        'move_lines': MoveLine.search_count([('lot_id', '=', lot.id)]),
        'quants': Quant.search_count([('lot_id', '=', lot.id)]),
    }


for (product_id, name), duplicate_lots in groups.items():
    if len(duplicate_lots) < 2:
        continue

    product = env['product.product'].sudo().browse(product_id).exists()
    if not product:
        continue

    report['groups_found'] += 1
    lots_with_counts = [
        (lot, _lot_ref_counts(lot))
        for lot in duplicate_lots.sorted(
            key=lambda item: (
                bool(item.company_id),
                item.id,
            )
        )
    ]
    keeper = next((lot for lot, _counts in lots_with_counts if not lot.company_id), False)
    if not keeper:
        keeper = lots_with_counts[0][0]
        success, error = _safe_write_global(keeper)
        report['keepers_globalized'].append({
            'lot_id': keeper.id,
            'name': keeper.name,
            'product_id': product_id,
            'applied': apply_cleanup and success,
            'error': error,
        })
        if error:
            continue

    for lot, counts in lots_with_counts:
        if lot == keeper:
            continue

        if counts['move_lines'] or counts['quants']:
            report['skipped_lots'].append({
                'lot_id': lot.id,
                'name': lot.name,
                'product_id': product_id,
                'reason': 'referenced',
                'move_lines': counts['move_lines'],
                'quants': counts['quants'],
            })
            continue

        success, error = _safe_archive(lot)
        if error:
            report['skipped_lots'].append({
                'lot_id': lot.id,
                'name': lot.name,
                'product_id': product_id,
                'reason': 'archive_failed',
                'error': error,
            })
            continue
        report['archived_lots'].append({
            'lot_id': lot.id,
            'name': lot.name,
            'product_id': product_id,
            'applied': apply_cleanup and success,
        })

duplicate_lot_cleanup_result = report
print(duplicate_lot_cleanup_result)
