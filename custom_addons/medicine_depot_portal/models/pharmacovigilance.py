# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

# Opciones reutilizadas por el controlador público (evita duplicación)
PATIENT_SEX_SELECTION = [
    ("female",      "Femenino"),
    ("male",        "Masculino"),
    ("other",       "Otro"),
    ("unspecified", "Prefiero no decirlo"),
]
SEVERITY_SELECTION = [
    ("mild",     "Leve"),
    ("moderate", "Moderado"),
    ("severe",   "Severo"),
    ("serious",  "Grave"),
]
OUTCOME_SELECTION = [
    ("recovered",     "Recuperado"),
    ("recovering",    "En recuperación"),
    ("not_recovered", "No recuperado"),
    ("unknown",       "Desconocido"),
]
REPORTER_ROLE_SELECTION = [
    ("patient",    "Paciente"),
    ("relative",   "Familiar"),
    ("healthcare", "Profesional de salud"),
    ("pharmacy",   "Personal de farmacia"),
    ("other",      "Otro"),
]
REPORTER_RELATIONSHIP_SELECTION = [
    ("self",           "Soy el paciente"),
    ("family",         "Soy familiar"),
    ("doctor",         "Soy médico o personal de salud"),
    ("pharmacy_staff", "Soy personal de farmacia"),
    ("other",          "Otro"),
]


class MedicineDepotPharmacovigilanceReport(models.Model):
    _name = "medicine.depot.pharmacovigilance.report"
    _description = "Medicine Depot Pharmacovigilance Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "report_date desc, id desc"
    _name_uniq = models.Constraint(
        'unique (name)',
        'El folio de pharmacovigilancia debe ser único.',
    )

    name = fields.Char(string="Folio", required=True, copy=False, readonly=True, default="/")
    report_date = fields.Datetime(string="Fecha de captura", readonly=True, default=fields.Datetime.now)
    state = fields.Selection(
        [
            ("submitted", "Recibido"),
            ("in_review", "En revisión"),
            ("done", "Cerrado"),
        ],
        string="Estado",
        default="submitted",
        required=True,
        index=True,
        tracking=True,
    )
    source = fields.Selection(
        [
            ("website", "Sitio web"),
        ],
        string="Origen",
        default="website",
        readonly=True,
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True, index=True)
    website_id = fields.Many2one("website", string="Sitio web", readonly=True, index=True)

    patient_name = fields.Char(string="Nombre del paciente", required=True)
    patient_age = fields.Integer(string="Edad del paciente")
    patient_sex = fields.Selection(PATIENT_SEX_SELECTION, string="Sexo del paciente")
    patient_city = fields.Char(string="Ciudad / estado")

    event_date = fields.Date(string="Fecha del evento")
    event_severity = fields.Selection(SEVERITY_SELECTION, string="Gravedad", tracking=True)
    event_outcome  = fields.Selection(OUTCOME_SELECTION, string="Evolución")
    event_description = fields.Text(string="Descripción del evento", required=True)

    suspected_product_name = fields.Char(string="Producto sospechoso", required=True)
    suspected_product_presentation = fields.Char(string="Presentación")
    suspected_batch = fields.Char(string="Lote / serie")
    suspected_dose = fields.Char(string="Dosis / frecuencia")

    medical_history = fields.Text(string="Antecedentes médicos")
    current_condition = fields.Text(string="Estado de salud actual")
    concomitant_medication = fields.Text(string="Medicamentos concomitantes")

    reporter_name = fields.Char(string="Nombre del notificador", required=True)
    reporter_role         = fields.Selection(REPORTER_ROLE_SELECTION, string="Perfil del notificador", required=True)
    reporter_relationship = fields.Selection(REPORTER_RELATIONSHIP_SELECTION, string="Relación con el paciente", required=True)
    reporter_email = fields.Char(string="Correo electrónico", required=True)
    reporter_phone = fields.Char(string="Teléfono")
    consent = fields.Boolean(string="Acepta privacidad", default=False)
    notes = fields.Text(string="Observaciones")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") in ("/", _("Nuevo")):
                vals["name"] = sequence.next_by_code("medicine.depot.pharmacovigilance.report") or "/"
            vals.setdefault("state", "submitted")
            vals.setdefault("source", "website")
            vals.setdefault("report_date", fields.Datetime.now())
            vals.setdefault("company_id", self.env.company.id)
            if not vals.get("website_id") and self.env.context.get("website_id"):
                vals["website_id"] = self.env.context["website_id"]
        return super().create(vals_list)
