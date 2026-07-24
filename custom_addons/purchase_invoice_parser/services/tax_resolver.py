import logging
from odoo import _

_logger = logging.getLogger(__name__)


class TaxResolver:
    """
    Resuelve account.tax para una compañía destino.
    Mantiene un caché interno por instancia para evitar queries repetidas.
    """

    def __init__(self, env, company):
        self.env = env
        self.company = company
        self._cache = {}
        self.warnings = []  # Avisos de tasa no coincidente (ej. CFDI 16% → sucursal 8%)

    def resolve(self, tasa, factor='', iva_presente=True):
        """
        Retorna el account.tax correcto para la tasa/factor dados.
        Si la tasa no está configurada para la compañía, retorna recordset vacío
        y acumula un aviso en self.warnings (no lanza excepción).
        Retorna recordset vacío cuando iva_presente=False.
        """
        key = (
            self.company.id,
            round(float(tasa or 0.0), 6),
            (factor or '').lower(),
            bool(iva_presente),
        )
        if key in self._cache:
            return self._cache[key]

        Tax = self.env['account.tax'].with_company(self.company)
        company_id = self.company.id
        tax = Tax.browse()

        if not iva_presente:
            self._cache[key] = tax
            return tax

        factor_low = (factor or '').strip().lower()
        if factor_low == 'exento':
            candidates = Tax.search([
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company_id),
                ('amount', '=', 0.0),
            ])
            tax = self._pick(candidates, expect_exento=True)
            if not tax:
                for fallback_id in self.env.companies.ids:
                    if fallback_id == company_id:
                        continue
                    fb = Tax.search([
                        ('type_tax_use', '=', 'purchase'),
                        ('company_id',   '=', fallback_id),
                        ('amount',       '=', 0.0),
                    ])
                    tax = self._pick(fb, expect_exento=True)
                    if tax:
                        _logger.info(
                            "TaxResolver: IVA Exento no encontrado en %s; "
                            "usando impuesto de %s (id=%d '%s') por fallback.",
                            self.company.display_name,
                            tax.company_id.display_name, tax.id, tax.name,
                        )
                        break
        else:
            pct = float(round(float(tasa or 0.0) * 100, 4))

            # 1. Búsqueda exacta con 'compra' en nombre (prioridad por convención de nombres)
            candidates = Tax.search([
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company_id),
                ('amount_type', '=', 'percent'),
                ('amount', '=', pct),
                ('name', 'ilike', 'compra'),
            ])
            tax = self._pick(candidates)

            # 2. Búsqueda exacta por tipo porcentaje (sin filtro de nombre)
            if not tax:
                candidates = Tax.search([
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', company_id),
                    ('amount_type', '=', 'percent'),
                    ('amount', '=', pct),
                ])
                tax = self._pick(candidates)

            # 3. Búsqueda exacta sin filtrar amount_type (cubre 'fixed' mal configurado)
            if not tax:
                candidates = Tax.search([
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', company_id),
                    ('amount', '=', pct),
                ])
                tax = self._pick(candidates)

            # 4. Búsqueda por tolerancia de punto flotante (ej. 0.160000 → 15.9999...)
            if not tax:
                all_candidates = Tax.search([
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', company_id),
                    ('amount_type', '=', 'percent'),
                ])
                near = all_candidates.filtered(lambda t: abs(t.amount - pct) < 0.01)
                tax = self._pick(near)
                if tax:
                    _logger.info(
                        "IVA resuelto por tolerancia: se buscó %.4f%%, encontrado %.4f%% "
                        "(id=%d, %s) para %s",
                        pct, tax.amount, tax.id, tax.name,
                        self.company.display_name,
                    )

            # 5. Fallback: buscar en el resto de empresas activas en la sesión
            # (env.companies = allowed_company_ids). Replica el comportamiento de
            # la UI, que muestra impuestos de todas las empresas del switcher.
            if not tax and abs(pct) >= 1e-9:
                for fallback_id in self.env.companies.ids:
                    if fallback_id == self.company.id:
                        continue
                    fb = Tax.search([
                        ('type_tax_use', '=', 'purchase'),
                        ('company_id',   '=', fallback_id),
                        ('amount_type',  '=', 'percent'),
                        ('amount',       '=', pct),
                    ])
                    tax = self._pick(fb)
                    if tax:
                        _logger.info(
                            "TaxResolver: IVA %g%% no encontrado en %s; "
                            "usando impuesto de %s (id=%d '%s') por fallback.",
                            pct, self.company.display_name,
                            tax.company_id.display_name, tax.id, tax.name,
                        )
                        break

            if not tax:
                if abs(pct) < 1e-9:
                    _logger.info(
                        "Sin impuesto de compra 0%% configurado para %s; "
                        "la línea se creará sin tax_ids.",
                        self.company.display_name,
                    )
                else:
                    warn_msg = _(
                        "⚠ IVA %(tasa)s%% del CFDI no está configurado como impuesto "
                        "de Compras para %(scope)s ni en ninguna empresa activa. "
                        "Tasas válidas: revisa Contabilidad → Configuración → Impuestos."
                    ) % {'tasa': f'{pct:g}', 'scope': self._company_label()}
                    if warn_msg not in self.warnings:
                        self.warnings.append(warn_msg)
                    _logger.warning(
                        "TaxResolver: IVA %g%% no encontrado para %s ni en fallback "
                        "— línea sin impuesto.",
                        pct, self.company.display_name,
                    )
                self._cache[key] = tax
                return tax

        self._cache[key] = tax
        return tax

    @staticmethod
    def _pick(candidates, expect_exento=False):
        """Selecciona el impuesto más específico priorizando IVA Compras."""
        candidates = candidates.filtered(lambda t: t.type_tax_use == 'purchase')
        if not candidates:
            return candidates
        if expect_exento:
            exento_named = candidates.filtered(
                lambda t: 'exent' in (t.name or '').lower()
            )
            if exento_named:
                candidates = exento_named
        compras_named = candidates.filtered(
            lambda t: 'compra' in (t.name or '').lower()
        )
        if compras_named:
            candidates = compras_named
        iva_named = candidates.filtered(
            lambda t: 'iva' in (t.name or '').lower()
        )
        if iva_named:
            candidates = iva_named
        return candidates.sorted(lambda t: (t.sequence, t.id))[:1]

    def _company_label(self):
        name = (self.company.display_name or '').strip()
        if not name:
            return _('la compañía destino')
        if 'matriz' in name.lower():
            return _('la Matriz')
        return name
