from collections import defaultdict

from odoo import api, models


class ReportScrapBatchConsolidated(models.AbstractModel):
    _name = 'report.medicine_depot_scrap_batch.report_scrap_consolidated'
    _description = 'Reporte consolidado de bajas por día'

    @api.model
    def _get_report_values(self, docids, data=None):
        batches = self.env['stock.scrap.batch'].browse(docids).sorted('date')

        # Agrupar órdenes por día (date part only)
        by_date = defaultdict(list)
        for batch in batches:
            day = batch.date.date() if batch.date else None
            by_date[day].append(batch)

        groups = []
        grand_total_cost = 0.0
        grand_total_qty = 0.0

        for day in sorted(by_date.keys(), key=lambda d: (d is None, d)):
            day_batches = by_date[day]

            # Consolidar líneas por producto dentro del grupo de día
            product_map = {}
            for batch in day_batches:
                for line in batch.line_ids:
                    pid = line.product_id.id
                    if pid not in product_map:
                        product_map[pid] = {
                            'product': line.product_id,
                            'uom': line.product_uom_id,
                            'qty': 0.0,
                            'cost': 0.0,
                            'lots': [],
                        }
                    product_map[pid]['qty'] += line.scrap_qty
                    product_map[pid]['cost'] += line.scrap_total_cost
                    if line.lot_id and line.lot_id.name not in product_map[pid]['lots']:
                        product_map[pid]['lots'].append(line.lot_id.name)

            consolidated_lines = sorted(
                product_map.values(),
                key=lambda r: r['product'].display_name,
            )

            day_total_qty = sum(r['qty'] for r in consolidated_lines)
            day_total_cost = sum(r['cost'] for r in consolidated_lines)
            grand_total_qty += day_total_qty
            grand_total_cost += day_total_cost

            # Recopilar motivos únicos del día
            reason_tags = set()
            for batch in day_batches:
                for tag in batch.scrap_reason_tag_ids:
                    reason_tags.add(tag.name)

            groups.append({
                'date': day,
                'batches': day_batches,
                'lines': consolidated_lines,
                'day_total_qty': day_total_qty,
                'day_total_cost': day_total_cost,
                'reason_tags': sorted(reason_tags),
                'company': day_batches[0].company_id if day_batches else self.env.company,
                'currency': day_batches[0].currency_id if day_batches else self.env.company.currency_id,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'stock.scrap.batch',
            'docs': batches,
            'groups': groups,
            'grand_total_qty': grand_total_qty,
            'grand_total_cost': grand_total_cost,
            'user': self.env.user,
        }
