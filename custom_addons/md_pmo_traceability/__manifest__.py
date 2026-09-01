{
    "name": "MDS PMO Traceability",
    "version": "19.0.1.0.0",
    "category": "Project",
    "summary": "Trazabilidad PMO Medicine Depot: proyectos, etapas y campos custom para "
    "el dashboard Notion + integraciones n8n/GitHub.",
    "description": """
Módulo de trazabilidad para el track Medicine Depot del proyecto de
orquestación PMO (Odoo <-> Notion <-> GitHub vía n8n).

Crea:
- Los proyectos [MDS] Medicine Depot - Migración Odoo.sh a Community v19 y
  [MDS] Medicine Depot - Mobile API & App, con subtareas iniciales.
- Las 6 etapas del pipeline PMO (idénticas en nombre/orden al track Quifamesa,
  para que el mapeo n8n sea un diccionario 1:1).
- Campos custom en project.task: x_empresa, x_modulo_componente,
  x_github_pr_url, x_notion_page_id, x_blocker_reason.

Ver docs/architecture/track_medicine_depot.md en el repo raíz de
pmo-trazabilidad para el diseño completo.
""",
    "author": "Medicine Depot",
    "license": "LGPL-3",
    "depends": ["project"],
    "data": [
        "data/project_pmo_data.xml",
    ],
    "installable": True,
    "application": False,
}
