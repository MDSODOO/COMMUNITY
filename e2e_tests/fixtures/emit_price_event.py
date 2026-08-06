# Dispara cambios de precio REALES por el camino de produccion
# (_notify_price_changes), no un bus._sendone falso: asi la prueba cubre
# tambien la construccion del payload y el ruteo por canal res.partner.
#
# Uso:  odoo shell ... < emit_price_event.py
#   COUNT=n  -> cuantas lineas alterar (default 1)
import os

count = int(os.environ.get("COUNT", "1"))

po = env["purchase.order"].search(
    [("state", "in", ("purchase", "done")), ("order_line", "!=", False)],
    limit=1,
)
if not po:
    print("RESULT:NO_PO")
else:
    lines = po.order_line.filtered(lambda l: l.product_id and l.price_unit)[:count]
    if not lines:
        print("RESULT:NO_LINES")
    else:
        # old_prices simula el snapshot de supplierinfo previo: -20% respecto
        # al precio actual de la linea => se detecta como subida del +25%.
        old_prices = {
            l.product_id.product_tmpl_id.id: l.price_unit * 0.8 for l in lines
        }
        before = env["purchase.price.notification"].search([]).ids
        env["purchase.invoice.import.wizard"]._notify_price_changes(
            po, po.company_id, old_prices, lines=lines
        )
        env.cr.commit()
        after = env["purchase.price.notification"].search([]).ids
        created = [i for i in after if i not in before]
        print("RESULT:CREATED:%s" % ",".join(str(i) for i in created))
