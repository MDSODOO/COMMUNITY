# -*- coding: utf-8 -*-
import json
import re
from urllib.parse import quote_plus, urlparse
from werkzeug.utils import redirect

from odoo import _, fields
from odoo.http import Controller, request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale
from .utils import clean as _clean_val, is_valid_email as _is_valid_email_util
from ..models.pharmacovigilance import (
    PATIENT_SEX_SELECTION,
    SEVERITY_SELECTION,
    OUTCOME_SELECTION,
    REPORTER_ROLE_SELECTION,
    REPORTER_RELATIONSHIP_SELECTION,
)

class MedicineDepotPublicController(Controller):
    """Public website routes for the Bento redesign."""

    # Opciones importadas del modelo para evitar duplicación (ver 3.3)
    _PHARMACOVIGILANCE_PATIENT_SEX_OPTIONS     = PATIENT_SEX_SELECTION
    _PHARMACOVIGILANCE_SEVERITY_OPTIONS        = SEVERITY_SELECTION
    _PHARMACOVIGILANCE_OUTCOME_OPTIONS         = OUTCOME_SELECTION
    _PHARMACOVIGILANCE_REPORTER_ROLE_OPTIONS   = REPORTER_ROLE_SELECTION
    _PHARMACOVIGILANCE_RELATIONSHIP_OPTIONS    = REPORTER_RELATIONSHIP_SELECTION

    # Known coordinates for each branch (used for Google Maps integration)
    _BRANCH_COORDS = {
        "mérida":            (20.9674, -89.5926),
        "merida":            (20.9674, -89.5926),
        "ticul":             (20.3954, -89.5228),
        "campeche":          (19.8301, -90.5349),
        "cancún":            (21.1619, -86.8515),
        "cancun":            (21.1619, -86.8515),
        "chetumal":          (18.5011, -88.3018),
        "playa del carmen":  (20.6540, -87.0682),
    }

    # State key by normalized city name (for tab filtering)
    _BRANCH_STATE_KEY = {
        "mérida": "yucatan", "merida": "yucatan",
        "ticul":  "yucatan",
        "campeche": "campeche",
        "cancún": "qroo", "cancun": "qroo",
        "chetumal": "qroo",
        "playa del carmen": "qroo",
    }

    _BRANCH_CITY_LABEL = {
        "mérida": "Mérida", "merida": "Mérida",
        "ticul": "Ticul",
        "campeche": "Campeche",
        "cancún": "Cancún", "cancun": "Cancún",
        "chetumal": "Chetumal",
        "playa del carmen": "Playa del Carmen",
    }

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

    _DEFAULT_BRANCH_SCHEDULE = {
        "open": "09:00",
        "close": "19:00",
        "open_sat": "09:00",
        "close_sat": "14:00",
        "open_sun": "",
        "close_sun": "",
    }

    _FALLBACK_BRANCHES = (
        {
            "name": "Mérida",
            "address": "Calle 29 No. 218 C entre 30 y 32, Colonia Garcia Gineres, Mérida, Yucatán 97070",
        },
        {
            "name": "Ticul",
            "address": "Calle 26-A No. 201 entre 25-A y 27, Colonia Centro, Ticul, Yucatán 97860",
        },
        {
            "name": "Campeche",
            "address": "Av. José López Portillo #231, Colonia San Rafael, San Francisco de Campeche, Campeche 24090",
        },
        {
            "name": "Cancún",
            "address": "Av. Palenque Lote 40 Mz. 4, entre 6 y 10 Poniente, Cancún, Quintana Roo 77520",
        },
        {
            "name": "Chetumal",
            "address": "Av. Independencia No. 94, Colonia Centro, Chetumal, Quintana Roo 77000",
        },
        {
            "name": "Playa del Carmen",
            "address": "Calle 34 Bis, Mz 165 Lote 5 y 6 Norte, Colonia Sac-Pacal, Playa del Carmen, Quintana Roo 77710",
        },
    )

    _FALLBACK_POSTS = (
        {
            "name": "Descubre cómo el deporte puede ser una oportunidad de negocio",
            "category": "Mi Farmacia",
            "summary": "Una estrategia eficaz para incrementar tu clientela y los beneficios de tu farmacia.",
            "url": "/blog",
            "date": "11/06/2024",
        },
        {
            "name": "Mejora la atención al cliente con estos tips",
            "category": "Mi Farmacia",
            "summary": "La tecnología es un elemento fundamental en el día a día de una farmacia mejor organizada.",
            "url": "/blog",
            "date": "05/03/2024",
        },
        {
            "name": "8 tips para mejorar la comunicación con los clientes mayores",
            "category": "Mi Farmacia",
            "summary": "Aprende a abordar y vender a adultos mayores con una comunicación más clara y cercana.",
            "url": "/blog",
            "date": "18/01/2024",
        },
    )

    _MENU_URL_CANONICAL = {
        "https://medicinedepot.com.mx/medicd/": "https://medicinedepot.com.mx/medicd/",
        "https://forms.gle/FJu6zr96Eu7EyB639": "/farmacovigilancia",
        "https://docs.google.com/forms/d/e/1FAIpQLSc9-Jj-g0p66gffeZmB0HSab9_YdG01_BhYmpa3fBH9oU2NJA/viewform": "/farmacovigilancia",
        "/contactanos": "/contactus",
    }

    def _canonicalize_menu_url(self, url):
        clean = (url or "").strip()
        if not clean:
            return clean
        if clean in self._MENU_URL_CANONICAL:
            return self._MENU_URL_CANONICAL[clean]
        if clean.startswith("/contactanos"):
            return "/contactus"
        if clean.startswith("/"):
            return clean

        parsed = urlparse(clean)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").rstrip("/")

        if host in ("medicinedepot.com.mx", "www.medicinedepot.com.mx") and path.endswith("/medicd"):
            return "/medicd"
        if host == "forms.gle" or "docs.google.com" in host:
            return "/farmacovigilancia"
        return clean

    def _company_partner(self):
        """Devuelve el partner de la compañía activa en el website, con fallback al usuario actual."""
        website = request.website.sudo() if request.website else False
        company = website.company_id.sudo() if website and website.company_id else request.env.company.sudo()
        return company.partner_id.sudo() if company and company.partner_id else request.env.user.partner_id.sudo()

    def _nav_items(self, active_route):
        items = []

        website = request.website
        root_menu = False
        if website:
            root_menu = request.env["website.menu"].sudo().search(
                [("url", "=", "/default-main-menu"), ("website_id", "=", website.id)],
                limit=1,
            )
        if root_menu:
            Menu = request.env["website.menu"].sudo()
            domain = [("parent_id", "=", root_menu.id)]
            if website:
                domain = ["|", ("website_id", "=", False), ("website_id", "=", website.id)] + domain
            menu_items = Menu.search(domain, order="sequence,id")
            for menu in menu_items:
                url = menu.page_id.url if "page_id" in menu._fields and menu.page_id else menu.url or ""
                if not url:
                    continue
                url = self._canonicalize_menu_url(url)
                items.append(
                    {
                        "label": menu.name,
                        "url": url,
                        "cta": url == "/contactus",
                    }
                )

        if not items:
            items = [
                {"label": _("Inicio"), "url": "/"},
                {"label": _("Afiliación"), "url": "/afiliacion"},
                {"label": _("MedicD"), "url": "https://medicinedepot.com.mx/medicd/"},
                {"label": _("Sucursales"), "url": "/sucursales"},
                {"label": _("Farmacovigilancia"), "url": "/farmacovigilancia"},
                {"label": _("Blog"), "url": "/blog"},
                {"label": _("Contacto"), "url": "/contactus", "cta": True},
            ]

        for item in items:
            item["active"] = active_route == item["url"]
        return items

    def _company_contact_values(self):
        partner = self._company_partner()
        return {
            "name": partner.name or "MedicineDepot",
            "phone": partner.phone or "",
            "email": partner.email or "",
            "website": partner.website or "",
        }

    def _format_partner_address(self, partner):
        parts = []
        for field_name in ("street", "street2", "city", "state_id", "zip", "country_id"):
            if field_name not in partner._fields:
                continue
            value = partner[field_name]
            if not value:
                continue
            if field_name in ("state_id", "country_id"):
                value = value.name
            parts.append(str(value).strip())
        return ", ".join(part for part in parts if part)

    def _branch_map_url(self, name, address):
        query = " ".join(part for part in (name, address) if part)
        return "https://www.google.com/maps/search/?api=1&query=%s" % quote_plus(query)

    def _branch_official_map_url(self, key, name, address):
        return self._BRANCH_MAP_URLS.get(key) or self._branch_map_url(name, address)

    def _whatsapp_url(self, phone):
        digits = re.sub(r"\D+", "", phone or "")
        return "https://wa.me/%s" % digits if digits else ""

    # Common warehouse name prefixes to strip before coord/state lookups
    _NAME_PREFIXES = ("mds ", "md ", "medicine depot ", "medicine depot sureste ", "farmacia ")

    def _normalize_branch_key(self, name):
        """Lowercase + strip company prefixes so 'MDS MERIDA' → 'merida'."""
        key = name.lower().strip()
        for prefix in self._NAME_PREFIXES:
            if key.startswith(prefix):
                key = key[len(prefix):]
                break
        return key.strip()

    def _enrich_branch(self, card):
        """Add lat/lng + state_key + city to a branch card dict."""
        key = self._normalize_branch_key(card["name"])
        lat, lng = self._BRANCH_COORDS.get(key, (0.0, 0.0))
        schedule = dict(self._DEFAULT_BRANCH_SCHEDULE)
        card["lat"] = lat
        card["lng"] = lng
        card["city"] = self._BRANCH_CITY_LABEL.get(key, card["name"])
        card["state_key"] = self._BRANCH_STATE_KEY.get(key, "")
        card["open_time"] = schedule["open"]
        card["close_time"] = schedule["close"]
        card["open_sat"] = schedule["open_sat"]
        card["close_sat"] = schedule["close_sat"]
        card["open_sun"] = schedule["open_sun"]
        card["close_sun"] = schedule["close_sun"]
        card["hours_weekday_label"] = "%s - %s" % (schedule["open"], schedule["close"])
        card["hours_sat_label"] = (
            "%s - %s" % (schedule["open_sat"], schedule["close_sat"])
            if schedule.get("open_sat") and schedule.get("close_sat")
            else ""
        )
        card["hours_sun_label"] = (
            "%s - %s" % (schedule["open_sun"], schedule["close_sun"])
            if schedule.get("open_sun") and schedule.get("close_sun")
            else ""
        )
        return card

    def _get_branch_cards(self):
        Warehouse = request.env["stock.warehouse"].sudo()
        warehouses = Warehouse.search([("active", "=", True)], order="sequence,id")
        cards = []
        for warehouse in warehouses:
            partner = warehouse.partner_id.sudo() if "partner_id" in warehouse._fields and warehouse.partner_id else False
            name = warehouse.display_name or warehouse.name or _("Sucursal")
            address = self._format_partner_address(partner) if partner else ""
            if not address:
                fallback = self._FALLBACK_BRANCHES[len(cards) % len(self._FALLBACK_BRANCHES)]
                address = fallback["address"]
            key = self._normalize_branch_key(name)
            phone = (partner.phone if partner and "phone" in partner._fields else "") or self._company_partner().phone or ""
            card = {
                "name": name,
                "address": address,
                "phone": phone,
                "email": partner.email if partner and "email" in partner._fields else "",
                "maps_url": self._branch_official_map_url(key, name, address),
                "whatsapp_url": self._whatsapp_url(phone),
            }
            cards.append(self._enrich_branch(card))

        if cards:
            return cards

        return [
            self._enrich_branch({
                "name": branch["name"],
                "address": branch["address"],
                "phone": "",
                "email": "",
                "maps_url": self._branch_official_map_url(
                    self._normalize_branch_key(branch["name"]),
                    branch["name"],
                    branch["address"],
                ),
                "whatsapp_url": "",
            })
            for branch in self._FALLBACK_BRANCHES
        ]

    def _get_featured_posts(self, limit=3):
        if "blog.post" not in request.registry.models:
            return list(self._FALLBACK_POSTS[:limit])

        Post = request.env["blog.post"].sudo()
        domain = [("is_published", "=", True)]
        if "website_id" in Post._fields and request.website:
            domain = ["|", ("website_id", "=", False), ("website_id", "=", request.website.id)] + domain
        posts = Post.search(domain, order="post_date desc,id desc", limit=limit)
        if posts:
            featured = []
            for post in posts:
                summary = post.subtitle or post.name
                featured.append({
                    "name": post.name,
                    "category": post.blog_id.name if "blog_id" in post._fields and post.blog_id else _("Blog"),
                    "summary": summary,
                    "url": post.website_url or "/blog",
                    "date": post.post_date.strftime("%d/%m/%Y") if getattr(post, "post_date", False) else "",
                })
            return featured
        return list(self._FALLBACK_POSTS[:limit])

    def _is_valid_email(self, email):
        return _is_valid_email_util(email)

    def _pharmacovigilance_context(self):
        partner = request.env.user.partner_id.sudo() if request.env.user and not request.env.user._is_public() else False
        reporter_name = partner.name if partner else ""
        reporter_email = partner.email if partner else ""
        reporter_phone = partner.phone if partner else ""
        return {
            "pharmacovigilance_steps": [
                {"number": "01", "label": _("Paciente"), "hint": _("Datos básicos")},
                {"number": "02", "label": _("Evento"), "hint": _("Qué sucedió")},
                {"number": "03", "label": _("Medicamento"), "hint": _("Producto sospechoso")},
                {"number": "04", "label": _("Estado"), "hint": _("Antecedentes y evolución")},
                {"number": "05", "label": _("Concomitantes"), "hint": _("Medicamentos actuales")},
                {"number": "06", "label": _("Notificador"), "hint": _("Consentimiento y envío")},
            ],
            "pharmacovigilance_options": {
                "patient_sex_options": self._PHARMACOVIGILANCE_PATIENT_SEX_OPTIONS,
                "severity_options": self._PHARMACOVIGILANCE_SEVERITY_OPTIONS,
                "outcome_options": self._PHARMACOVIGILANCE_OUTCOME_OPTIONS,
                "reporter_role_options": self._PHARMACOVIGILANCE_REPORTER_ROLE_OPTIONS,
                "relationship_options": self._PHARMACOVIGILANCE_RELATIONSHIP_OPTIONS,
            },
            "pharmacovigilance_defaults": {
                "reporter_name": reporter_name,
                "reporter_email": reporter_email,
                "reporter_phone": reporter_phone,
            },
        }

    def _validate_pharmacovigilance_post(self, post):
        errors = []
        required = {
            "patient_name": _("El nombre del paciente es obligatorio."),
            "event_description": _("Describe el evento adverso."),
            "event_severity": _("Selecciona la gravedad del evento."),
            "suspected_product_name": _("El producto sospechoso es obligatorio."),
            "reporter_name": _("El nombre del notificador es obligatorio."),
            "reporter_email": _("El correo del notificador es obligatorio."),
            "reporter_role": _("Selecciona el perfil del notificador."),
            "reporter_relationship": _("Selecciona la relación con el paciente."),
        }
        for key, message in required.items():
            if not (post.get(key) or "").strip():
                errors.append(message)

        email = (post.get("reporter_email") or "").strip()
        if email and not self._is_valid_email(email):
            errors.append(_("El correo del notificador no tiene un formato válido."))

        if not post.get("consent"):
            errors.append(_("Debes aceptar el aviso de privacidad para continuar."))

        valid_sets = {
            "patient_sex": {value for value, _label in self._PHARMACOVIGILANCE_PATIENT_SEX_OPTIONS},
            "event_severity": {value for value, _label in self._PHARMACOVIGILANCE_SEVERITY_OPTIONS},
            "event_outcome": {value for value, _label in self._PHARMACOVIGILANCE_OUTCOME_OPTIONS},
            "reporter_role": {value for value, _label in self._PHARMACOVIGILANCE_REPORTER_ROLE_OPTIONS},
            "reporter_relationship": {value for value, _label in self._PHARMACOVIGILANCE_RELATIONSHIP_OPTIONS},
        }
        friendly_names = {
            "patient_sex": _("sexo del paciente"),
            "event_severity": _("gravedad"),
            "event_outcome": _("evolución"),
            "reporter_role": _("perfil del notificador"),
            "reporter_relationship": _("relación con el paciente"),
        }
        for field_name, allowed in valid_sets.items():
            value = (post.get(field_name) or "").strip()
            if value and value not in allowed:
                errors.append(_("Valor inválido para %(field)s.", field=friendly_names.get(field_name, field_name)))

        age = (post.get("patient_age") or "").strip()
        if age and not age.isdigit():
            errors.append(_("La edad del paciente debe ser un número entero."))

        event_date = (post.get("event_date") or "").strip()
        if event_date:
            try:
                fields.Date.to_date(event_date)
            except Exception:
                errors.append(_("La fecha del evento no tiene un formato válido."))

        if post.get("md_hp_field"):
            errors.append(_("Solicitud no válida."))

        return errors

    def _pharmacovigilance_report_vals(self, post):
        def _clean(key):
            return _clean_val(post, key)

        event_date = _clean("event_date")
        if event_date:
            event_date = fields.Date.to_date(event_date)

        vals = {
            "patient_name": _clean("patient_name"),
            "patient_age": int(_clean("patient_age")) if _clean("patient_age").isdigit() else False,
            "patient_sex": _clean("patient_sex"),
            "patient_city": _clean("patient_city"),
            "event_date": event_date or False,
            "event_severity": _clean("event_severity"),
            "event_outcome": _clean("event_outcome") or "unknown",
            "event_description": _clean("event_description"),
            "suspected_product_name": _clean("suspected_product_name"),
            "suspected_product_presentation": _clean("suspected_product_presentation"),
            "suspected_batch": _clean("suspected_batch"),
            "suspected_dose": _clean("suspected_dose"),
            "medical_history": _clean("medical_history"),
            "current_condition": _clean("current_condition"),
            "concomitant_medication": _clean("concomitant_medication"),
            "reporter_name": _clean("reporter_name"),
            "reporter_role": _clean("reporter_role"),
            "reporter_relationship": _clean("reporter_relationship"),
            "reporter_email": _clean("reporter_email"),
            "reporter_phone": _clean("reporter_phone"),
            "consent": bool(_clean("consent")),
            "notes": _clean("notes"),
        }
        if request.website:
            vals["website_id"] = request.website.id
            if request.website.company_id:
                vals["company_id"] = request.website.company_id.id
        return vals

    def _public_context(self, active_route):
        branch_cards = self._get_branch_cards()
        website = request.website
        if website:
            branch_cards_json = website._md_branch_cards_json()
        else:
            _gmap_fields = ("name", "address", "phone", "whatsapp_url", "maps_url", "lat", "lng", "state_key", "city")
            branch_cards_json = json.dumps(
                [{k: b.get(k, "") for k in _gmap_fields} for b in branch_cards],
                ensure_ascii=False,
            )
        return {
            "company": self._company_contact_values(),
            "nav_items": self._nav_items(active_route),
            "branch_cards": branch_cards,
            "branch_cards_json": branch_cards_json,
            "featured_posts": self._get_featured_posts(),
            "active_route": active_route,
        }

    @route(["/", "/home"], type="http", auth="public", website=True, sitemap=True)
    def home(self, **kw):
        return request.render("medicine_depot_portal.public_home_page", self._public_context("/"))

    @route(["/sucursales", "/sucursal"], type="http", auth="public", website=True, sitemap=True)
    def branches(self, **kw):
        return request.render("medicine_depot_portal.public_branches_page", self._public_context("/sucursales"))

    @route(["/shop/compare"], type="http", auth="public", website=True, sitemap=False)
    def shop_compare_alias(self, **kw):
        # Alias defensivo cuando website_sale_comparison no está activo.
        return redirect("/shop")

    @route(["/my/picking"], type="http", auth="user", website=True, sitemap=False)
    def portal_picking_alias(self, **kw):
        return redirect("/my/pickings")

    @route(["/my/documents"], type="http", auth="user", website=True, sitemap=False)
    def portal_documents_alias(self, **kw):
        return redirect("/odoo/documents_portal")

    def _has_view(self, xmlid):
        try:
            request.env.ref(xmlid)
        except ValueError:
            return False
        return True

    def _render_public_page(self, xmlid, active_route, fallback_xmlid="medicine_depot_portal.public_home_page"):
        context = self._public_context(active_route)
        if self._has_view(xmlid):
            return request.render(xmlid, context)
        return request.render(fallback_xmlid, self._public_context("/"))

    @route(["/medicd"], type="http", auth="public", website=True, sitemap=True)
    def medicd(self, **kw):
        return redirect("https://medicinedepot.com.mx/medicd/")

    @route(["/contactanos"], type="http", auth="public", website=True, sitemap=True)
    def contact_legacy(self, **kw):
        # Alias estable para campañas históricas y enlaces existentes.
        return self._render_public_page("medicine_depot_portal.contact_page_view", "/contactus")

    @route(["/contactus"], type="http", auth="public", website=True, sitemap=True)
    def contactus(self, **kw):
        # Unificamos la ruta canónica de contacto público.
        if self._has_view("medicine_depot_portal.contact_page_view"):
            return self._render_public_page("medicine_depot_portal.contact_page_view", "/contactus")
        return self._render_public_page("medicine_depot_portal.complaint_page_view", "/contactus")

    @route(["/contacto-quejas"], type="http", auth="public", website=True, sitemap=True)
    def complaints(self, **kw):
        if self._has_view("medicine_depot_portal.complaint_page_view"):
            return self._render_public_page("medicine_depot_portal.complaint_page_view", "/contactus")
        return self._render_public_page("medicine_depot_portal.contact_page_view", "/contactus")

    @route(["/farmacovigilancia"], type="http", auth="public", website=True, sitemap=True, methods=["GET", "POST"])
    def pharmacovigilance(self, **post):
        context = self._public_context("/farmacovigilancia")
        context.update(self._pharmacovigilance_context())

        if request.httprequest.method != "POST":
            return request.render("medicine_depot_portal.public_pharmacovigilance_page", context)

        validation_errors = self._validate_pharmacovigilance_post(post)
        if validation_errors:
            return request.make_json_response(
                {"success": False, "message": " ".join(validation_errors)},
                status=400,
            )

        report_vals = self._pharmacovigilance_report_vals(post)
        try:
            report = request.env["medicine.depot.pharmacovigilance.report"].sudo().create(report_vals)
        except Exception:
            return request.make_json_response(
                {"success": False, "message": _("Ocurrió un error inesperado al registrar el reporte.")},
                status=500,
            )
        return request.make_json_response(
            {
                "success": True,
                "message": _("Reporte recibido correctamente."),
                "reference": report.name,
            }
        )

    # /contactanos y /contactus se resuelven por rutas explícitas para evitar drift de website.page.


class WebsiteSaleShopAccess(WebsiteSale):

    @route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True, sitemap=False)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        if request.env.user._is_public():
            return request.render("medicine_depot_portal.md_shop_access_restricted", {})
        return super().shop(page=page, category=category, search=search, min_price=min_price, max_price=max_price, ppg=ppg, **post)

