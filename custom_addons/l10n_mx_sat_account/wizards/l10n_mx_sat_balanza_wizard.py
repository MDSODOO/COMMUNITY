# -*- coding: utf-8 -*-
import base64
import calendar
from xml.etree import ElementTree as ET

from odoo import fields, models
from odoo.exceptions import UserError

# Esquema real confirmado contra el XSD oficial del SAT:
# http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion/BalanzaComprobacion_1_3.xsd
# Root "Balanza" (Version/RFC/Mes/Anio/TipoEnvio), hijos "Ctas"
# (NumCta/SaldoIni/Debe/Haber/SaldoFin, t_Importe = decimal 2 posiciones).
NS = "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion"


class L10nMxSatBalanzaWizard(models.TransientModel):
    _name = "l10n_mx.sat.balanza.wizard"
    _description = "Exportar Balanza de Comprobación SAT (XML)"

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
                    "asignado. Mapea al menos una cuenta antes de generar "
                    "la balanza.",
                    name=company.name,
                )
            )

        date_from = fields.Date.from_string(f"{self.year}-{self.month}-01")
        last_day = calendar.monthrange(self.year, int(self.month))[1]
        date_to = date_from.replace(day=last_day)

        root = ET.Element(
            f"{{{NS}}}Balanza",
            {
                "Version": "1.3",
                "RFC": company.vat,
                "Mes": self.month,
                "Anio": str(self.year),
                "TipoEnvio": "N",
            },
        )

        AML = self.env["account.move.line"]
        mapped_with_movement = 0
        for account in accounts:
            base_domain = [
                ("account_id", "=", account.id),
                ("company_id", "=", company.id),
                ("parent_state", "=", "posted"),
            ]
            initial_lines = AML.search(base_domain + [("date", "<", date_from)])
            saldo_ini = sum(initial_lines.mapped("debit")) - sum(
                initial_lines.mapped("credit")
            )

            period_lines = AML.search(
                base_domain + [("date", ">=", date_from), ("date", "<=", date_to)]
            )
            debe = sum(period_lines.mapped("debit"))
            haber = sum(period_lines.mapped("credit"))
            saldo_fin = saldo_ini + debe - haber

            if not (initial_lines or period_lines):
                # Sin ningún movimiento histórico ni del periodo: no tiene
                # sentido incluirla en la balanza de este mes.
                continue
            mapped_with_movement += 1

            ET.SubElement(
                root,
                f"{{{NS}}}Ctas",
                {
                    "NumCta": account.code or str(account.id),
                    "SaldoIni": f"{saldo_ini:.2f}",
                    "Debe": f"{debe:.2f}",
                    "Haber": f"{haber:.2f}",
                    "SaldoFin": f"{saldo_fin:.2f}",
                },
            )

        if mapped_with_movement == 0:
            raise UserError(
                self.env._(
                    "Ninguna de las cuentas mapeadas a código agrupador tiene "
                    "movimiento en %(mes)s/%(anio)s para %(name)s.",
                    mes=self.month,
                    anio=self.year,
                    name=company.name,
                )
            )

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"BalanzaComprobacion_{company.vat}_{self.year}{self.month}.xml",
                "type": "binary",
                "datas": base64.b64encode(xml_bytes),
                "mimetype": "application/xml",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
            "context": {
                "l10n_mx_sat_balanza_mapped": mapped_with_movement,
                "l10n_mx_sat_balanza_total": total_accounts,
            },
        }
