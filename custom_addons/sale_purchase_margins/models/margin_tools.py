# -*- coding: utf-8 -*-
import re
import unicodedata

from odoo import fields


def get_line_company(line):
    if 'company_id' in line._fields and line.company_id:
        return line.company_id
    if 'order_id' in line._fields and line.order_id and line.order_id.company_id:
        return line.order_id.company_id
    return line.env.company


def get_line_currency(line, company=None):
    if 'currency_id' in line._fields and line.currency_id:
        return line.currency_id
    if 'order_id' in line._fields and line.order_id and line.order_id.currency_id:
        return line.order_id.currency_id
    company = company or get_line_company(line)
    return company.currency_id


def get_line_date(line):
    order = line.order_id if 'order_id' in line._fields else False
    date_order = order.date_order if order and 'date_order' in order._fields else False
    return fields.Date.to_date(date_order) if date_order else fields.Date.context_today(line)


def get_line_uom(line, product, field_name):
    if field_name in line._fields and line[field_name]:
        return line[field_name]
    return product.uom_id


def convert_unit_price(price, from_uom, to_uom, from_currency, to_currency, company, date):
    if from_uom and to_uom and from_uom != to_uom:
        price = from_uom._compute_price(price, to_uom)
    if from_currency and to_currency and from_currency != to_currency:
        price = from_currency._convert(price, to_currency, company, date)
    return price


def get_standard_cost_for_line(line, uom_field_name):
    product = line.product_id
    if not product:
        return 0.0

    company = get_line_company(line)
    currency = get_line_currency(line, company)
    date = get_line_date(line)
    product = product.with_company(company)
    product_uom = product.uom_id
    line_uom = get_line_uom(line, product, uom_field_name)

    return convert_unit_price(
        product.standard_price or 0.0,
        product_uom,
        line_uom,
        company.currency_id,
        currency,
        company,
        date,
    )


def normalize_margin_key(value):
    value = (value or '').strip().upper()
    value = ''.join(
        char for char in unicodedata.normalize('NFD', value)
        if unicodedata.category(char) != 'Mn'
    )
    value = re.sub(r'[^A-Z0-9]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def should_apply_price_update(policy, old_price, new_price):
    if policy == 'manual_review':
        return False
    if policy == 'only_increase':
        return new_price > (old_price or 0.0)
    return True


def price_update_reason(policy, should_update, old_price, new_price):
    if policy == 'manual_review':
        return 'Modo sugerencia: no se aplica cambio automático.'
    if policy == 'only_increase' and not should_update:
        return (
            f'Política "Solo aumentar": precio nuevo ({new_price:.2f}) '
            f'no supera al actual ({old_price:.2f}).'
        )
    if should_update:
        return 'Precio actualizado automáticamente por política activa.'
    return 'No se aplicó actualización automática.'
