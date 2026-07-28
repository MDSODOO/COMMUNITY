import { Page, Locator, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

/**
 * Abre el wizard "Importar XML de Proveedor" desde la lista de Ordenes de
 * Compra confirmadas (boton .pip_import_xml_btn, ver purchase_order_views.xml).
 *
 * IMPORTANTE — hallazgo de esta auditoria: se navega a /odoo/purchase-orders
 * ("Ordenes de compra") y NO a /odoo/purchase ("Solicitudes de cotizacion").
 * La accion de RFQ (purchase.purchase_rfq) fuerza view_id=purchase_order_kpis_tree,
 * una vista primaria standalone (inherit_id=False) que NUNCA aplica las
 * extensiones de purchase_invoice_parser — el boton "Importar XML" es
 * invisible ahi pese a `display="always"`. En la lista de Ordenes de Compra
 * la accion usa la vista por defecto (sin override), que si hereda
 * correctamente, y el boton renderiza. Ver reporte de hallazgos.
 *
 * Opens the "Import Supplier XML" wizard from the confirmed Purchase Order
 * list (button .pip_import_xml_btn, see purchase_order_views.xml).
 *
 * IMPORTANT — finding from this audit: navigates to /odoo/purchase-orders
 * ("Purchase Orders"), NOT /odoo/purchase ("Quotations/RFQ"). The RFQ action
 * (purchase.purchase_rfq) hardcodes view_id=purchase_order_kpis_tree, a
 * standalone primary view (inherit_id=False) that NEVER applies
 * purchase_invoice_parser's extensions — the "Importar XML" button is
 * invisible there despite `display="always"`. The Purchase Orders list uses
 * the default view (no override), which inherits correctly and renders the
 * button. See findings report.
 */
export async function openImportWizard(page: Page): Promise<Locator> {
  await page.goto('/odoo/purchase-orders');
  await page.locator('button.pip_import_xml_btn').first().click();
  const dialog = page.locator('.o_dialog').last();
  await expect(dialog.locator('.o_form_view')).toBeVisible({ timeout: 15_000 });
  return dialog;
}

/**
 * Sube un archivo al campo cfdi_upload indicado (xml_file, pdf_file, zip_file).
 * El widget custom (cfdi_upload_widget.js) esconde un <input type=file> real
 * dentro de la zona de drag&drop — Playwright puede apuntarle aunque no sea
 * visible para el usuario.
 *
 * Uploads a file into the given cfdi_upload field (xml_file, pdf_file,
 * zip_file). The custom widget hides a real <input type=file> inside the
 * drag&drop zone — Playwright can target it even though it's not visible.
 */
export async function uploadCfdiFile(
  dialog: Locator,
  fieldName: 'xml_file' | 'pdf_file' | 'zip_file',
  filePath: string
) {
  const input = dialog.locator(`[name="${fieldName}"] input[type="file"]`);
  await input.setInputFiles(filePath);
}

/**
 * Detecta si hay un modal de error de Odoo visible (clase .o_error_dialog,
 * o un dialogo cuyo titulo contiene "Error"). Si lo encuentra, toma una
 * captura de pantalla con nombre descriptivo, independientemente de si el
 * test termina en pass/fail — un modal de error puede ser el resultado
 * ESPERADO (ej. archivo corrupto) o un bug real (Traceback/500).
 *
 * Detects a visible Odoo error modal (.o_error_dialog class, or a dialog
 * whose title contains "Error"). If found, takes a descriptive screenshot
 * regardless of pass/fail — an error modal can be the EXPECTED result
 * (e.g. corrupt file) or a real bug (Traceback/500).
 *
 * @returns true si se detecto y capturo un modal de error / true if an
 * error modal was detected and captured.
 */
export async function captureIfErrorDialog(page: Page, label: string): Promise<boolean> {
  // Odoo usa el titulo fijo "Operacion no valida" (Invalid Operation) para
  // cualquier UserError sin titulo custom, y SI aplica la clase real
  // ".o_error_dialog" — pero en ".modal-content", no en el wrapper ".o_dialog".
  // Bug real encontrado durante esta auditoria: el wrapper exterior ".o_dialog"
  // es un contenedor de 0x0 (sin tamano propio, el contenido real esta en su
  // hijo .modal-content) — usar ".o_dialog:has-text(...)" con .first() elegia
  // ese wrapper vacio y waitFor({state:'visible'}) nunca se cumplia. Por eso
  // se apunta directo a .modal-content, que si tiene bounding box real.
  //
  // Odoo uses the fixed title "Operacion no valida" (Invalid Operation) for
  // any UserError without a custom title, and DOES apply the real
  // ".o_error_dialog" class — but on ".modal-content", not the ".o_dialog"
  // wrapper. Real bug found during this audit: the outer ".o_dialog" wrapper
  // is a 0x0 container (no intrinsic size, real content lives in its
  // .modal-content child) — using ".o_dialog:has-text(...)" with .first()
  // picked that empty wrapper and waitFor({state:'visible'}) never resolved.
  // Hence targeting .modal-content directly, which has a real bounding box.
  const errorDialog = page.locator(
    '.o_error_dialog, .modal-content:has-text("Operación no válida"), .modal-content:has-text("Invalid Operation"), .modal-content:has-text("Error de validación")'
  );

  // IMPORTANTE: locator.isVisible({timeout}) NO espera/reintenta — hace una
  // sola comprobacion instantanea del DOM (el timeout no lo hace pollear).
  // waitFor({state:'visible'}) si hace polling hasta que el modal renderice
  // tras el roundtrip RPC. Bug real encontrado durante esta auditoria: con
  // isVisible() la deteccion era una carrera contra el render del dialogo.
  //
  // IMPORTANT: locator.isVisible({timeout}) does NOT wait/retry — it's a
  // single instant DOM check (the timeout does not make it poll).
  // waitFor({state:'visible'}) does poll until the modal renders after the
  // RPC roundtrip. Real bug found during this audit: with isVisible() the
  // detection was a race against the dialog's render.
  const found = await errorDialog
    .first()
    .waitFor({ state: 'visible', timeout: 5_000 })
    .then(() => true)
    .catch(() => false);
  if (!found) {
    return false;
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filePath = path.join(SCREENSHOT_DIR, `${label}__${timestamp}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  // eslint-disable-next-line no-console
  console.log(`[o_error_dialog detectado] Screenshot guardado en / saved to: ${filePath}`);
  return true;
}

/**
 * Acepta el dialogo de confirmacion nativo que Odoo abre para botones con
 * atributo confirm="..." (ej. action_create_purchase_order). El texto del
 * boton en Odoo 19 es "De acuerdo", no "Aceptar"/"Ok".
 *
 * Accepts the native confirmation dialog Odoo opens for buttons with a
 * confirm="..." attribute (e.g. action_create_purchase_order). The button
 * text on Odoo 19 is "De acuerdo", not "Aceptar"/"Ok".
 */
export async function acceptConfirmDialog(page: Page, bodyTextHint: string): Promise<void> {
  const confirmDialog = page.locator(`.modal:has-text("${bodyTextHint}")`);
  // waitFor() poll-espera el render; isVisible() no lo hace (ver nota en
  // captureIfErrorDialog). / waitFor() polls for the render; isVisible()
  // does not (see note in captureIfErrorDialog).
  const appeared = await confirmDialog
    .first()
    .waitFor({ state: 'visible', timeout: 3_000 })
    .then(() => true)
    .catch(() => false);
  if (appeared) {
    await confirmDialog.getByRole('button', { name: /De acuerdo|Aceptar|Ok/i }).click();
  }
}

/**
 * La vista de Productos en Inventario trae filtros por defecto ("En
 * Existencia", "Ventas") que EXCLUYEN productos recien auto-creados por el
 * parser: qty_available=0 (aun no hay recepcion fisica) y sale_ok=False
 * (por diseno, ver _auto_create_product). Sin limpiar estos filtros, la
 * busqueda del producto no encuentra nada aunque el producto SI exista —
 * hallazgo real de esta auditoria, no un supuesto.
 *
 * The Products view in Inventory carries default filters ("In Stock",
 * "Can be Sold") that EXCLUDE freshly auto-created products from the
 * parser: qty_available=0 (no physical receipt yet) and sale_ok=False (by
 * design, see _auto_create_product). Without clearing these filters, the
 * product search finds nothing even though the product DOES exist — a real
 * finding from this audit, not an assumption.
 */
export async function clearSearchFilters(page: Page): Promise<void> {
  // Los filtros por defecto de la vista se aplican via RPC DESPUES de que
  // goto() ya resolvio (la navegacion termina antes de que la SPA de Odoo
  // termine de hidratar) — sin esta espera, el loop de abajo comprueba
  // "sin filtros" antes de que existan y sale de inmediato sin limpiar nada.
  //
  // The view's default filters are applied via RPC AFTER goto() already
  // resolved (navigation finishes before Odoo's SPA finishes hydrating) —
  // without this wait, the loop below checks "no filters" before they even
  // exist and exits immediately without clearing anything.
  await page.locator('.o_searchview_input_container').first().waitFor({ state: 'visible', timeout: 10_000 });
  await page.waitForTimeout(1_000);

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const facet = page.locator('.o_searchview_facet .o_facet_remove').first();
    const hasFacet = await facet.isVisible({ timeout: 500 }).catch(() => false);
    if (!hasFacet) break;
    await facet.click();
    await page.waitForTimeout(300);
  }
}

/** Ruta absoluta a un archivo de fixtures. / Absolute path to a fixture file. */
export function fixture(name: string): string {
  return path.join(__dirname, '..', 'fixtures', name);
}

/**
 * Login manual (mismos pasos que auth.setup.ts) para specs que necesitan un
 * usuario DISTINTO al de la sesion compartida (.auth/odoo-session.json).
 * Requiere que el test/archivo use `test.use({ storageState: undefined })`
 * para no arrancar ya autenticado con la sesion compartida.
 *
 * Manual login (same steps as auth.setup.ts) for specs that need a
 * DIFFERENT user than the shared session (.auth/odoo-session.json).
 * Requires the test/file to set `test.use({ storageState: undefined })` so
 * it doesn't start out already authenticated via the shared session.
 */
export async function loginAs(page: Page, login: string, password: string, db?: string): Promise<void> {
  await page.goto('/web/login');

  // Si hay usuarios recientes en esta instancia, Odoo 19 muestra un selector
  // ("Choose a user") en vez del formulario de login directo -- el input de
  // login SI esta en el DOM pero oculto detras de esa pantalla. Hay que
  // pasar por "Use another user" primero.
  //
  // OJO con .isVisible({timeout}): NO hace polling, es una sola
  // comprobacion instantanea del DOM (mismo gotcha ya documentado en
  // captureIfErrorDialog mas arriba en este archivo) -- con eso, esta
  // deteccion era una carrera contra el render de la pantalla del selector
  // y fallaba de forma intermitente. .waitFor() si hace polling.
  //
  // If there are recent users on this instance, Odoo 19 shows a chooser
  // ("Choose a user") instead of the plain login form -- the login input IS
  // in the DOM but hidden behind that screen. Need to go through "Use
  // another user" first.
  //
  // Watch out for .isVisible({timeout}): it does NOT poll, it's a single
  // instant DOM check (same gotcha already documented in
  // captureIfErrorDialog earlier in this file) -- with that, this
  // detection was a race against the chooser screen's render and failed
  // intermittently. .waitFor() does poll.
  const useAnotherUser = page.getByRole('button', { name: /Use another user|Usar otro usuario/i });
  const chooserAppeared = await useAnotherUser
    .waitFor({ state: 'visible', timeout: 3_000 })
    .then(() => true)
    .catch(() => false);
  if (chooserAppeared) {
    await useAnotherUser.click();
  }

  const dbField = page.locator('input[name="db"]');
  if (await dbField.isVisible().catch(() => false)) {
    await dbField.fill(db ?? process.env.ODOO_DB ?? 'medicinedepot_dev');
  }

  await page.locator('input[name="login"]').fill(login);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('form:has(input[name="password"]) button[type="submit"]').click();

  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 20_000 });
}
