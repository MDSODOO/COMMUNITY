#!/usr/bin/env python3
"""
update_prices.py

Sincroniza precios (list_price, standard_price) desde la base restaurada en
Odoo.sh (fuente / source) hacia la base 'dev' autohospedada (destino / target),
emparejando productos por codigo de barras (barcode).

Si un barcode existe en la fuente pero no tiene producto correspondiente en
el destino, se crea el producto en destino con: name, barcode, default_code,
uom_id (mapeado por nombre, con 'Units' como respaldo), list_price y
standard_price. La categoria (categ_id) NO se copia de la fuente -- decision
explicita del usuario -- se deja que Odoo aplique su categoria por defecto.

No se filtra por cantidad fisica ('A la mano' / On Hand): se procesa el
catalogo completo, tal como se acordo con el usuario.

Decisiones que generaron este script (2026-07-27, via interaccion con el usuario):
  - Fuente: medicinedepot-test-35511442.dev.odoo.com (base restaurada Odoo.sh).
  - Destino: dev autohospedado en este servidor (localhost:8069, db medicinedepot_dev).
  - Llave de match: barcode (verificado sin duplicados en ninguna de las 2 bases).
  - Campos a actualizar: list_price y standard_price (ambos).
  - Filtro por 'A la mano' (On Hand): ninguno, aplica a todo el catalogo.
  - Barcodes sin match en destino: SI crear el producto (no solo reportar).
  - Campos a copiar al crear: name, default_code, uom_id (no categ_id).
"""
import os
import sys
import xmlrpc.client


def _require_env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(
            "Falta variable de entorno / Missing environment variable: {}\n"
            "Carga las credenciales antes de correr el script, ej.:\n"
            "  set -a; source .env.price_sync; set +a; python3 scripts/update_prices.py".format(name)
        )
    return value


SOURCE = {
    "url": _require_env("SRC_URL"),
    "db": _require_env("SRC_DB"),
    "user": _require_env("SRC_USER"),
    "password": _require_env("SRC_PASSWORD"),
}

TARGET = {
    "url": _require_env("TGT_URL"),
    "db": _require_env("TGT_DB"),
    "user": _require_env("TGT_USER"),
    "password": _require_env("TGT_PASSWORD"),
}

FALLBACK_UOM_NAME = "Units"


def connect(cfg):
    common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(cfg["url"]))
    uid = common.authenticate(cfg["db"], cfg["user"], cfg["password"], {})
    if not uid:
        raise RuntimeError("Autenticacion fallida / Authentication failed: {}".format(cfg["url"]))
    models = xmlrpc.client.ServerProxy("{}/xmlrpc/2/object".format(cfg["url"]))
    return uid, models


def main():
    src_uid, src_models = connect(SOURCE)
    tgt_uid, tgt_models = connect(TARGET)

    # 1. Leer catalogo completo de la fuente con codigo de barras
    source_products = src_models.execute_kw(
        SOURCE["db"], src_uid, SOURCE["password"],
        "product.template", "search_read",
        [[("barcode", "!=", False)]],
        {"fields": ["name", "barcode", "default_code", "list_price", "standard_price", "uom_id"]},
    )
    print("Fuente / Source: {} productos con barcode.".format(len(source_products)))

    # 2. Mapear productos existentes en destino por barcode
    target_products = tgt_models.execute_kw(
        TARGET["db"], tgt_uid, TARGET["password"],
        "product.template", "search_read",
        [[("barcode", "!=", False)]],
        {"fields": ["barcode", "list_price", "standard_price"]},
    )
    target_by_barcode = {p["barcode"]: p for p in target_products}
    print("Destino / Target: {} productos con barcode.".format(len(target_products)))

    # 3. Mapear unidades de medida del destino por nombre (para creaciones)
    target_uoms = tgt_models.execute_kw(
        TARGET["db"], tgt_uid, TARGET["password"],
        "uom.uom", "search_read", [[]], {"fields": ["name"]},
    )
    uom_by_name = {u["name"].strip().lower(): u["id"] for u in target_uoms}
    fallback_uom_id = uom_by_name.get(FALLBACK_UOM_NAME.strip().lower())

    updated, created, skipped = [], [], []

    for sp in source_products:
        barcode = sp["barcode"]
        match = target_by_barcode.get(barcode)

        if match:
            old_list = match["list_price"]
            old_std = match["standard_price"]
            new_list = sp["list_price"]
            new_std = sp["standard_price"]

            if old_list == new_list and old_std == new_std:
                continue  # sin cambios / no changes

            tgt_models.execute_kw(
                TARGET["db"], tgt_uid, TARGET["password"],
                "product.template", "write",
                [[match["id"]], {"list_price": new_list, "standard_price": new_std}],
            )
            updated.append((match["id"], sp["name"], old_list, new_list, old_std, new_std))
            print(
                "ACTUALIZADO id={} '{}' | list_price: {} -> {} | standard_price: {} -> {}".format(
                    match["id"], sp["name"], old_list, new_list, old_std, new_std
                )
            )
        else:
            uom_name = (sp["uom_id"][1] if sp["uom_id"] else "").strip().lower()
            uom_id = uom_by_name.get(uom_name, fallback_uom_id)
            if not uom_id:
                skipped.append((barcode, sp["name"], "sin UoM valida en destino / no valid UoM in target"))
                print("OMITIDO barcode={} '{}': no se encontro UoM valida en destino.".format(barcode, sp["name"]))
                continue

            new_id = tgt_models.execute_kw(
                TARGET["db"], tgt_uid, TARGET["password"],
                "product.template", "create",
                [{
                    "name": sp["name"],
                    "barcode": barcode,
                    "default_code": sp["default_code"],
                    "uom_id": uom_id,
                    "type": "consu",
                    "is_storable": True,
                    "list_price": sp["list_price"],
                    "standard_price": sp["standard_price"],
                }],
            )
            created.append((new_id, sp["name"], barcode, sp["list_price"], sp["standard_price"]))
            print(
                "CREADO id={} '{}' barcode={} | list_price={} standard_price={}".format(
                    new_id, sp["name"], barcode, sp["list_price"], sp["standard_price"]
                )
            )

    print("\n--- Resumen / Summary ---")
    print("Actualizados / Updated: {}".format(len(updated)))
    print("Creados / Created: {}".format(len(created)))
    print("Omitidos / Skipped: {}".format(len(skipped)))


if __name__ == "__main__":
    main()
