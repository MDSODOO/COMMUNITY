import { test, expect } from '@playwright/test';
import fs from 'fs';
import os from 'os';
import path from 'path';
import {
  openImportWizard,
  uploadCfdiFile,
  captureIfErrorDialog,
  acceptConfirmDialog,
  clearSearchFilters,
  fixture,
} from './utils/odoo';

/**
 * Genera una copia de unmapped_products.xml con un codigo de producto UNICO
 * por corrida (basado en Date.now()). Necesario para que el test de
 * auto-creacion sea idempotente: si se reusa el mismo codigo fijo
 * ("999999999") en corridas sucesivas, la SEGUNDA corrida ya encuentra el
 * producto que creo la primera (match limpio via default_code, confianza
 * 0.99) en vez de ejercer el path de auto-creacion — dando un falso
 * positivo/negativo segun el orden de ejecucion.
 *
 * Generates a copy of unmapped_products.xml with a UNIQUE product code per
 * run (based on Date.now()). Needed for the auto-creation test to be
 * idempotent: reusing the same fixed code ("999999999") across successive
 * runs means the SECOND run already finds the product the first one
 * created (clean match via default_code, 0.99 confidence) instead of
 * exercising the auto-creation path — giving a false positive/negative
 * depending on run order.
 */
function withUniqueProductCode(sourcePath: string): string {
  const uniqueCode = `9${Date.now()}`.slice(0, 9); // 9 digitos, estilo CodigoSAP
  const uniqueBarcode = `9${Date.now()}`.padEnd(13, '0').slice(0, 13); // 13 digitos, estilo EAN
  // IMPORTANTE: reemplazar primero el patron de 13 digitos (el barcode) y
  // DESPUES el de 9 — "9999999999990" contiene "999999999" como substring,
  // así que el orden inverso corrompería el barcode a medio reemplazar.
  // IMPORTANT: replace the 13-digit pattern (the barcode) FIRST, then the
  // 9-digit one — "9999999999990" contains "999999999" as a substring, so
  // the reverse order would corrupt the barcode mid-replacement.
  const xml = fs
    .readFileSync(sourcePath, 'utf-8')
    .replace(/9999999999990/g, uniqueBarcode)
    .replace(/999999999/g, uniqueCode)
    .replace(/D013FF13-7E6F-4030-8CCE-F248602D74DC/g, `D013FF13-7E6F-4030-8CCE-${Date.now()}`.slice(0, 36));

  const outPath = path.join(os.tmpdir(), `unmapped_products_${Date.now()}.xml`);
  fs.writeFileSync(outPath, xml, 'utf-8');
  return outPath;
}

/**
 * Suite de auditoria UI: purchase_invoice_parser
 * UI audit suite: purchase_invoice_parser
 *
 * Regla de negocio innegociable: cuando se verifican cantidades fisicas de
 * inventario resultantes de una compra, el termino es siempre "A la mano"
 * (On Hand). Nunca "Disponible", "Stock" ni "Existencias".
 *
 * Non-negotiable business rule: when verifying physical on-hand inventory
 * quantities resulting from a purchase, the term is always "A la mano"
 * (On Hand). Never "Disponible" (Available), "Stock", or "Existencias".
 */

const FIXTURES = {
  // BRUDIFARMA: los lotes se extraen automaticamente de la Addenda XML, no
  // requiere PDF (a diferencia de QUIFAMESA). Ver utils/odoo.ts.
  // BRUDIFARMA: lots are auto-extracted from the XML Addenda, no PDF needed
  // (unlike QUIFAMESA). See utils/odoo.ts.
  valid: fixture('valid_invoice.xml'),
  broken: fixture('broken_invoice.xml'),
  unmapped: fixture('unmapped_products.xml'),
  // Mismo producto que "valid" (BRUDIFARMA, matchea por default_code, sin
  // Addenda ni "Lote:" en la Descripcion) para forzar el Hard Stop de
  // "A la Mano" en action_create_purchase_order.
  // Same product as "valid" (BRUDIFARMA, matches by default_code, no
  // Addenda and no "Lote:" in Descripcion) to force the "A la Mano" (On
  // Hand) Hard Stop in action_create_purchase_order.
  missingLot: fixture('missing_lot.xml'),
};

