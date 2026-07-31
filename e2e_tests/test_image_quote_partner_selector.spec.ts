import { test, expect } from '@playwright/test';
import { fixture } from './utils/odoo';

/**
 * Auditoria (2026-07-28): el dialogo "Nueva cotizacion desde imagen" tenia
 * un "selector de cliente" que en realidad era un <input> de texto suelto,
 * sin ninguna relacion con res.partner -- cualquier nombre/telefono/correo
 * tecleado a mano se guardaba tal cual, y action_create_quotation resolvia
 * el partner despues por fuzzy-match (correo/telefono) o creaba uno nuevo.
 *
 * Regla de negocio (confirmada por el usuario): no se vende a clientes no
 * registrados -- siempre deben haberse registrado antes via el portal de
 * /afiliacion. Por eso el selector ahora es un Many2XAutocomplete real
 * sobre res.partner, de SOLO busqueda (sin create/createEdit): no hay forma
 * de crear un cliente nuevo ni de enviar la solicitud sin elegir uno que ya
 * exista. Ver image_quote_drop_dialog.js/.xml y
 * controllers/quote_from_image_internal.py.
 *
 * Audit (2026-07-28): the "Quote from image" dialog's "customer selector"
 * was actually a plain text <input>, with no relation to res.partner at all
 * -- whatever name/phone/email was typed by hand got saved as-is, and
 * action_create_quotation resolved the partner afterward via fuzzy-match
 * (email/phone) or created a brand new one.
 *
 * Business rule (confirmed by the user): no selling to unregistered
 * customers -- they must always have registered beforehand via the
 * /afiliacion portal. So the selector is now a real Many2XAutocomplete over
 * res.partner, search-ONLY (no create/createEdit): there's no way to create
 * a new customer or submit the request without picking one that already
 * exists. See image_quote_drop_dialog.js/.xml and
 * controllers/quote_from_image_internal.py.
 */
test.describe('local_ai_connector — selector de cliente del dialogo "Nueva cotización desde imagen"', () => {
  test('no se puede enviar sin seleccionar un cliente registrado, y no hay forma de crear uno nuevo', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

    // La paleta custom de este proyecto (md_command_palette) reemplaza la
    // nativa de Odoo -- se abre con el boton de Apps de la NavBar, NO con
    // env.services.command.openMainPalette() (eso abre la paleta nativa,
    // que este proyecto no usa; ver md_command_palette/static/src/js/launcher.js).
    await page.locator('.o_navbar_apps_menu').click();
    const paletteInput = page.locator('.o_md_command_palette_input');
    await expect(paletteInput).toBeVisible({ timeout: 5000 });
    await paletteInput.fill('cotiz');
    await page.getByText('Nueva cotización desde imagen').click();

    const dialog = page.locator('.modal-content:has-text("Nueva cotización desde imagen")');
    await expect(dialog).toBeVisible({ timeout: 5000 });

    // Ya no debe existir NINGUN input de texto para nombre/telefono/correo
    // -- esa era la via de "cliente no registrado" que se elimino.
    await expect(dialog.locator('input[placeholder="Nombre del cliente *"]')).toHaveCount(0);
    await expect(dialog.locator('input[placeholder="Teléfono (WhatsApp)"]')).toHaveCount(0);
    await expect(dialog.locator('input[placeholder="Correo (opcional)"]')).toHaveCount(0);

    await dialog.locator('input[type="file"]').setInputFiles(fixture('tiny_test_image.png'));
    await page.waitForTimeout(300);

    // Hay foto pero no hay cliente: el boton debe seguir deshabilitado.
    await expect(dialog.getByRole('button', { name: 'Crear solicitud' })).toBeDisabled();

    // Buscar algo que definitivamente no existe: el dropdown NO debe
    // ofrecer "Crear" (activeActions.create/createEdit estan en false).
    const partnerInput = dialog.locator('.iqd_partner_select input');
    await partnerInput.click();
    await partnerInput.fill('zzzzz este nombre no existe 999');
    await page.waitForTimeout(800);
    await expect(page.locator('.o-autocomplete--dropdown-item', { hasText: 'Crear' })).toHaveCount(0);
  });

  test('seleccionar un cliente registrado habilita el envío y el partner_id llega correcto al backend', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

    // Cliente conocido de antemano via ORM -- evita depender de que un
    // nombre especifico exista en cualquier entorno donde corra la suite.
    const expectedPartner = await page.evaluate(async () => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const partners = await ormSvc.searchRead(
        'res.partner',
        [
          ['active', '=', true],
          ['name', '!=', false],
          '|', ['phone', '!=', false], ['email', '!=', false],
        ],
        ['id', 'name'],
        { limit: 1, order: 'id asc' }
      );
      return partners[0];
    });
    expect(expectedPartner, 'No hay ningun res.partner en esta base para usar en la prueba').toBeTruthy();

    await page.locator('.o_navbar_apps_menu').click();
    const paletteInput = page.locator('.o_md_command_palette_input');
    await expect(paletteInput).toBeVisible({ timeout: 5000 });
    await paletteInput.fill('cotiz');
    await page.getByText('Nueva cotización desde imagen').click();

    const dialog = page.locator('.modal-content:has-text("Nueva cotización desde imagen")');
    await expect(dialog).toBeVisible({ timeout: 5000 });

    const partnerInput = dialog.locator('.iqd_partner_select input');
    await partnerInput.click();
    await partnerInput.fill(expectedPartner.name);
    await page.waitForTimeout(800);
    const option = page.locator('.o-autocomplete--dropdown-item', { hasText: expectedPartner.name }).first();
    await expect(option).toBeVisible({ timeout: 5000 });
    await option.click();
    await page.waitForTimeout(300);

    await expect(dialog.getByRole('button', { name: 'Crear solicitud' })).toBeDisabled(); // aun sin foto
    await dialog.locator('input[type="file"]').setInputFiles(fixture('tiny_test_image.png'));
    await page.waitForTimeout(300);
    await expect(dialog.getByRole('button', { name: 'Crear solicitud' })).toBeEnabled();

    await dialog.getByRole('button', { name: 'Crear solicitud' }).click();
    const result = dialog.locator('.iqd_result.alert-success');
    await expect(result).toBeVisible({ timeout: 5000 });
    const resultText = await result.textContent();
    const reference = resultText?.match(/AIQ-\d+/)?.[0];
    expect(reference).toBeTruthy();

    const created = await page.evaluate(async (ref) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const rows = await ormSvc.searchRead(
        'local.ai.image.quote.request',
        [['name', '=', ref]],
        ['partner_id', 'customer_name']
      );
      return rows[0];
    }, reference);
    expect(created?.partner_id?.[0]).toBe(expectedPartner.id);
  });
});
