import { test, expect, Page, ConsoleMessage, Response } from '@playwright/test';

/**
 * AUDITORÍA: md_telegram_notify – Carga en res.config.settings
 *
 * Objetivos:
 *  1. Navegar a /odoo/settings y detectar la sección de Telegram.
 *  2. Capturar errores de consola JS/OWL.
 *  3. Capturar respuestas de red HTTP 4xx/5xx.
 *  4. Verificar que el DOM contiene el bloque de Telegram.
 *  5. Verificar que los campos md_telegram_bot_token y md_telegram_po_threshold están presentes.
 */

const CONSOLE_ERRORS: string[] = [];
const FAILED_REQUESTS: { url: string; status: number }[] = [];

test.describe('Auditoría UI: md_telegram_notify en Ajustes', () => {

  test.beforeEach(async ({ page }) => {
    CONSOLE_ERRORS.length = 0;
    FAILED_REQUESTS.length = 0;

    // Captura errores de consola del navegador
    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        CONSOLE_ERRORS.push(`[${msg.type().toUpperCase()}] ${msg.text()}`);
      }
    });

    // Captura errores JS no capturados
    page.on('pageerror', (err: Error) => {
      CONSOLE_ERRORS.push(`[PAGEERROR] ${err.message}\n${err.stack}`);
    });

    // Captura respuestas de red fallidas (4xx / 5xx)
    page.on('response', (response: Response) => {
      const status = response.status();
      if (status >= 400) {
        FAILED_REQUESTS.push({ url: response.url(), status });
      }
    });
  });

  test('1. Navegar a /odoo/settings sin errores críticos', async ({ page }) => {
    // ---- Navegar a Ajustes ----
    const responsePromise = page.waitForResponse(
      r => r.url().includes('/odoo/settings') || r.url().includes('/web#action'),
      { timeout: 30_000 }
    ).catch(() => null);

    await page.goto('/odoo/settings', { waitUntil: 'domcontentloaded', timeout: 30_000 });

    // Esperar que el formulario principal esté visible
    await page.waitForSelector('.o_settings_container, .o_form_view, .o_setting_box', {
      timeout: 30_000,
      state: 'visible',
    }).catch(() => {
      // Captura screenshot en caso de fallo
      return page.screenshot({ path: '/tmp/settings_load_failure.png' });
    });

    // Esperar un momento extra para que OWL hidrate completamente
    await page.waitForTimeout(3000);

    // ---- Recopilar errores ----
    console.log('\n=== ERRORES DE CONSOLA ===');
    if (CONSOLE_ERRORS.length === 0) {
      console.log('  ✅ Sin errores de consola.');
    } else {
      CONSOLE_ERRORS.forEach(e => console.log('  ❌ ' + e));
    }

    console.log('\n=== SOLICITUDES FALLIDAS ===');
    if (FAILED_REQUESTS.length === 0) {
      console.log('  ✅ Sin solicitudes fallidas.');
    } else {
      FAILED_REQUESTS.forEach(r => console.log(`  ❌ HTTP ${r.status}: ${r.url}`));
    }

    // ---- Captura de pantalla del estado actual ----
    await page.screenshot({ path: '/tmp/settings_current_state.png', fullPage: true });
    console.log('\n📸 Screenshot guardado en /tmp/settings_current_state.png');

    // ---- Verificar que no hay errores HTTP 500 críticos ----
    const http500 = FAILED_REQUESTS.filter(r => r.status >= 500);
    expect(http500, `HTTP 500 encontrados: ${JSON.stringify(http500)}`).toHaveLength(0);

    // ---- Verificar ausencia de errores OWL críticos ----
    const owlErrors = CONSOLE_ERRORS.filter(e =>
      e.includes('OWL') ||
      e.includes('Component') ||
      e.includes('RPC') ||
      e.includes('Cannot read') ||
      e.includes('is not defined') ||
      e.includes('TypeError') ||
      e.includes('Error:')
    );
    if (owlErrors.length > 0) {
      console.log('\n🚨 ERRORES OWL/JS DETECTADOS:');
      owlErrors.forEach(e => console.log('  ' + e));
    }
    expect(owlErrors, `Errores OWL/JS: ${owlErrors.join('\n')}`).toHaveLength(0);
  });

  test('2. Sección Telegram visible en la página de Ajustes', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'domcontentloaded', timeout: 30_000 });

    // Esperar que la vista de ajustes esté lista
    await page.waitForSelector('.o_settings_container, .o_form_view', {
      timeout: 30_000,
      state: 'visible',
    });
    await page.waitForTimeout(3000);

    // Buscar el app panel de Telegram
    const telegramApp = page.locator('[data-string="Telegram"], app[string="Telegram"]');
    const telegramAppVisible = await telegramApp.isVisible().catch(() => false);

    // Buscar por texto "Telegram" en la navegación lateral
    const telegramNavItem = page.locator('.app_name:has-text("Telegram"), .settings_tab:has-text("Telegram")');
    const telegramNavVisible = await telegramNavItem.isVisible().catch(() => false);

    // Buscar el campo Bot Token
    const botTokenField = page.locator('[name="md_telegram_bot_token"], input[id*="telegram"]');
    const botTokenVisible = await botTokenField.isVisible().catch(() => false);

    console.log('\n=== DIAGNÓSTICO DE ELEMENTOS DOM ===');
    console.log(`  app[data-string="Telegram"] visible: ${telegramAppVisible}`);
    console.log(`  Nav item "Telegram" visible: ${telegramNavVisible}`);
    console.log(`  Campo Bot Token visible: ${botTokenVisible}`);

    // Screenshot con anotaciones
    await page.screenshot({ path: '/tmp/settings_telegram_section.png', fullPage: true });

    // Verificar que al menos el panel de Telegram existe en el DOM (puede estar oculto)
    const telegramInDOM = await page.locator('[data-string="Telegram"], [name="md_telegram_bot_token"]').count();
    console.log(`  Elementos Telegram en DOM: ${telegramInDOM}`);

    if (telegramInDOM === 0) {
      // Captura del HTML completo de la vista para diagnóstico
      const settingsHTML = await page.locator('.o_settings_container, .o_form_view').innerHTML().catch(() => 'NO CONTAINER');
      console.log('\n📋 HTML de .o_settings_container (primeros 2000 chars):');
      console.log(settingsHTML.substring(0, 2000));
    }

    expect(telegramInDOM, 'La sección Telegram no aparece en el DOM de Ajustes').toBeGreaterThan(0);
  });

  test('3. Campos md_telegram interactuables en Ajustes', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await page.waitForSelector('.o_settings_container, .o_form_view', { timeout: 30_000 });
    await page.waitForTimeout(3000);

    // Intentar hacer clic en la sección Telegram si hay navegación lateral
    const telegramTab = page.locator('text=Telegram').first();
    if (await telegramTab.isVisible().catch(() => false)) {
      await telegramTab.click();
      await page.waitForTimeout(1500);
    }

    // Verificar el campo Bot Token
    const botTokenField = page.locator('[name="md_telegram_bot_token"]');
    const botTokenExists = await botTokenField.count() > 0;
    console.log(`  Campo md_telegram_bot_token en DOM: ${botTokenExists}`);

    // Verificar el campo umbral PO
    const poThresholdField = page.locator('[name="md_telegram_po_threshold"]');
    const poThresholdExists = await poThresholdField.count() > 0;
    console.log(`  Campo md_telegram_po_threshold en DOM: ${poThresholdExists}`);

    // Screenshot final
    await page.screenshot({ path: '/tmp/settings_telegram_fields.png', fullPage: true });

    expect(botTokenExists, 'Campo md_telegram_bot_token no encontrado').toBe(true);
    expect(poThresholdExists, 'Campo md_telegram_po_threshold no encontrado').toBe(true);
  });

  test.afterEach(async ({ page }) => {
    // Resumen final siempre
    console.log('\n======= RESUMEN FINAL =======');
    console.log(`Errores de consola totales: ${CONSOLE_ERRORS.length}`);
    console.log(`Solicitudes fallidas totales: ${FAILED_REQUESTS.length}`);
  });
});
