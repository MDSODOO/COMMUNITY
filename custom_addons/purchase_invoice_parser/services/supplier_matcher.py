import logging

_logger = logging.getLogger(__name__)


class SupplierMatcher:
    """
    En CFDI el RFC es único y determinista — no se necesita fuzzy matching.
    Estrategia: RFC exacto → RFC parcial (12 chars) → nombre ilike → sin match.
    """

    def __init__(self, env):
        self.env = env

    def find_partner(self, rfc=None, nombre=None, company_id=None):
        """
        Retorna (partner, confidence, method).
        company_id: filtrar por compañía asignada al partner (None = sin filtro).
        """
        Partner = self.env['res.partner']

        company_domain = []
        if company_id:
            company_domain = [('company_id', 'in', [company_id, False])]

        if rfc:
            partner = Partner.search(
                [('vat', '=ilike', rfc), ('supplier_rank', '>', 0)] + company_domain,
                limit=1,
            )
            if partner:
                return partner, 1.0, 'rfc_exact'

            partner = Partner.search(
                [('vat', 'ilike', rfc[:12]), ('supplier_rank', '>', 0)] + company_domain,
                limit=1,
            )
            if partner:
                return partner, 0.9, 'rfc_partial'

        if nombre:
            partner = Partner.search(
                [('name', 'ilike', nombre), ('supplier_rank', '>', 0)] + company_domain,
                limit=1,
            )
            if partner:
                return partner, 0.7, 'name_ilike'

        return None, 0.0, 'unresolved'
