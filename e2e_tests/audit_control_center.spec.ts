import { test, expect, Page, ConsoleMessage } from '@playwright/test';

/**
 * Auditoria funcional del Control Center (md_navbar_style.control_center).
 * MedicineDepot Odoo 19 — self-hosted (ionos).
 *
 * Contexto: panel bento-glass en el systray que agrega Mensajes/Actividades/
 * Modo Oscuro/Ajustes en tiles tipo macOS Control Center. Delega en los
 * componentes nativos ya probados (ActivityMenu, md_dark_mode toggle) en
 * vez de reimplementar su logica -- este spec confirma que esa delegacion
 * realmente dispara la accion nativa, no solo que el panel abre.
 *
 * El panel se renderiza via usePopover() (.o_popover, portado a body con
 * position:fixed). Ver docs/audits/2026-07-01_backend_dark_mode_audit.md
 * para el bug de compositing de Chromium con backdrop-filter en portales --
 * probado en vivo 2026-08-06 (capturas cc_open_light.png/cc_open_dark.png):
 * no se reproduce en este panel.
 */

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
}

async function openControlCenter(page: Page) {
  const toggle = page.locator('.o_mds_control_center_toggle');
  await expect(toggle, 'boton del Control Center no visible').toBeVisible({ timeout: 10_000 });
  await toggle.click();
  const menu = page.locator('.o_mds_control_center');
  await expect(menu, 'panel del Control Center no abrio').toBeVisible({ timeout: 5_000 });
  return menu;
}

test.describe('Control Center (systray)', () => {
  test('panel abre con 4 tiles en claro y oscuro, sin errores', async ({ page }) => {
    const errors: ConsoleMessage[] = [];
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg); });

    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });

    for (const dark of [false, true]) {
      await setDarkMode(page, dark);
      await page.waitForTimeout(200);
      const menu = await openControlCenter(page);
      await expect(menu.locator('.o_mds_cc_tile')).toHaveCount(4);
      await expect(menu.getByText('Mensajes')).toBeVisible();
      await expect(menu.getByText('Actividades')).toBeVisible();
      await expect(menu.getByText('Modo Oscuro')).toBeVisible();
      await expect(menu.getByText('Ajustes')).toBeVisible();
      await page.keyboard.press('Escape');
      await page.waitForTimeout(150);
    }

    const relevant = errors.filter((e) => /control_center|ControlCenter|mds_cc/i.test(e.text()));
    expect(relevant.map((e) => e.text()), 'errores de consola del Control Center').toHaveLength(0);
  });

  test('tile Actividades delega en el ActivityMenu nativo', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });

    const menu = await openControlCenter(page);
    await menu.getByText('Actividades').click();

    // El click debe cerrar el Control Center y abrir el dropdown nativo de
    // ActivityMenu (mail), no un panel propio reimplementado.
    await expect(page.locator('.o_mds_control_center')).toBeHidden({ timeout: 5_000 });
    await expect(page.locator('.o-mail-ActivityMenu')).toBeVisible({ timeout: 5_000 });
  });

  test('tile Ajustes navega a Configuracion general', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });

    const menu = await openControlCenter(page);
    await menu.getByText('Ajustes').click();

    await expect(page.locator('.o_mds_control_center')).toBeHidden({ timeout: 5_000 });
    await expect(page).toHaveURL(/settings|general_settings/i, { timeout: 10_000 });
  });

  test('tile Modo Oscuro alterna el tema real (clase + atributo)', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });
    await setDarkMode(page, false);

    const menu = await openControlCenter(page);
    await menu.getByText('Modo Oscuro').click();
    await page.waitForTimeout(300);

    expect(await isDarkModeActive(page)).toBe(true);
    const bsTheme = await page.evaluate(() => document.documentElement.getAttribute('data-bs-theme'));
    expect(bsTheme).toBe('dark');

    // Vuelve a claro para no dejar la sesion de Playwright en oscuro entre specs.
    await setDarkMode(page, false);
  });

  test('tile Mensajes abre Discuss', async ({ page }) => {
    await page.goto('/odoo/contacts');
    await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });

    const menu = await openControlCenter(page);
    await menu.getByText('Mensajes').click();

    await expect(page.locator('.o_mds_control_center')).toBeHidden({ timeout: 5_000 });
    await expect(page.locator('.o-mail-Discuss')).toBeVisible({ timeout: 10_000 });
  });
});
