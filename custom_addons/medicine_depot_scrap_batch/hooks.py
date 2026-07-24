def post_init_hook(env):
    """Corrige registros existentes cuya ubicacion de bajas no sea Virtual Locations/Scrap.
    Se ejecuta tras install y tras upgrade del modulo."""
    ScrapBatch = env['stock.scrap.batch']
    correct_loc = ScrapBatch._resolve_scrap_location()
    if not correct_loc:
        return
    wrong = ScrapBatch.search([('scrap_location_id', '!=', correct_loc.id)])
    if wrong:
        wrong.write({'scrap_location_id': correct_loc.id})
