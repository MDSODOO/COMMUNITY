# -*- coding: utf-8 -*-
import base64
from xml.etree import ElementTree as ET

from odoo import fields, models
from odoo.exceptions import UserError

# Naturaleza D (deudora) para cuentas con saldo normal deudor,
# A (acreedora) para las de saldo normal acreedor -- según el propio
# account_type nativo de Odoo, no según el código agrupador.
_DEBIT_NORMAL_TYPES = {
    "asset_receivable",
    "asset_cash",
    "asset_current",
    "asset_non_current",
    "asset_prepayments",
    "asset_fixed",
    "expense",
    "expense_depreciation",
    "expense_direct_cost",
}
_CREDIT_NORMAL_TYPES = {
    "liability_payable",
    "liability_credit_card",
    "liability_current",
    "liability_non_current",
    "equity",
    "equity_unaffected",
    "income",
    "income_other",
}

NS = "http://www.sat.gob.mx/esquemas/ContabilidadE/1_1/CatalogoCuentas"


class L10nMxSatCatalogoWizard(models.TransientModel):
    _name = "l10n_mx.sat.catalogo.wizard"
    _description = "Exportar Catálogo de Cuentas SAT (XML)"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    month = fields.Selection(
        [(f"{i:02d}", f"{i:02d}") for i in range(1, 13)],
        required=True,
        default=lambda self: fields.Date.context_today(self).strftime("%m"),
    )
    year = fields.Integer(
        required=True, default=lambda self: fields.Date.context_today(self).year
    )

    def action_generate_xml(self):
        self.ensure_one()
        company = self.company_id
        if not company.vat:
            raise UserError(
                self.env._(
                    "La compañía %(name)s no tiene RFC configurado -- "
                    "requerido por el esquema del SAT (atributo RFC).",
                    name=company.name,
                )
            )

        accounts = (
            self.env["account.account"]
            .with_company(company)
            .search(
                [
                    ("company_ids", "in", company.id),
                    ("l10n_mx_sat_group_code_id", "!=", False),
                ]
            )
        )
        total_accounts = (
            self.env["account.account"]
            .with_company(company)
            .search_count([("company_ids", "in", company.id)])
        )
        if not accounts:
            raise UserError(
                self.env._(
                    "Ninguna cuenta de %(name)s tiene código agrupador SAT "
                    "asignado (sat_group_code_id). Mapea al menos una "
                    "cuenta antes de generar el catálogo.",
                    name=company.name,
                )
            )

        root = ET.Element(
            f"{{{NS}}}Catalogo",
            {
                "Version": "1.1",
                "RFC": company.vat,
                "Mes": self.month,
                "Anio": str(self.year),
            },
        )
        for account in accounts:
            natur = (
                "D"
                if account.account_type in _DEBIT_NORMAL_TYPES
                else "A" if account.account_type in _CREDIT_NORMAL_TYPES else "D"
            )
            ET.SubElement(
                root,
                f"{{{NS}}}Ctas",
                {
                    "CodAgrup": account.l10n_mx_sat_group_code_id.code,
                    "NumCta": account.code or str(account.id),
                    "Desc": account.name or "",
                    # Simplificación: catálogo plano, sin jerarquía de
                    # subcuentas explícita en este ambiente -- todas
                    # nivel 1. Si el contribuyente maneja subcuentas
                    # reales (SubCtaDe), esto requiere revisión.
                    "Nivel": "1",
                    "Natur": natur,
                },
            )

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"CatalogoCuentas_{company.vat}_{self.year}{self.month}.xml",
                "type": "binary",
                "datas": base64.b64encode(xml_bytes),
                "mimetype": "application/xml",
            }
        )
        mapped = len(accounts)
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
            "context": {
                "l10n_mx_sat_catalogo_mapped": mapped,
                "l10n_mx_sat_catalogo_total": total_accounts,
            },
        }
