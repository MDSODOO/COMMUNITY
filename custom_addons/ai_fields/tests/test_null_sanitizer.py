# -*- coding: utf-8 -*-
from unittest import TestCase

from ai_fields.models.null_sanitizer import _col_exists, _sanitize_nulls, _table_exists


class FakeCursor:
    def __init__(self):
        self.tables = {
            'account_account': [{'create_asset': None}, {'create_asset': 'no'}],
            'website': [{
                'shop_default_sort': None,
                'product_page_image_layout': None,
                'product_page_image_width': None,
                'product_page_image_spacing': None,
                'product_page_image_roundness': None,
                'product_page_image_ratio': None,
                'product_page_image_ratio_mobile': None,
                'ecommerce_access': None,
            }],
            'purchase_order': [{'picking_type_id': 1, 'company_id': 1}],
            'stock_picking_type': [{'id': 1, 'code': 'incoming'}],
            'stock_warehouse': [{'id': 1, 'company_id': 1}],
            'product_template': [{'base_unit_count': None}],
            'product_product': [{'base_unit_count': None}],
            'account_reports_export_wizard': [{'folder_id': 1}],
            'documents_folder': [{'id': 1, 'parent_folder_id': None}],
        }
        self.rowcount = 0
        self._fetchone = None
        self.update_history = []

    def execute(self, query, params=None):
        normalized = ' '.join(query.lower().split())
        self.rowcount = 0
        self._fetchone = None

        if 'information_schema.columns' in normalized:
            if 'select data_type' in normalized:
                table, column = params
                if self._has_column(table, column):
                    self._fetchone = (self._column_type(table, column),)
                else:
                    self._fetchone = None
                return
            table, column = params
            self._fetchone = (1,) if self._has_column(table, column) else None
            return

        if 'information_schema.tables' in normalized:
            table = params[0]
            self._fetchone = (1,) if table in self.tables else None
            return

        if normalized.startswith('select count(*) from website where '):
            column = normalized.split('where ', 1)[1].split(' is null', 1)[0]
            count = sum(1 for row in self.tables['website'] if row.get(column) is None)
            self._fetchone = (count,)
            return

        if normalized.startswith('update account_account set create_asset'):
            self._update_nulls('account_account', 'create_asset', 'no')
            return

        if normalized.startswith('update website w set'):
            column = normalized.split('update website w set ', 1)[1].split(' = ', 1)[0]
            self.update_history.append(('website', column, 0))
            return

        if normalized.startswith('update website set'):
            column = normalized.split('update website set ', 1)[1].split(' = ', 1)[0]
            if ' = false where ' in normalized:
                self._update_nulls('website', column, False)
            elif ' = 0 where ' in normalized:
                self._update_nulls('website', column, 0)
            else:
                self._update_nulls('website', column, params[0])
            return

        if normalized.startswith('update purchase_order'):
            self.update_history.append(('purchase_order', 'picking_type_id', 0))
            return

        if normalized.startswith('update product_template set base_unit_count'):
            self._update_nulls('product_template', 'base_unit_count', 1.0)
            return

        if normalized.startswith('update product_product set base_unit_count'):
            self._update_nulls('product_product', 'base_unit_count', 0)
            return

        if normalized.startswith('update account_reports_export_wizard'):
            self.update_history.append((
                'account_reports_export_wizard',
                'folder_id',
                0,
            ))

    def fetchone(self):
        return self._fetchone

    def _has_column(self, table, column):
        return table in self.tables and any(column in row for row in self.tables[table])

    def _column_type(self, table, column):
        numeric_website_columns = {
            'product_page_image_width',
            'product_page_image_spacing',
            'product_page_image_roundness',
        }
        if table == 'website' and column in numeric_website_columns:
            return 'integer'
        return 'character varying'

    def _update_nulls(self, table, column, value):
        updated = 0
        for row in self.tables[table]:
            if row.get(column) is None:
                row[column] = value
                updated += 1
        self.rowcount = updated
        self.update_history.append((table, column, updated))


class TestNullSanitizer(TestCase):
    def test_sanitize_nulls_is_idempotent(self):
        cr = FakeCursor()

        _sanitize_nulls(cr)
        first_history_len = len(cr.update_history)
        first_updates = [event for event in cr.update_history if event[2] > 0]

        _sanitize_nulls(cr)
        second_events = cr.update_history[first_history_len:]

        self.assertTrue(first_updates)
        self.assertTrue(second_events)
        self.assertTrue(all(event[2] == 0 for event in second_events))

    def test_audited_columns_are_guarded_before_update(self):
        cr = FakeCursor()
        expected_columns = [
            ('account_account', 'create_asset'),
            ('website', 'shop_default_sort'),
            ('website', 'product_page_image_layout'),
            ('website', 'product_page_image_width'),
            ('website', 'product_page_image_spacing'),
            ('website', 'product_page_image_roundness'),
            ('website', 'product_page_image_ratio'),
            ('website', 'product_page_image_ratio_mobile'),
            ('website', 'ecommerce_access'),
            ('purchase_order', 'picking_type_id'),
            ('product_template', 'base_unit_count'),
            ('product_product', 'base_unit_count'),
            ('account_reports_export_wizard', 'folder_id'),
        ]

        for table, column in expected_columns:
            self.assertTrue(_col_exists(cr, table, column), (table, column))

        self.assertTrue(_table_exists(cr, 'stock_picking_type'))
        self.assertTrue(_table_exists(cr, 'documents_folder'))
