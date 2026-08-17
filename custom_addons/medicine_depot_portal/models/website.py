# -*- coding: utf-8 -*-
import json
import re
from urllib.parse import quote_plus

from markupsafe import Markup

from odoo import models, tools
from odoo.http import request

# Coordenadas conocidas por ciudad normalizada (igual que en el controlador)
_BRANCH_COORDS = {
    "mérida":           (20.9674, -89.5926),
    "merida":           (20.9674, -89.5926),
    "ticul":            (20.3954, -89.5228),
    "campeche":         (19.8301, -90.5349),
    "cancún":           (21.1619, -86.8515),
    "cancun":           (21.1619, -86.8515),
    "chetumal":         (18.5011, -88.3018),
    "playa del carmen": (20.6540, -87.0682),
}
_BRANCH_STATE_KEY = {
    "mérida": "yucatan", "merida": "yucatan",
    "ticul":  "yucatan",
    "campeche": "campeche",
    "cancún": "qroo", "cancun": "qroo",
    "chetumal": "qroo",
    "playa del carmen": "qroo",
}
_NAME_PREFIXES = ("mds ", "md ", "medicine depot ", "medicine depot sureste ", "farmacia ")
_GMAP_FIELDS   = ("name", "address", "phone", "whatsapp_url", "maps_url", "lat", "lng", "state_key", "city")
_BRANCH_MAP_URLS = {
    "mérida": "https://maps.app.goo.gl/yuoGwpfnShyntM7x5?g_st=awb",
    "merida": "https://maps.app.goo.gl/yuoGwpfnShyntM7x5?g_st=awb",
    "campeche": "https://maps.app.goo.gl/UAEwdQmQW6pfwezDA?g_st=awb",
    "playa del carmen": "https://maps.app.goo.gl/y2wCoF1MWmw7XeYq6?g_st=awb",
    "ticul": "https://maps.app.goo.gl/QMSKsg2sg87YHpteA?g_st=awb",
    "cancún": "https://maps.app.goo.gl/pLsGau8TNF8AaYtW6?g_st=awb",
    "cancun": "https://maps.app.goo.gl/pLsGau8TNF8AaYtW6?g_st=awb",
    "chetumal": "https://maps.app.goo.gl/jdHRLsWnnjzdTTf2A?g_st=awb",
}


def _normalize(name):
    key = (name or "").lower().strip()
    for prefix in _NAME_PREFIXES:
        if key.startswith(prefix):
            return key[len(prefix):].strip()
    return key


def _map_url(name, address):
    official_url = _BRANCH_MAP_URLS.get(_normalize(name))
    if official_url:
        return official_url
    query = " ".join(p for p in (name, address) if p)
    return "https://www.google.com/maps/search/?api=1&query=%s" % quote_plus(query)


def _whatsapp_url(phone):
    digits = re.sub(r"\D+", "", phone or "")
    return "https://wa.me/%s" % digits if digits else ""


def _enrich(card):
    key = _normalize(card["name"])
    lat, lng = _BRANCH_COORDS.get(key, (0.0, 0.0))
    return {**card, "lat": lat, "lng": lng, "city": card["name"],
            "state_key": _BRANCH_STATE_KEY.get(key, ""),
            "open_time": "09:00", "close_time": "19:00"}


class Website(models.Model):
    _inherit = 'website'
    _description = 'Website (MD branch cards cache)'

    @tools.ormcache('self.id')
    def _md_branch_cards_json(self):
        """Retorna JSON de sucursales para el widget de Google Maps. Resultado cacheado por website."""
        Warehouse = self.env['stock.warehouse'].sudo()
        warehouses = Warehouse.search([('active', '=', True)], order='sequence,id')
        cards = []
        for wh in warehouses:
            partner = wh.partner_id.sudo() if 'partner_id' in wh._fields and wh.partner_id else False
            name = wh.display_name or wh.name or 'Sucursal'
            address_parts = []
            if partner:
                for f in ('street', 'street2', 'city', 'state_id', 'zip', 'country_id'):
                    if f not in partner._fields:
                        continue
                    val = partner[f]
                    if not val:
                        continue
                    address_parts.append(val.name if f in ('state_id', 'country_id') else str(val).strip())
            address = ', '.join(p for p in address_parts if p)
            phone = (partner.phone if partner and 'phone' in partner._fields else '') or self.company_id.partner_id.phone or ''
            cards.append(_enrich({
                "name": name,
                "address": address,
                "phone": phone,
                "email": partner.email if partner and 'email' in partner._fields else '',
                "maps_url": _map_url(name, address),
                "whatsapp_url": _whatsapp_url(phone),
            }))

        return json.dumps(
            [{k: c.get(k, '') for k in _GMAP_FIELDS} for c in cards],
            ensure_ascii=False,
        )

    def _md_invalidate_branch_cache(self):
        """Invalidar caché cuando cambien datos de sucursales."""
        self.env.registry.clear_cache()

    def get_md_organization_jsonld(self):
        """JSON-LD Organization + WebSite con la marca pública real.

        Reemplaza (vía md_organization_jsonld_override en md_bento_theme) el bloque
        genérico que inyecta website_sale.website_sale_layout, que usa
        res_company.name (nombre interno del ERP, ej. 'MDS MÉRIDA') y no incluye
        sameAs ni WebSite/SearchAction.

        Sin ormcache (a diferencia de _md_branch_cards_json): el resultado incluye
        la URL base, que debe reflejar el dominio real de la petición (mismo criterio
        que el <link rel="canonical"> ya presente en cada página) — el website.domain
        configurado en Ajustes puede apuntar a un dominio distinto (ej. producción
        futura) del que realmente se está sirviendo en este entorno.
        """
        base_url = (
            request.httprequest.url_root.rstrip("/")
            if request and request.httprequest
            else self.get_base_url()
        )
        org_id = "%s/#organization" % base_url
        org = {
            "@type": "Organization",
            "@id": org_id,
            "name": "Medicine Depot",
            "alternateName": "Medicine Depot Sureste",
            "url": base_url,
            "logo": "%s/logo.png?company=%s" % (base_url, self.company_id.id),
            # Ya publicadas y enlazadas en el footer (md_bento_theme/views/layout.xml).
            "sameAs": [
                "https://www.facebook.com/MedicineDepotMX",
                "https://www.instagram.com/medicinedepotmx/",
                "https://www.linkedin.com/company/medicine-depot/",
            ],
        }
        site = {
            "@type": "WebSite",
            "@id": "%s/#website" % base_url,
            "url": base_url,
            "name": "Medicine Depot",
            "publisher": {"@id": org_id},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": "%s/website/search?search={search_term_string}" % base_url,
                },
                "query-input": "required name=search_term_string",
            },
        }
        # Markup(): t-out escapa HTML por defecto (comillas -> &#34;), lo que
        # invalidaría el JSON dentro del <script>. El JSON ya está serializado
        # de forma segura por json.dumps, no necesita (ni debe) volver a escaparse.
        return Markup(json.dumps({"@context": "https://schema.org", "@graph": [org, site]}, ensure_ascii=False))
