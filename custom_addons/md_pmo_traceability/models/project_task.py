from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    # Mismos campos x_* en ambas instancias (Quifamesa y Medicine Depot) para
    # que los 3 workflows n8n (odoo_to_notion / github_to_odoo / notion_to_odoo)
    # sean un único template parametrizado por instancia. Ver
    # docs/architecture/project_traceability_orchestration.md §3.
    x_empresa = fields.Selection(
        selection=[
            ("quifamesa", "Quifamesa"),
            ("medicine_depot", "Medicine Depot"),
        ],
        string="Empresa",
        help="Empresa a la que pertenece esta tarea, usada para filtrar el "
        "dashboard PMO compartido de Notion.",
    )
    x_modulo_componente = fields.Selection(
        selection=[
            ("etl_db", "ETL / Extracción DB"),
            ("addon_odoo", "Addon Odoo"),
            ("api_movil", "API Móvil"),
            ("app_frontend", "App Frontend"),
            ("n8n_automation", "Automatización n8n"),
            ("reportes_qweb", "Reportes QWeb"),
        ],
        string="Módulo / Componente",
    )
    x_github_pr_url = fields.Char(
        string="URL de rama/PR de GitHub",
        help="Rama feature/MDS-<id>-... o URL del PR asociado a esta tarea.",
    )
    x_notion_page_id = fields.Char(
        string="ID de página en Notion",
        copy=False,
        help="ID de la página en la base 'Deliverables & Tasks Matrix' de "
        "Notion, usado por el workflow odoo_to_notion para hacer upsert "
        "idempotente.",
    )
    x_blocker_reason = fields.Text(
        string="Motivo de bloqueo",
        help="Solo relevante cuando la tarea está marcada como bloqueada "
        "(kanban_state=blocked).",
    )
