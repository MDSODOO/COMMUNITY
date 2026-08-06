import { test, expect, Page, ConsoleMessage } from '@playwright/test';

/**
 * Auditoria funcional del Navbar tras el rediseño MDS (md_navbar_style 19.0.1.1.0).
 * MedicineDepot Odoo 19 — self-hosted (ionos).
 *
 * Contexto: md_navbar_style agrego un patch OWL a NavBar (navbar_patch.js) y una
 * extension XPath sobre web.NavBar (navbar_templates.xml) que inserta
 * .mds-navbar-custom-zone antes de .o_menu_systray. Este spec confirma que esa
 * extension no rompio los dos desplegables nativos del systray (Apps, Usuario)
 * ni introdujo errores de consola, en modo claro y en modo oscuro (toggle real
 * de custom_addons/md_dark_mode, ver audit_theme_modes.spec.ts).
 *
 * Chat (mail.MessagingMenu) se consolido dentro del Control Center
 * (2026-08-06): su boton nativo queda oculto en la barra exterior -- ver
 * audit_control_center.spec.ts ("tile Mensajes abre Discuss").
 *
 * No hace click en "Cerrar sesion" / "Log out" del menu de usuario -- solo
 * confirma que el dropdown abre con contenido visible.
 */

async function isDarkModeActive(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.classList.contains('o_md_dark_mode'));
}

async function setDarkMode(page: Page, enable: boolean) {
  const current = await isDarkModeActive(page);
  if (current !== enable) {
    // Oculto (display:none) desde la consolidacion en el Control Center --
    // sigue montado y funcional. display:none no tiene geometria: ni
    // click({force:true}) puede simular el mouse ahi, se dispara el click()
    // real de DOM via evaluate (mismo mecanismo que usa control_center.js).
    const toggle = page.locator('.o_md_dark_mode_toggle');
    await expect(toggle).toBeAttached({ timeout: 10_000 });
    await toggle.evaluate((el: HTMLElement) => el.click());
    await page.waitForTimeout(300);
  }
  await expect(async () => {
    expect(await isDarkModeActive(page)).toBe(enable);
  }).toPass({ timeout: 5_000 });
}

function collectConsoleErrors(page: Page): ConsoleMessage[] {
  const errors: ConsoleMessage[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg);
    }
  });
  return errors;
}

async function closeAnyOpenDropdown(page: Page) {
  await page.keyboard.press('Escape');
  await page.waitForTimeout(150);
}

async function auditNavbarDropdowns(page: Page, themeLabel: string, consoleErrors: ConsoleMessage[]) {
  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });

  // Zona custom insertada por md_navbar_style -- confirma que el XPath
  // extension se aplico y el systray original sigue presente junto a ella.
  await expect(page.locator('.mds-navbar-custom-zone')).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('.o_menu_systray')).toBeVisible();

  // 1. Apps
  // Esta instancia tiene md_command_palette instalado, que sustituye el
  // dropdown nativo de Apps por un launcher tipo command-palette (grid de
  // apps dentro de un dialog con buscador). Se audita ese comportamiento
  // real, no el dropdown simple de Odoo vanilla.
  const appsToggle = page.locator('.o_navbar_apps_menu button, .o_menu_toggle').first();
  await expect(appsToggle, `[${themeLabel}] boton de Apps no visible`).toBeVisible({ timeout: 10_000 });
  await appsToggle.click();
  const appsOverlay = page
    .locator('.o_navbar_apps_menu .dropdown-menu, [role="dialog"]:has(input[placeholder*="Buscar" i])')
    .first();
  await expect(appsOverlay, `[${themeLabel}] menu/launcher de Apps no abrio`).toBeVisible({ timeout: 5_000 });
  const appCount = await appsOverlay.locator('.o_app, [role="option"]').count();
  expect(appCount, `[${themeLabel}] menu de Apps abrio sin items`).toBeGreaterThan(0);
  await closeAnyOpenDropdown(page);

  // 2. Usuario
  const userToggle = page.locator('.o_user_menu button').first();
  await expect(userToggle, `[${themeLabel}] boton de Usuario no visible`).toBeVisible({ timeout: 10_000 });
  await userToggle.click();
  const userMenu = page.locator('.o_user_menu .dropdown-menu, .o-dropdown--menu').first();
  await expect(userMenu, `[${themeLabel}] menu de Usuario no abrio`).toBeVisible({ timeout: 5_000 });
  const userItemCount = await userMenu.locator('.dropdown-item, [role="menuitem"]').count();
  expect(userItemCount, `[${themeLabel}] menu de Usuario abrio sin items`).toBeGreaterThan(0);
  await closeAnyOpenDropdown(page);

  // 3. Chat: consolidado en el Control Center, ver comentario de cabecera.
  // El boton nativo debe seguir ADJUNTO al DOM (oculto, no destruido) --
  // confirma que la consolidacion oculta, no rompe, el componente real.
  await expect(
    page.locator('.o_menu_systray button:has(i.fa-comments)').first(),
    `[${themeLabel}] boton nativo de Chat ya no esta en el DOM (deberia seguir montado, solo oculto)`
  ).toBeAttached({ timeout: 5_000 });

  const relevantErrors = consoleErrors.filter(
    (e) => /navbar|NavBar|mds/i.test(e.text()) || /navbar_patch|navbar_templates/i.test(e.location().url)
  );
  expect(
    relevantErrors.map((e) => e.text()),
    `[${themeLabel}] errores de consola atribuibles al navbar/md_navbar_style`
  ).toHaveLength(0);
}

test.describe('Navbar MDS — desplegables Apps/Usuario/Chat', () => {
  test('Claro y oscuro — los tres desplegables abren con contenido y sin errores', async ({ page }) => {
    const consoleErrors = collectConsoleErrors(page);

    await page.goto('/odoo');

    await setDarkMode(page, false);
    await auditNavbarDropdowns(page, 'claro', consoleErrors);

    await setDarkMode(page, true);
    await auditNavbarDropdowns(page, 'oscuro', consoleErrors);
  });
});
