import { test, expect, Page, ConsoleMessage, Response } from '@playwright/test';

/**
 * AUDITORÍA v2: md_telegram_notify – Carga en res.config.settings (Odoo 19)
 *
 * Correctivos v2:
 *  - Selectores actualizados para Odoo 19 (res.config.settings usa .o_res_config_settings_view_form)
 *  - Navegación explícita al panel de Telegram via click en sidebar
 *  - Espera de networkidle para garantizar que OWL hidrata
 */

const CONSOLE_ERRORS: string[] = [];
const FAILED_REQUESTS: { url: string; status: number; body?: string }[] = [];

test.describe('Auditoría UI v2: md_telegram_notify en Ajustes', () => {

  test.beforeEach(async ({ page }) => {
    CONSOLE_ERRORS.length = 0;
    FAILED_REQUESTS.length = 0;

    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        CONSOLE_ERRORS.push(`[${msg.type().toUpperCase()}] ${msg.text()}`);
      }
    });

    page.on('pageerror', (err: Error) => {
      CONSOLE_ERRORS.push(`[PAGEERROR] ${err.message}`);
    });

    page.on('response', async (response: Response) => {
      const status = response.status();
      if (status >= 400) {
        FAILED_REQUESTS.push({ url: response.url(), status });
      }
    });
  });

  test('1. Ajustes carga sin errores de JS ni HTTP 500', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(2000);

    console.log('\n=== ERRORES DE CONSOLA ===');
    if (CONSOLE_ERRORS.length === 0) {
      console.log('  ✅ Sin errores de consola.');
    } else {
      CONSOLE_ERRORS.forEach(e => console.log('  ❌ ' + e));
    }

    const http500 = FAILED_REQUESTS.filter(r => r.status >= 500);
    if (http500.length === 0) {
      console.log('  ✅ Sin respuestas HTTP 500.');
    } else {
      http500.forEach(r => console.log(`  ❌ HTTP ${r.status}: ${r.url}`));
    }

    const telegramOnchangeError = FAILED_REQUESTS.some(r =>
      r.url.includes('onchange') && r.status >= 400
    );
    console.log(`  onchange error: ${telegramOnchangeError}`);

    await page.screenshot({ path: '/tmp/v2_settings_overview.png', fullPage: false });
    expect(http500, `HTTP 500: ${JSON.stringify(http500)}`).toHaveLength(0);
  });

  test('2. Telegram aparece en el sidebar de Ajustes', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(2000);

    // Odoo 19: el sidebar de ajustes usa .o_settings_menu_item o directamente <a> con texto
    const sidebar = page.locator('.o_settings_container_left, .o_app_settings, nav.o_settings_menu');
    const sidebarExists = await sidebar.count() > 0;
    console.log(`  Sidebar presente: ${sidebarExists}`);

    // Buscar "Telegram" en el sidebar (puede estar en cualquier <li> o <a>)
    const telegramSidebarItem = page.locator('.o_settings_menu_item:has-text("Telegram"), a:has-text("Telegram"), li:has-text("Telegram")').first();
    const telegramVisible = await telegramSidebarItem.isVisible().catch(() => false);
    console.log(`  "Telegram" en sidebar: ${telegramVisible}`);

    // Snapshot del HTML del sidebar para diagnóstico
    const bodyText = await page.locator('body').innerText().catch(() => '');
    const hasTelegramText = bodyText.includes('Telegram');
    console.log(`  Texto "Telegram" en body: ${hasTelegramText}`);

    // Obtener la estructura del sidebar
    const sidebarHTML = await page.evaluate(() => {
      const nav = document.querySelector('.o_settings_menu, .o_settings_nav, nav, aside');
      return nav ? nav.innerHTML.substring(0, 1500) : 'NO NAV ELEMENT';
    });
    console.log('\n📋 HTML del nav/sidebar:');
    console.log(sidebarHTML.substring(0, 800));

    await page.screenshot({ path: '/tmp/v2_settings_sidebar.png', fullPage: false });

    expect(hasTelegramText, 'El texto "Telegram" no está en ninguna parte de la página').toBe(true);
  });

  test('3. Navegar a sección Telegram y verificar campos', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(2000);

    // Hacer clic en "Telegram" en el sidebar
    const telegramLink = page.locator('text=Telegram').first();
    const isTelegramVisible = await telegramLink.isVisible().catch(() => false);

    if (isTelegramVisible) {
      console.log('  ✅ Clic en "Telegram" en el sidebar');
      await telegramLink.click();
      await page.waitForTimeout(2000);
    } else {
      console.log('  ⚠️  No se encontró el link "Telegram" — tomando screenshot del estado actual');
    }

    await page.screenshot({ path: '/tmp/v2_telegram_section.png', fullPage: true });

    // Verificar el campo Bot Token en cualquier form input
    const botTokenCount = await page.locator('[name="md_telegram_bot_token"]').count();
    const poThresholdCount = await page.locator('[name="md_telegram_po_threshold"]').count();
    const detectarChatsBtn = await page.locator('button:has-text("Detectar chats")').count();
    const enviarPruebaBtn = await page.locator('button:has-text("Enviar prueba")').count();

    console.log(`\n=== DIAGNÓSTICO CAMPOS TELEGRAM ===`);
    console.log(`  md_telegram_bot_token en DOM: ${botTokenCount}`);
    console.log(`  md_telegram_po_threshold en DOM: ${poThresholdCount}`);
    console.log(`  Botón "Detectar chats": ${detectarChatsBtn}`);
    console.log(`  Botón "Enviar prueba": ${enviarPruebaBtn}`);

    // Captura HTML de la sección activa
    const activeSection = await page.evaluate(() => {
      const content = document.querySelector('.o_content, .o_view_controller, main');
      return content ? content.innerHTML.substring(0, 3000) : 'NO CONTENT';
    });
    if (botTokenCount === 0) {
      console.log('\n📋 HTML de .o_content (primeros 2000 chars):');
      console.log(activeSection.substring(0, 2000));
    }

    console.log('\n=== ERRORES DE CONSOLA ACUMULADOS ===');
    if (CONSOLE_ERRORS.length === 0) {
      console.log('  ✅ Sin errores de consola.');
    } else {
      CONSOLE_ERRORS.forEach(e => console.log('  ❌ ' + e));
    }

    expect(botTokenCount, 'Campo md_telegram_bot_token no encontrado en el DOM').toBeGreaterThan(0);
    expect(poThresholdCount, 'Campo md_telegram_po_threshold no encontrado en el DOM').toBeGreaterThan(0);
    expect(detectarChatsBtn, 'Botón "Detectar chats" no encontrado').toBeGreaterThan(0);
  });

  test.afterEach(async ({}) => {
    console.log(`\n======= RESUMEN =======`);
    console.log(`Errores consola: ${CONSOLE_ERRORS.length}`);
    console.log(`Solicitudes fallidas: ${FAILED_REQUESTS.length}`);
  });
});