test.beforeAll(() => {
  const missing = Object.entries(FIXTURES).filter(([, p]) => !fs.existsSync(p));
  if (missing.length) {
    const names = missing.map(([k, p]) => `  - ${k}: ${p}`).join('\n');
    throw new Error(
      `Faltan archivos de fixtures / Missing fixture files:\n${names}\n` +
        `Coloca los 3 archivos en ./fixtures/ antes de correr la suite.\n` +
        `Place the 3 files under ./fixtures/ before running the suite.`
    );
  }
});

test.describe('purchase_invoice_parser — importacion de CFDI / CFDI import', () => {
  test('Happy Path: XML valido crea Orden de Compra en borrador / valid XML creates a draft Purchase Order', async ({
    page,
  }) => {
    const dialog = await openImportWizard(page);

    await uploadCfdiFile(dialog, 'xml_file', FIXTURES.valid);
    await dialog.locator('button[name="action_parse_xml"]').click();

    const hadError = await captureIfErrorDialog(page, 'happy-path-after-parse');
    expect(hadError, 'El archivo valido no deberia disparar un modal de error / valid file should not trigger an error modal').toBe(false);

    // Debe pasar al estado "review": aparece el UUID del CFDI y la tabla de conceptos.
    // Should move to "review" state: CFDI UUID and concepts table appear.
    await expect(dialog.locator('[name="cfdi_uuid"]')).not.toHaveText('');
    await expect(dialog.locator('[name="line_ids"] .o_list_renderer .o_data_row').first()).toBeVisible();

    // Verificacion campo por campo de los datos de cabecera del CFDI contra
    // el XML fuente (valid_invoice.xml) — el corazon del audit: confirmar
    // que la captura de informacion es exacta, no solo que "algo" se llena.
    //
    // Field-by-field verification of the CFDI header data against the
    // source XML (valid_invoice.xml) — the core of the audit: confirming
    // capture accuracy, not just that "something" gets filled.
    await expect(dialog.locator('[name="cfdi_uuid"]')).toContainText('D013FF13-7E6F-4030-8CCE-F248602D74DB');
    await expect(dialog.locator('[name="cfdi_folio"]')).toContainText('F2000201962');
    await expect(dialog.locator('[name="cfdi_moneda"]')).toContainText('MXN');
    await expect(dialog.locator('[name="cfdi_condiciones"]')).toContainText('75 dias sin DPP');
    await expect(dialog.locator('[name="cfdi_subtotal"]')).toContainText('2,112.00');
    await expect(dialog.locator('[name="cfdi_total"]')).toContainText('2,112.00');
    await expect(dialog.locator('[name="emisor_rfc"]')).toContainText('BRU971010227');
    await expect(dialog.locator('[name="emisor_nombre"]')).toContainText('BRUDIFARMA');
    await expect(dialog.locator('[name="supplier_format"]')).toContainText(/BRUDIFARMA/i);
    await expect(dialog.locator('[name="partner_match_method"]')).toContainText('rfc_exact');

    // Verificacion campo por campo de la unica linea de concepto: codigo de
    // proveedor, descripcion, producto matcheado, cantidad, precio, IVA e
    // importe deben coincidir exactamente con el XML fuente.
    //
    // Field-by-field verification of the single concept line: supplier
    // code, description, matched product, quantity, price, VAT and amount
    // must exactly match the source XML.
    const firstRow = dialog.locator('[name="line_ids"] .o_data_row').first();
    await expect(firstRow.locator('[name="no_identificacion"]')).toContainText('513769');
    await expect(firstRow.locator('[name="descripcion"]')).toContainText('ADINOL INF 3.2 G/100 ML SOL C/120 ML');
    await expect(firstRow.locator('[name="product_id"]')).toContainText('7501537103545');
    await expect(firstRow.locator('[name="cantidad"]')).toContainText('120.0000');
    await expect(firstRow.locator('[name="valor_unitario"]')).toContainText('17.6000');
    await expect(firstRow.locator('[name="tasa_iva"]').first()).toContainText('0%');
    await expect(firstRow.locator('[name="importe"]')).toContainText('2,112.00');
    // Lote y caducidad extraidos de la Addenda XML — dato fisico de
    // inventario resultante de la compra, jamas "Disponible"/"Stock".
    // Lot and expiration extracted from the XML Addenda — physical
    // inventory data resulting from the purchase, never "Disponible"/"Stock".
    await expect(firstRow.locator('[name="lots_display"]')).toContainText('2605456');
    await expect(firstRow.locator('[name="lots_display"]')).toContainText('13/05/2028');

    // Ninguna linea deberia quedar marcada en rojo (needs_review sin producto) en un XML limpio.
    // No line should be flagged red (needs_review without product) on a clean XML.
    const redRows = dialog.locator('[name="line_ids"] .o_data_row.text-danger, [name="line_ids"] .o_data_row.o_data_row_danger');
    await expect(redRows).toHaveCount(0);

    // Brudifarma auto-extrae lotes de la Addenda XML durante el parseo
    // (_postprocess_brudifarma). El resumen de lotes reporta cantidades
    // fisicas resultantes de la compra: el termino obligatorio es
    // "A la mano" (On Hand) — nunca "Disponible"/"Stock"/"Existencias".
    //
    // Brudifarma auto-extracts lots from the XML Addenda during parsing
    // (_postprocess_brudifarma). The lots summary reports physical
    // quantities resulting from the purchase: the mandatory term is
    // "A la mano" (On Hand) — never "Disponible"/"Stock"/"Existencias".
    const lotsSummary = dialog.locator('[name="lots_summary"]');
    if (await lotsSummary.isVisible().catch(() => false)) {
      await expect(lotsSummary).toContainText(/a la mano/i);
      await expect(lotsSummary).not.toContainText(/disponible|existencias|\bstock\b/i);
    }

    await dialog.locator('button[name="action_create_purchase_order"]').click();

    // El boton tiene confirm="..." → Odoo abre un dialogo de confirmacion
    // nativo ANTES de disparar la llamada al servidor (boton "De acuerdo").
    // The button has confirm="..." → Odoo opens a native confirmation
    // dialog BEFORE firing the server call (button "De acuerdo").
    await acceptConfirmDialog(page, 'Verifica que los lotes');

    await captureIfErrorDialog(page, 'happy-path-after-create');

    // La OC se crea y se navega a su formulario (target: current) en estado borrador (RFQ).
    // The PO is created and we navigate to its form (target: current) in draft (RFQ) state.
    await expect(page.locator('.o_form_view .o_field_widget[name="name"] input, .o_breadcrumb')).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.locator('.o_statusbar_status button.o_arrow_button_current, .o_statusbar_status .btn-primary')).toContainText(
      /RFQ|Solicitud de cotización|Borrador/i
    );
  });

  test('Error Handling: archivo corrupto muestra UserError legible, no Traceback / corrupt file shows a readable UserError, not a stack trace', async ({
    page,
  }) => {
    const dialog = await openImportWizard(page);

    await uploadCfdiFile(dialog, 'xml_file', FIXTURES.broken);
    await dialog.locator('button[name="action_parse_xml"]').click();

    const hadErrorDialog = await captureIfErrorDialog(page, 'broken-invoice-error-dialog');

    // Regresion critica: la UI NUNCA debe mostrar un traceback Python crudo o error 500.
    // Critical regression: the UI must NEVER show a raw Python traceback or a 500 error.
    await expect(page.locator('body')).not.toContainText('Traceback (most recent call last)');
    await expect(page.locator('body')).not.toContainText(/odoo\.exceptions\.|psycopg2\.|werkzeug\.exceptions\.InternalServerError/);
    await expect(page).not.toHaveTitle(/500|Internal Server Error/i);

    // Se espera un UserError con mensaje de negocio claro (modal de error de Odoo).
    // A UserError with a clear business message is expected (Odoo error modal).
    expect(
      hadErrorDialog,
      'Se esperaba un modal .o_error_dialog con un mensaje claro / expected an .o_error_dialog with a clear message'
    ).toBe(true);
  });

  test('Unmapped Product Handling: producto desconocido se auto-crea como bien almacenable, queda marcado para revisión, y la OC se genera / unknown product auto-creates as a storable good, flagged for review, and the PO is generated', async ({
    page,
  }) => {
    // NOTA DE ACTUALIZACION: este test reemplaza el comportamiento anterior
    // (bloqueo + producto vacio) tras el refactor que agrego
    // _auto_create_product() en purchase_invoice_import_wizard.py. Ver
    // conversacion: ahora un codigo sin match crea dinamicamente un
    // product.product almacenable en vez de bloquear la importacion.
    //
    // UPDATE NOTE: this test replaces the previous behavior (block + empty
    // product) after the refactor that added _auto_create_product() in
    // purchase_invoice_import_wizard.py. See conversation: an unmatched code
    // now dynamically creates a storable product.product instead of
    // blocking the import.
    const dialog = await openImportWizard(page);

    // Codigo unico por corrida — ver withUniqueProductCode() arriba.
    // Unique code per run — see withUniqueProductCode() above.
    const runFixture = withUniqueProductCode(FIXTURES.unmapped);
    await uploadCfdiFile(dialog, 'xml_file', runFixture);
    await dialog.locator('button[name="action_parse_xml"]').click();

    const hadError = await captureIfErrorDialog(page, 'unmapped-after-parse');
    expect(hadError, 'El parseo no deberia fallar / parsing should not fail').toBe(false);

    // La linea debe traer el producto YA asignado (auto-creado), pero
    // needs_review sigue en True → decoration-warning (naranja/text-warning),
    // NO decoration-danger (rojo) — esa combinacion (needs_review Y
    // product_id) es justo lo que distingue "auto-creado, pendiente de
    // revision humana" de "sin producto en absoluto". Verificado en vivo
    // contra la vista real, no asumido.
    //
    // The line must come with the product ALREADY assigned (auto-created),
    // but needs_review stays True → decoration-warning (orange/text-warning),
    // NOT decoration-danger (red) — that combination (needs_review AND
    // product_id) is exactly what distinguishes "auto-created, pending
    // human review" from "no product at all". Verified live against the
    // real view, not assumed.
    const row = dialog.locator('[name="line_ids"] .o_data_row').first();
    await expect(row).toHaveClass(/text-warning/);
    await expect(row).not.toHaveClass(/text-danger/);
    await expect(row.locator('[name="product_id"]')).toContainText('PRODUCTO NUEVO SIN CATALOGAR');
    // No se afirma el codigo exacto: es unico por corrida (withUniqueProductCode).
    // Exact code not asserted: it's unique per run (withUniqueProductCode).

    // Crear la OC ya NO debe bloquearse: el producto auto-creado cuenta
    // como "asignado" para el hard-stop de sin_producto.
    // Creating the PO must NOT be blocked anymore: the auto-created product
    // counts as "assigned" for the sin_producto hard-stop.
    await dialog.locator('button[name="action_create_purchase_order"]').click();
    await acceptConfirmDialog(page, 'Verifica que los lotes');

    const blockedAfterCreate = await captureIfErrorDialog(page, 'unmapped-autocreated-po-created');
    expect(
      blockedAfterCreate,
      'La OC con producto auto-creado NO deberia bloquearse / PO with an auto-created product should NOT be blocked'
    ).toBe(false);
    await expect(page.locator('.o_breadcrumb')).toBeVisible({ timeout: 15_000 });
    await expect(
      page.locator('.o_statusbar_status button.o_arrow_button_current, .o_statusbar_status .btn-primary')
    ).toContainText(/RFQ|Solicitud de cotización|Borrador/i);

    // Verificacion en catalogo: el producto quedo como bien almacenable
    // ("Bienes") y su cantidad fisica resultante de esta compra en borrador
    // es 0 — el termino obligatorio es "A la mano" (On Hand), NUNCA
    // "Disponible"/"Stock"/"Existencias" (regla de negocio innegociable).
    //
    // Catalog verification: the product landed as a storable good ("Bienes")
    // and its physical quantity resulting from this still-draft purchase is
    // 0 — the mandatory term is "A la mano" (On Hand), NEVER
    // "Disponible"/"Stock"/"Existencias" (non-negotiable business rule).
    await page.goto('/odoo/inventory/products');
    await clearSearchFilters(page);
    const searchBox = page.locator('.o_searchview_input, input[placeholder*="Buscar"]').first();
    await searchBox.fill('PRODUCTO NUEVO SIN CATALOGAR');
    await page.getByText('Búsqueda Producto para:').first().click();
    const productCard = page.locator('.o_kanban_record', { hasText: 'PRODUCTO NUEVO SIN CATALOGAR' }).first();
    await expect(productCard).toBeVisible({ timeout: 10_000 });
    await productCard.click();

    await expect(page.getByText('Bienes', { exact: true })).toBeVisible({ timeout: 10_000 });
    const onHandQty = page.locator('[name="qty_available"]').first();
    await expect(onHandQty).toContainText('0.00');
    await expect(onHandQty).not.toContainText(/disponible|existencias|\bstock\b/i);
  });

  test('Hard Stop "A la Mano": producto con seguimiento por lote sin lote valido bloquea la creacion de la OC / product with lot tracking but no valid lot blocks PO creation', async ({
    page,
  }) => {
    const dialog = await openImportWizard(page);

    await uploadCfdiFile(dialog, 'xml_file', FIXTURES.missingLot);
    await dialog.locator('button[name="action_parse_xml"]').click();
    await captureIfErrorDialog(page, 'missing-lot-after-parse');

    // El producto SI matchea (por default_code) y NO requiere revision —
    // este Hard Stop es distinto al de "producto sin asignar": aqui el
    // problema es la falta de lote para un producto con tracking='lot'.
    //
    // The product DOES match (by default_code) and does NOT need review —
    // this Hard Stop is different from "unassigned product": here the
    // problem is the missing lot for a tracking='lot' product.
    const firstRow = dialog.locator('[name="line_ids"] .o_data_row').first();
    await expect(firstRow.locator('[name="product_id"]')).toContainText('ADINOL');
    const redRows = dialog.locator('[name="line_ids"] .o_data_row.text-danger, [name="line_ids"] .o_data_row.o_data_row_danger');
    await expect(redRows).toHaveCount(0);

    // El resumen de lotes debe avisar que no se encontraron lotes en el XML.
    // The lots summary must warn that no lots were found in the XML.
    await expect(dialog.locator('[name="lots_summary"]')).toContainText(/sin lotes/i);

    await dialog.locator('button[name="action_create_purchase_order"]').click();
    await acceptConfirmDialog(page, 'Verifica que los lotes');

    const blocked = await captureIfErrorDialog(page, 'missing-lot-create-blocked');
    expect(
      blocked,
      'La creacion de OC sin lote para un producto con tracking=lot debe bloquearse / PO creation without a lot for a tracking=lot product must be blocked'
    ).toBe(true);

    // Regla de negocio innegociable (Paso 2 de las instrucciones): el
    // mensaje de bloqueo debe usar "A la Mano" (On Hand), NUNCA
    // "Disponible", "Stock" ni "Existencias".
    //
    // Non-negotiable business rule (instructions Step 2): the block message
    // must use "A la Mano" (On Hand), NEVER "Disponible", "Stock", or
    // "Existencias".
    const errorDialog = page.locator('.modal-content.o_error_dialog');
    await expect(errorDialog).toContainText(/a la mano/i);
    await expect(errorDialog).toContainText(/on hand/i);
    await expect(errorDialog).not.toContainText(/disponible|existencias|\bstock\b/i);
    await expect(errorDialog).toContainText(/seguimiento por lote/i);

    // No se crea ninguna OC: seguimos en el wizard.
    // No PO gets created: we remain in the wizard.
    await page.locator('.modal-content.o_error_dialog button.o-default-button').click();
    await expect(dialog.locator('.o_form_view')).toBeVisible();
  });
});
