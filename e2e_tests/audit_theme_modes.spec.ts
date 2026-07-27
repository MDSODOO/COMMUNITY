import { test, expect, Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

/**
 * Auditoria de contraste Claro/Oscuro (Light/Dark mode) — MedicineDepot Odoo 19.
 *
 * Contexto: IrHttp.color_scheme() esta hardcodeado a "light" en el core de
 * Odoo 19 Community (odoo/addons/web/models/ir_http.py) -- el bundle nativo
 * web.assets_web_dark NUNCA carga en esta instancia. El unico mecanismo de
 * dark mode que funciona es el toggle propio de custom_addons/md_dark_mode
 * (clase .o_md_dark_mode + atributo [data-bs-theme="dark"] en <html>). Este
 * spec valida ese mecanismo real, no el nativo de Odoo.
 *
 * Vistas cubiertas (backend, unico alcance donde el toggle es alcanzable
 * hoy -- el toggle del sitio publico esta desconectado, ver
 * docs/AI_MODEL_ODOO_CONFIG.md / hallazgos de auditoria 2026-07-27):
 *   1. Contactos: ficha con chatter + grupos de campos.
 *   2. Inventario > Productos: kanban con la card de md_pharma_regulatory.
 *   3. Bajas de caducidad (medicine_depot_scrap_batch): statusbar.
 *   4. Menu de campanita "Actualizaciones de precio" (purchase_invoice_parser).
 *
 * No usamos "Disponible"/"Stock"/"Existencias" en ningun selector, log ni
 * comentario -- cualquier cantidad fisica de producto se llama 'A la mano'
 * (On Hand) si llegara a aparecer en una de estas vistas.
 */

const CONTRAST_THRESHOLD = 4.5;
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'theme_audit_failures');

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
});

// ─── Utilidades de contraste ────────────────────────────────────────────
// Inyectadas en la pagina via page.evaluate: componen el fondo efectivo
// subiendo por los ancestros (alpha-blend correcto), no solo leen el
// background-color del propio elemento -- md_dark_mode/dark_mode.scss ya
// documenta que un chequeo ingenuo produce falsos positivos con fondos
// translucidos (rgba con alpha < 1), que son la norma en este tema.
const CONTRAST_UTILS_SRC = `
function parseColor(str) {
  if (!str) return null;
  const m = str.match(/rgba?\\(([^)]+)\\)/);
  if (!m) return null;
  const parts = m[1].split(',').map(s => parseFloat(s.trim()));
  const [r, g, b, a] = parts;
  return { r, g, b, a: a === undefined ? 1 : a };
}

function blend(fg, bg) {
  const a = fg.a;
  return {
    r: fg.r * a + bg.r * (1 - a),
    g: fg.g * a + bg.g * (1 - a),
    b: fg.b * a + bg.b * (1 - a),
    a: 1,
  };
}

function getEffectiveBackground(el) {
  const chain = [];
  let node = el;
  while (node) {
    chain.unshift(node);
    node = node.parentElement;
  }
  let acc = { r: 255, g: 255, b: 255, a: 1 };
  for (const n of chain) {
    const bg = parseColor(getComputedStyle(n).backgroundColor);
    if (bg && bg.a > 0) {
      acc = bg.a >= 1 ? bg : blend(bg, acc);
    }
  }
  return acc;
}

function relLuminance(c) {
  const lin = (v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
}

function contrastRatio(fgStr, bgColor) {
  const fg = parseColor(fgStr);
  if (!fg) return null;
  const fgOverBg = fg.a >= 1 ? fg : blend(fg, bgColor);
  const l1 = relLuminance(fgOverBg);
  const l2 = relLuminance(bgColor);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

window.__mdThemeAudit = function (selector) {
  const els = Array.from(document.querySelectorAll(selector));
  return els.slice(0, 5).map((el) => {
    const style = getComputedStyle(el);
    const bg = getEffectiveBackground(el);
    const ratio = contrastRatio(style.color, bg);
    const rect = el.getBoundingClientRect();
    return {
      selector,
      text: (el.textContent || '').trim().slice(0, 40),
      color: style.color,
      effectiveBg: \`rgb(\${Math.round(bg.r)}, \${Math.round(bg.g)}, \${Math.round(bg.b)})\`,
      ratio: ratio === null ? null : Math.round(ratio * 100) / 100,
      visible: rect.width > 0 && rect.height > 0,
    };
  });
};
`;

async function injectContrastUtils(page: Page) {
  await page.addScriptTag({ content: CONTRAST_UTILS_SRC });
}

async function auditSelectors(page: Page, selectors: string[]) {
  const results: any[] = [];
  for (const sel of selectors) {
    const rows = await page.evaluate((s) => (window as any).__mdThemeAudit(s), sel);
    results.push(...rows.filter((r: any) => r.visible));
  }
  return results;
}

async function isDarkModeActive(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.classList.contains('o_md_dark_mode'));
}

