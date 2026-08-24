from odoo import models, fields
from odoo.tools.translate import _
import base64
import io
import csv


class RestrictedProductImport(models.TransientModel):
    _name = 'restricted.product.import'
    _description = 'Import Restricted Product SKUs'

    csv_file = fields.Binary(
        string='CSV File',
        required=True,
        help='Upload a CSV file with columns: ean, marca, nombre',
    )
    csv_filename = fields.Char(string='Filename')
    import_log = fields.Text(
        string='Import Log',
        readonly=True,
        help='Results of the import process.',
    )

    def action_import(self):
        """Import restricted SKUs from CSV (ean,marca,nombre)."""
        if not self.csv_file:
            raise ValueError(_('Please upload a CSV file.'))

        try:
            decoded = base64.b64decode(self.csv_file).decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded))

            if not csv_reader.fieldnames or 'ean' not in csv_reader.fieldnames:
                raise ValueError(_('CSV must have columns: ean, marca, nombre'))

            sku_model = self.env['sale.restricted.sku']
            product_model = self.env['product.product']
            tag_model = self.env['product.tag']

            logs = []
            imported = 0
            updated = 0
            not_found = 0

            sku_tag = tag_model.search([('name', '=', 'SKU_RESTRINGIDO_EAN')], limit=1)
            if not sku_tag:
                sku_tag = tag_model.create({'name': 'SKU_RESTRINGIDO_EAN'})

            for row in csv_reader:
                ean = row.get('ean', '').strip()
                marca = row.get('marca', '').strip()
                nombre = row.get('nombre', '').strip()

                if not ean:
                    logs.append(_('Warning: empty EAN, skipping row'))
                    continue

                existing_sku = sku_model.search([('ean', '=', ean)], limit=1)
                if existing_sku:
                    existing_sku.write({'marca': marca, 'nombre': nombre})
                    updated += 1
                    log_entry = _('Updated SKU %s') % ean
                else:
                    sku_model.create({'ean': ean, 'marca': marca, 'nombre': nombre})
                    imported += 1
                    log_entry = _('Created SKU %s') % ean

                product = product_model.search([('barcode', '=', ean)], limit=1)
                if product:
                    if sku_tag not in product.product_tmpl_id.product_tag_ids:
                        product.product_tmpl_id.product_tag_ids = [(4, sku_tag.id)]
                    log_entry += _(' -> tagged: %s') % product.name
                else:
                    not_found += 1

                logs.append(log_entry)

            summary = _(
                'Import completed:\n'
                'Created: %(imported)d\n'
                'Updated: %(updated)d\n'
                'Products not in catalog: %(not_found)d',
                imported=imported,
                updated=updated,
                not_found=not_found,
            )

            self.import_log = '\n'.join(logs) + '\n\n' + summary

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Complete'),
                    'message': summary,
                    'type': 'success' if imported > 0 else 'warning',
                    'sticky': True,
                },
            }
        except Exception as e:
            raise ValueError(_('CSV parsing error: %s') % str(e))
