# -*- coding: utf-8 -*-
import re
from markupsafe import escape
from odoo.tools import email_normalize


def clean(post, key):
    """Extrae, limpia y escapa HTML de un campo de un dict POST."""
    val = (post.get(key) or '').strip()
    return str(escape(val)) if val else ''


def is_valid_email(email):
    """Valida formato de email. Usa tools.email_normalize cuando está disponible."""
    normalized = email_normalize(email or '')
    if normalized:
        return True
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email or ''))
