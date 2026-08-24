"""Fusiona partners duplicados (res.partner, mismo vat/RFC activo).

Pensado para correr vía `odoo shell -d medicinedepot_migration_clean`
(nunca contra medicinedepot_dev ni Odoo.sh). `env` ya viene ligado al
shell de Odoo.

Regla de negocio (confirmada por el usuario 2026-08-13, mismo proceso ya
validado en medicinedepot_dev el 2026-08-10 para Quifamesa/Brudifarma):
  - Se agrupa por vat entre partners activos.
  - Gana el registro con MÁS account.move asociados (empate: menor id).
  - Se fusiona con el wizard nativo de Odoo (base.partner.merge.automatic
    .wizard / action_merge) -- NUNCA UPDATE SQL a mano -- porque Odoo
    reasigna correctamente TODAS las relaciones (facturas, conciliaciones,
    mensajes, seguidores, etc.), no solo las que se nos ocurra listar.
  - El wizard ya archiva (active=False) a los perdedores por sí mismo;
    nunca se usa unlink.

Modo dry-run por defecto (MD_DEDUP_DRY_RUN=1): solo imprime el plan y las
verificaciones de conteo, sin llamar action_merge. Para ejecutar de
verdad: MD_DEDUP_DRY_RUN=0.

Correcciones tras el primer intento real (2026-08-13):
  - Se excluyen los RFC genéricos del SAT para "público en general"
    (XAXX010101000 persona física, XEXX010101000 extranjeros): NO son
    una entidad duplicada, son N clientes distintos que comparten el
    mismo RFC placeholder por convención fiscal -- fusionarlos mezclaría
    el historial de empresas/personas completamente distintas.
  - El wizard de Odoo no permite fusionar más de 3 contactos a la vez
    ("For safety reasons..."). Varios de los grupos reales tienen más
    de 2 perdedores, así que se fusiona en lotes de hasta 2 perdedores
    por llamada, repitiendo hasta absorber a todos.
  - Algunos "duplicados" resultaron ser direcciones hijas legítimas
    (type='delivery'/'invoice', parent_id apuntando a otro miembro del
    mismo grupo) que heredaron el mismo vat del padre al crearse -- NO
    son duplicados, son estructura normal de Odoo. Se detectan y se
    excluyen del merge (quedan tal cual, activos, sin tocar).
"""
import os

DRY_RUN = os.environ.get("MD_DEDUP_DRY_RUN", "1") != "0"

GENERIC_VAT_EXCLUDE = {"XAXX010101000", "XEXX010101000"}

MODELS_TO_CHECK = [
    "account.move",
    "purchase.order",
    "sale.order",
    "stock.picking",
    "account.payment",
    "pos.order",
]

MERGE_CHUNK_SIZE = 2  # wizard admite máx. 3 contactos por llamada (1 ganador + 2 perdedores)


def count_refs(partner_id):
    counts = {}
    for model in MODELS_TO_CHECK:
        try:
            counts[model] = env[model].search_count([("partner_id", "=", partner_id)])
        except KeyError:
            counts[model] = None  # modelo no instalado en esta BD
    return counts


def find_duplicate_groups():
    partners = env["res.partner"].search([("vat", "!=", False), ("active", "=", True)])
    by_vat = {}
    for p in partners:
        if not p.vat or p.vat.upper() in GENERIC_VAT_EXCLUDE:
            continue
        by_vat.setdefault(p.vat, []).append(p)
    return {vat: recs for vat, recs in by_vat.items() if len(recs) > 1}


def pick_winner(records):
    ranked = sorted(
        records,
        key=lambda p: (-env["account.move"].search_count([("partner_id", "=", p.id)]), p.id),
    )
    return ranked[0], ranked[1:]


def split_children_in_group(records):
    """Separa hijos legítimos (parent_id apunta a otro miembro del mismo
    grupo) del resto -- esos no son duplicados, no se tocan."""
    ids_in_group = {r.id for r in records}
    children, mergeable = [], []
    for r in records:
        if r.parent_id and r.parent_id.id in ids_in_group:
            children.append(r)
        else:
            mergeable.append(r)
    return mergeable, children


