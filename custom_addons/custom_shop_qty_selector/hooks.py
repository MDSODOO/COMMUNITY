"""Install/uninstall hooks for custom_shop_qty_selector.

Las ACLs publicas para los modelos Studio `x_active_ingredient` y
`x_line` no pueden cargarse via XML de datos porque el atributo
``search=[('model','=',...)]`` del campo ``model_id`` devuelve vacio
si el modelo Studio no existe en la DB destino. Resultado: el
registro ``ir.model.access`` se intenta crear con ``model_id=NULL``
violando el NOT NULL constraint y abortando el rebuild.

Este hook crea las ACLs solo si el modelo Studio existe — el modulo
queda instalable en DBs donde nunca se publicaron esas
customizaciones Studio (filtros y eyebrow simplemente no aparecen
en /shop, comportamiento ya esperado por los controllers/models).
"""

STUDIO_MODELS = ('x_active_ingredient', 'x_line')
_MODULE = 'custom_shop_qty_selector'


def _post_init_create_studio_acls(env):
    """Crea ir.model.access publica (read) por cada modelo Studio presente."""
    IrModel = env['ir.model'].sudo()
    IrModelData = env['ir.model.data'].sudo()
    AccessModel = env['ir.model.access'].sudo()

    for studio_model in STUDIO_MODELS:
        model_rec = IrModel.search([('model', '=', studio_model)], limit=1)
        if not model_rec:
            continue

        xmlid_name = f'access_{studio_model}_public_read'
        full_xmlid = f'{_MODULE}.{xmlid_name}'
        if env.ref(full_xmlid, raise_if_not_found=False):
            continue

        acl = AccessModel.create({
            'name': f'{studio_model} public read',
            'model_id': model_rec.id,
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })
        IrModelData.create({
            'name': xmlid_name,
            'module': _MODULE,
            'model': 'ir.model.access',
            'res_id': acl.id,
            'noupdate': True,
        })


def _uninstall_cleanup_studio_acls(env):
    """Limpieza explicita por seguridad — Odoo ya las elimina via ir.model.data."""
    for studio_model in STUDIO_MODELS:
        record = env.ref(
            f'{_MODULE}.access_{studio_model}_public_read',
            raise_if_not_found=False,
        )
        if record:
            record.sudo().unlink()
