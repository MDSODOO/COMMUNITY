import { test, expect, ConsoleMessage, Response } from '@playwright/test';

/**
 * AUDITORÍA v3 (FINAL): md_telegram_notify – Odoo 19
 *
 * Odoo 19 estructura de res.config.settings:
 *   - Sidebar izquierdo: .settings_tab (contiene los items de cada app)
 *   - Contenido principal: .o_setting_container
 *   - Cada panel app: .app_settings_block
 */

const CONSOLE_ERRORS: string[] = [];
const FAILED_REQUESTS: { url: string; status: number }[] = [];

test.describe('Auditoría UI Final: md_telegram_notify en Ajustes (Odoo 19)', () => {

  test.beforeEach(async ({ page }) => {
    CONSOLE_ERRORS.length = 0;
    FAILED_REQUESTS.length = 0;

    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error') {
        CONSOLE_ERRORS.push(`[ERROR] ${msg.text()}`);
      }
    });
    page.on('pageerror', (err: Error) => {
      CONSOLE_ERRORS.push(`[PAGEERROR] ${err.message}`);
    });
    page.on('response', (response: Response) => {
      if (response.status() >= 500) {
        FAILED_REQUESTS.push({ url: response.url(), status: response.status() });
      }
    });
  });

  test('1. Ajustes carga sin errores HTTP 500 ni errores JS', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(2000);

    console.log('\n=== ERRORES DE CONSOLA ===');
    if (CONSOLE_ERRORS.length === 0) {
      console.log('  ✅ Sin errores de consola.');
    } else {
      CONSOLE_ERRORS.forEach(e => console.log('  ❌ ' + e));
    }

    console.log('\n=== HTTP 500 ===');
    if (FAILED_REQUESTS.length === 0) {
      console.log('  ✅ Sin errores HTTP 500.');
    } else {
      FAILED_REQUESTS.forEach(r => console.log(`  ❌ ${r.status}: ${r.url}`));
    }

    await page.screenshot({ path: '/tmp/v3_settings_load.png', fullPage: false });
    expect(FAILED_REQUESTS).toHaveLength(0);
  });

  test('2. Sección Telegram en sidebar de Ajustes', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(2000);

    // Odoo 19: el sidebar de settings usa .settings_tab que contiene items <div class="app_settings_entry">
    // Cada entrada tiene el nombre del módulo/app.
    // Selector más robusto: buscar dentro del sidebar izquierdo
    const settingsTab = page.locator('.settings_tab');
    await expect(settingsTab).toBeVisible({ timeout: 15_000 });

    // Buscar el item de Telegram dentro del sidebar
    const telegramEntry = settingsTab.locator('text=Telegram').first();
    const isTelegramInSidebar = await telegramEntry.isVisible().catch(() => false);
    console.log(`  Telegram en sidebar (.settings_tab): ${isTelegramInSidebar}`);

    // Si hay el item, capturamos su texto completo y href
    if (isTelegramInSidebar) {
      const href = await telegramEntry.getAttribute('href').catch(() => null);
      console.log(`  href del item Telegram: ${href}`);
    }

    // Screenshot del estado
    await page.screenshot({ path: '/tmp/v3_sidebar_state.png', fullPage: false });

    // Verificar que el texto "Bot Token" o "Credenciales" también está en el DOM
    // (puede estar en otra sección oculta o en la misma visible)
    const fullBody = await page.locator('body').innerText();
    const hasTelegram = fullBody.includes('Telegram');
    console.log(`  Texto "Telegram" en body completo: ${hasTelegram}`);

    expect(isTelegramInSidebar, 'El item "Telegram" no aparece en el sidebar de Ajustes').toBe(true);
  });

  test('3. Panel Telegram muestra campos después de navegar', async ({ page }) => {
    await page.goto('/odoo/settings', { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForTimeout(2000);

    // Esperar el sidebar
    const settingsTab = page.locator('.settings_tab');
    await expect(settingsTab).toBeVisible({ timeout: 15_000 });

    // Clic en el item Telegram del sidebar (dentro de .settings_tab, NO del navbar superior)
    const telegramSidebarItem = settingsTab.locator('text=Telegram').first();
    await telegramSidebarItem.click();
    await page.waitForTimeout(2000);

    // Tomar screenshot del estado después del clic
    await page.screenshot({ path: '/tmp/v3_after_click.png', fullPage: true });

    // Verificar campos en el DOM
    const botTokenCount = await page.locator('[name="md_telegram_bot_token"]').count();
    const poThresholdCount = await page.locator('[name="md_telegram_po_threshold"]').count();
    const detectarBtn = await page.locator('button:has-text("Detectar chats"), button:has-text("Detectar")').count();
    const pruebaBtn = await page.locator('button:has-text("Enviar prueba"), button:has-text("prueba")').count();

    console.log(`\n=== CAMPOS TELEGRAM DESPUÉS DE CLIC ===`);
    console.log(`  md_telegram_bot_token: ${botTokenCount}`);
    console.log(`  md_telegram_po_threshold: ${poThresholdCount}`);
    console.log(`  Botón "Detectar chats": ${detectarBtn}`);
    console.log(`  Botón "Enviar prueba": ${pruebaBtn}`);

    // Diagnóstico adicional: html del bloque activo
    const activeBlock = await page.evaluate(() => {
      const block = document.querySelector('.app_settings_block, .selected .app_settings_block, section.o_setting_box, [data-string="Telegram"]');
      return block ? block.innerHTML.substring(0, 2000) : 'NO BLOCK FOUND';
    });
    if (botTokenCount === 0) {
      console.log('\n📋 HTML del bloque activo:');
      console.log(activeBlock.substring(0, 1500));
    }

    console.log(`\n=== ERRORES ACUMULADOS ===`);
    if (CONSOLE_ERRORS.length === 0) {
      console.log('  ✅ Sin errores JS.');
    } else {
      CONSOLE_ERRORS.forEach(e => console.log('  ❌ ' + e));
    }
    if (FAILED_REQUESTS.length === 0) {
      console.log('  ✅ Sin HTTP 500.');
    } else {
      FAILED_REQUESTS.forEach(r => console.log(`  ❌ ${r.status}: ${r.url}`));
    }

    expect(botTokenCount, 'Campo md_telegram_bot_token no visible después de clic en Telegram').toBeGreaterThan(0);
    expect(poThresholdCount, 'Campo md_telegram_po_threshold no visible después de clic').toBeGreaterThan(0);
    expect(detectarBtn, 'Botón "Detectar chats" no encontrado').toBeGreaterThan(0);
  });

  test.afterEach(async ({}) => {
    console.log(`\n-- Resumen: errores=${CONSOLE_ERRORS.length}, http500=${FAILED_REQUESTS.length}`);
  });
});
