# -*- coding: utf-8 -*-
"""Remove obsolete has_packages QWeb guards from delivery report views.

Studio duplicates may keep evaluating stale QWeb branches even after the
main report template is patched. This migration scans every ir.ui.view row,
patches any language payload stored in arch_db, and disables residual copy
views that are not referenced by a report action.
"""

import json
import logging

from lxml import etree

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_NEEDLE = "has_packages"
_LIKE_NEEDLE = "%has_packages%"
_JSON_TYPES = {"json", "jsonb"}


def _arch_column_type(cr):
    cr.execute(
        """
        SELECT udt_name
        FROM information_schema.columns
        WHERE table_name = 'ir_ui_view'
          AND column_name = 'arch_db'
        """
    )
    row = cr.fetchone()
    return row[0] if row and row[0] else "text"


def _report_action_refs(cr):
    cr.execute("SELECT to_regclass('ir_act_report_xml')")
    row = cr.fetchone()
    if not row or not row[0]:
        return set()

    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'ir_act_report_xml'
          AND column_name IN ('report_name', 'report_file')
        ORDER BY column_name
        """
    )
    columns = [row[0] for row in cr.fetchall()]
    if not columns:
        return set()

    select_list = ", ".join("COALESCE(%s, '')" % column for column in columns)
    cr.execute(
        """
        SELECT %s
        FROM ir_act_report_xml
        """
        % select_list
    )
    refs = set()
    for row in cr.fetchall():
        refs.update(value for value in row if value)
    return refs


def _decode_arch_payload(raw_arch, column_type):
    if isinstance(raw_arch, dict):
        return raw_arch, True
    if isinstance(raw_arch, bytes):
        raw_arch = raw_arch.decode("utf-8")
    if column_type in _JSON_TYPES and isinstance(raw_arch, str):
        try:
            return json.loads(raw_arch), True
        except ValueError:
            return raw_arch, False
    return raw_arch, False


def _remove_node(node):
    parent = node.getparent()
    if parent is None:
        patched = False
        if hasattr(node, "attrib"):
            for attr_name, attr_value in list(node.attrib.items()):
                if _NEEDLE in attr_value:
                    del node.attrib[attr_name]
                    patched = True
        if getattr(node, "text", None) and _NEEDLE in node.text:
            node.text = None
            patched = True
        return patched

    parent.remove(node)
    return True


def _patch_arch(arch):
    if not arch or _NEEDLE not in arch:
        return arch, False

    parser = etree.XMLParser(remove_blank_text=False, recover=True)
    try:
        tree = etree.fromstring(arch.encode("utf-8"), parser=parser)
    except (TypeError, ValueError, etree.XMLSyntaxError):
        # Last-resort cleanup for malformed Studio fragments: remove only
        # lines carrying the obsolete guard so the stale field is not evaluated.
        cleaned = "\n".join(
            line for line in arch.splitlines() if _NEEDLE not in line
        )
        return cleaned, cleaned != arch

    patched = False
    for xpath_expr in (
        "//comment()[contains(., 'has_packages')]",
        "//*[@*[contains(., 'has_packages')]]",
        "//*[text()[contains(., 'has_packages')]]",
    ):
        for node in list(tree.xpath(xpath_expr)):
            patched = _remove_node(node) or patched

    for node in tree.iter():
        if node.tail and _NEEDLE in node.tail:
            node.tail = node.tail.replace(_NEEDLE, "")
            patched = True

    new_arch = etree.tostring(tree, encoding="unicode")
    return new_arch, patched or new_arch != arch


def _patch_payload(raw_arch, column_type):
    payload, is_json_payload = _decode_arch_payload(raw_arch, column_type)
    if is_json_payload and isinstance(payload, dict):
        patched_payload = dict(payload)
        patched = False
        for lang, lang_arch in payload.items():
            if not isinstance(lang_arch, str):
                continue
            new_lang_arch, lang_patched = _patch_arch(lang_arch)
            if lang_patched:
                patched_payload[lang] = new_lang_arch
                patched = True
        return patched_payload, patched, True

    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if payload is None:
        payload = ""
    new_arch, patched = _patch_arch(str(payload))
    return new_arch, patched, False


def _is_residual_delivery_copy(key, name, report_refs):
    key = key or ""
    name = name or ""
    marker = "%s %s" % (key, name)
    marker_lower = marker.lower()
    if "copy" not in marker_lower:
        return False
    if "delivery_document" not in marker_lower and "report_delivery" not in marker_lower:
        return False
    return key not in report_refs and name not in report_refs


def _write_view(cr, view_id, patched_payload, is_json_payload, column_type, deactivate):
    if is_json_payload or column_type in _JSON_TYPES:
        cast_type = "jsonb" if column_type == "jsonb" else "json"
        sql = """
            UPDATE ir_ui_view
               SET arch_db = %s::%s,
                   arch_fs = NULL
        """ % ("%s", cast_type)
        if deactivate:
            sql += ", active = FALSE"
        sql += " WHERE id = %s"
        cr.execute(sql, (json.dumps(patched_payload, ensure_ascii=False), view_id))
        return

    sql = """
        UPDATE ir_ui_view
           SET arch_db = %s,
               arch_fs = NULL
    """
    if deactivate:
        sql += ", active = FALSE"
    sql += " WHERE id = %s"
    cr.execute(sql, (patched_payload, view_id))


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    column_type = _arch_column_type(cr)
    report_refs = _report_action_refs(cr)

    cr.execute(
        """
        SELECT id, COALESCE(key, ''), COALESCE(name, ''), active, arch_db
        FROM ir_ui_view
        WHERE arch_db::text ILIKE %s
        """,
        (_LIKE_NEEDLE,),
    )
    rows = cr.fetchall()

    patched_count = 0
    deactivated_count = 0
    for view_id, key, name, active, raw_arch in rows:
        patched_payload, patched, is_json_payload = _patch_payload(
            raw_arch, column_type
        )
        deactivate = bool(
            active and _is_residual_delivery_copy(key, name, report_refs)
        )
        if not patched and not deactivate:
            continue

        _write_view(
            cr, view_id, patched_payload, is_json_payload, column_type, deactivate
        )
        patched_count += 1 if patched else 0
        deactivated_count += 1 if deactivate else 0

    cr.execute(
        """
        SELECT id, COALESCE(key, ''), COALESCE(name, '')
        FROM ir_ui_view
        WHERE active IS TRUE
          AND arch_db::text ILIKE %s
        """,
        (_LIKE_NEEDLE,),
    )
    remaining = cr.fetchall()
    if remaining:
        raise RuntimeError(
            "Active QWeb views still contain has_packages after cleanup: %s"
            % ", ".join(
                "%s:%s/%s" % (view_id, key, name)
                for view_id, key, name in remaining
            )
        )

    env.registry.clear_cache()
    _logger.info(
        "pharma_reports 19.0.1.0.3: patched %d QWeb views and disabled %d "
        "residual delivery report copies containing has_packages",
        patched_count,
        deactivated_count,
    )