def main():
    groups = find_duplicate_groups()
    print(f"=== {'DRY-RUN' if DRY_RUN else 'EJECUCIÓN REAL'}: {len(groups)} grupos de vat duplicado ===\n")

    total_merged = 0
    total_children_skipped = 0
    skipped_groups = []
    for vat, all_records in groups.items():
        mergeable, children = split_children_in_group(all_records)
        if children:
            print(f"--- VAT {vat}: {len(children)} dirección(es) hija(s) detectada(s), NO se tocan ---")
            for child in children:
                print(f"  (hijo, se deja igual) id={child.id} '{child.name}' parent_id={child.parent_id.id}")
            total_children_skipped += len(children)

        if len(mergeable) < 2:
            if children:
                print("  Sin duplicados reales que fusionar en este grupo tras excluir hijos.\n")
            continue

        winner, losers = pick_winner(mergeable)
        winner_before = count_refs(winner.id)
        losers_before = [(loser, count_refs(loser.id)) for loser in losers]

        expected_after = dict(winner_before)
        for _, before in losers_before:
            for model, n in before.items():
                if n is not None:
                    expected_after[model] = (expected_after[model] or 0) + n

        print(f"--- VAT {vat} ---")
        print(f"  Ganador: id={winner.id} '{winner.name}' {winner_before}")
        for loser, before in losers_before:
            print(f"  Perdedor: id={loser.id} '{loser.name}' {before}")
        print(f"  Esperado en ganador tras fusión: {expected_after}")

        if not DRY_RUN:
            savepoint = env.cr.savepoint()
            try:
                loser_ids = [loser.id for loser in losers]
                for i in range(0, len(loser_ids), MERGE_CHUNK_SIZE):
                    chunk = loser_ids[i : i + MERGE_CHUNK_SIZE]
                    wizard = env["base.partner.merge.automatic.wizard"].create(
                        {
                            "partner_ids": [(6, 0, [winner.id] + chunk)],
                            "dst_partner_id": winner.id,
                        }
                    )
                    wizard.action_merge()

                winner_after = count_refs(winner.id)
                mismatches = {
                    model: (expected_after[model], winner_after[model])
                    for model in MODELS_TO_CHECK
                    if expected_after[model] is not None and expected_after[model] != winner_after[model]
                }
                if mismatches:
                    print(f"  *** DESAJUSTE tras fusionar: {mismatches} -- REVISAR A MANO, se revierte este grupo ***")
                    savepoint.rollback()
                    skipped_groups.append((vat, "desajuste de conteos tras fusionar"))
                else:
                    savepoint.close()
                    env.cr.commit()
                    print(f"  OK -- conteos verificados tras fusión: {winner_after} (commiteado)")
                    total_merged += len(losers)
            except Exception as exc:  # noqa: BLE001 -- casos reales heterogéneos, no abortar el lote completo
                savepoint.rollback()
                print(f"  *** ERROR al fusionar, se revierte SOLO este grupo: {exc} ***")
                skipped_groups.append((vat, str(exc)))
        else:
            total_merged += len(losers)

        print()

    print(
        f"=== Total: {len(groups)} grupos, {total_merged} partners fusionados/archivados, "
        f"{total_children_skipped} direcciones hijas detectadas y NO tocadas, "
        f"{len(skipped_groups)} grupo(s) con error (revisión manual) ==="
    )
    if skipped_groups:
        print("Grupos que necesitan revisión manual:")
        for vat, reason in skipped_groups:
            print(f"  - VAT {vat}: {reason}")
    if DRY_RUN:
        print("(dry-run -- no se modificó nada; correr con MD_DEDUP_DRY_RUN=0 para ejecutar de verdad)")
    else:
        print("Cada grupo exitoso ya quedó commiteado individualmente.")


main()