async function setDarkMode(page: Page, enable: boolean) {
  const current = await isDarkModeActive(page);
  if (current !== enable) {
    const toggle = page.locator('.o_md_dark_mode_toggle');
    await expect(toggle).toBeVisible({ timeout: 10_000 });
    await toggle.click();
    await page.waitForTimeout(300);
  }
  await expect(async () => {
    expect(await isDarkModeActive(page)).toBe(enable);
  }).toPass({ timeout: 5_000 });
  // El toggle real (dark_mode_toggle.js) tambien debe fijar [data-bs-theme]
  // -- verificamos que ambas senales queden consistentes, no solo la clase.
  const bsTheme = await page.evaluate(() => document.documentElement.getAttribute('data-bs-theme'));
  expect(bsTheme).toBe(enable ? 'dark' : null);
}

async function assertContrast(page: Page, viewName: string, selectors: string[]) {
  await injectContrastUtils(page);

  await setDarkMode(page, false);
  const lightResults = await auditSelectors(page, selectors);

  await setDarkMode(page, true);
  const darkResults = await auditSelectors(page, selectors);

  const failures = darkResults.filter((r) => r.ratio !== null && r.ratio < CONTRAST_THRESHOLD);

  if (failures.length > 0) {
    const shotPath = path.join(
      SCREENSHOT_DIR,
      `${viewName.replace(/[^a-z0-9]+/gi, '_')}.png`
    );
    await page.screenshot({ path: shotPath, fullPage: true });
    console.error(
      `[${viewName}] Contraste insuficiente en modo oscuro (umbral ${CONTRAST_THRESHOLD}:1):\n` +
        failures.map((f) => `  ${f.selector} "${f.text}" -> ${f.ratio}:1 (color=${f.color} sobre ${f.effectiveBg})`).join('\n') +
        `\nCaptura: ${shotPath}`
    );
  }

  console.log(
    `[${viewName}] claro: ${JSON.stringify(lightResults.map((r) => r.ratio))} | oscuro: ${JSON.stringify(darkResults.map((r) => r.ratio))}`
  );

  expect(failures, `${failures.length} elemento(s) con contraste < ${CONTRAST_THRESHOLD}:1 en modo oscuro`).toHaveLength(0);
}

// ─── Vistas ──────────────────────────────────────────────────────────────

test.describe('Auditoria de tema Claro/Oscuro', () => {
  test('Contactos — chatter y grupos de campos', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await page.locator('.o_kanban_record, .o_data_row').first().click();
    await expect(page.locator('.o_form_view')).toBeVisible({ timeout: 15_000 });
    await assertContrast(page, 'contactos_ficha', [
      '.o_form_label',
      '.o_field_widget input',
      '.o-mail-Chatter, .o_Chatter',
    ]);
  });

  test('Inventario > Productos — kanban con card COFEPRIS', async ({ page }) => {
    await page.goto('/odoo/action-stock.product_template_action_product');
    await expect(page.locator('.o_kanban_view, .o_list_view')).toBeVisible({ timeout: 15_000 });

    const kanbanToggle = page.locator('.o_switch_view.o_kanban').first();
    if (await kanbanToggle.isVisible().catch(() => false)) {
      await kanbanToggle.click();
      await page.waitForTimeout(500);
    }

    const hasRegCard = await page.locator('.o_md_product_kanban_card').count();
    test.skip(hasRegCard === 0, 'No hay productos con card COFEPRIS renderizada en este dataset — nada que auditar.');

    await assertContrast(page, 'inventario_kanban_producto', [
      '.md-kanban-product-name',
      '.md-kanban-price',
    ]);
  });

  test('Bajas de caducidad — statusbar del formulario', async ({ page }) => {
    await page.goto('/odoo/action-medicine_depot_scrap_batch.action_stock_scrap_batch');
    await expect(page.locator('.o_list_view, .o_kanban_view, .o_form_view')).toBeVisible({ timeout: 15_000 });

    const firstRecord = page.locator('.o_data_row, .o_kanban_record').first();
    if (await firstRecord.count() === 0) {
      test.skip(true, 'No hay registros de bajas de caducidad en este dataset.');
    }
    await firstRecord.click();
    await expect(page.locator('.o_form_statusbar')).toBeVisible({ timeout: 15_000 });

    await assertContrast(page, 'bajas_caducidad_statusbar', [
      '.o_form_statusbar .o_arrow_button',
      '.o_statusbar_buttons .btn',
    ]);
  });

  test('Systray — menu de actualizaciones de precio', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });

    const bell = page.locator('.pip_price_notification .o_nav_entry');
    test.skip((await bell.count()) === 0, 'purchase_invoice_parser no expuso el systray en esta sesion.');

    await bell.click();
    await expect(page.locator('.pip_dropdown')).toBeVisible({ timeout: 5_000 });

    await assertContrast(page, 'systray_price_notification', [
      '.pip_dropdown .pip_header span',
      '.pip_dropdown .pip_empty',
      '.pip_dropdown .pip_product',
      '.pip_dropdown .pip_old',
      '.pip_dropdown .pip_new',
    ]);
  });
});
