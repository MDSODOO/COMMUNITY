# -*- coding: utf-8 -*-
{
    "name": "MDS - Catálogo de Cuentas SAT (Contabilidad Electrónica)",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Código agrupador SAT y export XML del Catálogo de Cuentas (Anexo 24)",
    "description": """
Primera pieza de Contabilidad Electrónica para México: no existe ningún
módulo Community/OCA que la provea (verificado a fondo en esta sesión,
incluyendo los 20 módulos de OCA/l10n-mexico).

- Tabla de referencia del código agrupador SAT completa, transcrita
  directamente del Anexo 24 de la RMF 2026 (DOF, 13-enero-2026),
  fuente oficial primaria — no de un tercero.
- Campo `sat_group_code_id` en `account.account` para mapear cada cuenta
  al código agrupador correspondiente.
- Wizard que exporta el Catálogo de Cuentas en el esquema XML real del
  SAT (`Catalogo`/`Ctas`, namespace ContabilidadE 1.1), confirmado contra
  el XSD oficial publicado por el SAT.

Ver docs/plans/PLAN_ADAPTACION_CONTABILIDAD_COMMUNITY.md para el alcance
completo y lo que falta (firmado/sellado digital, envío real al SAT,
Balanza y Pólizas quedan fuera de este módulo).
    """,
    "author": "Medicine Depot",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_mx.sat.account.group.code.csv",
        "views/account_account_views.xml",
        "views/l10n_mx_sat_account_group_code_views.xml",
        "views/l10n_mx_sat_catalogo_wizard_views.xml",
    ],
    "installable": True,
}
