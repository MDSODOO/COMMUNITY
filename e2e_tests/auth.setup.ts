import { test as setup, expect } from '@playwright/test';
import path from 'path';

const STORAGE_STATE = path.join(__dirname, '.auth', 'odoo-session.json');
const DB = process.env.ODOO_DB ?? 'medicinedepot_dev';
const LOGIN = process.env.ODOO_LOGIN ?? 'admin';
const PASSWORD = process.env.ODOO_PASSWORD ?? 'admin';

// Autentica una sola vez y reutiliza la sesion en todos los tests.
// Authenticates once and reuses the session across every test.
setup('autenticar en Odoo / authenticate against Odoo', async ({ page }) => {
  await page.goto('/web/login');

  // Instancias multi-BD muestran un selector de base de datos antes del login.
  // Multi-DB instances show a database selector before the login form.
  const dbField = page.locator('input[name="db"]');
  if (await dbField.isVisible().catch(() => false)) {
    await dbField.fill(DB);
  }

  await page.locator('input[name="login"]').fill(LOGIN);
  await page.locator('input[name="password"]').fill(PASSWORD);
  // Acotado al formulario de login: la pagina tiene otros button[type=submit]
  // (buscadores) que hacian ambiguo el selector generico.
  // Scoped to the login form: the page has other button[type=submit] elements
  // (search boxes) that made the generic selector ambiguous.
  await page.locator('form:has(input[name="password"]) button[type="submit"]').click();

  // Login exitoso = llegamos al backend (menu principal visible).
  // Successful login = we land in the backend (main menu visible).
  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 20_000 });

  await page.context().storageState({ path: STORAGE_STATE });
});
