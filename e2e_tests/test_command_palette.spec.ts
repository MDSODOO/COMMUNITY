import { test, expect } from '@playwright/test';

/**
 * El comando "Copiloto de inventario (IA local)" se registra via useCommand
 * (mismo mecanismo nativo de Odoo que cualquier otro comando del Ctrl+K/
 * Alt+Espacio). Se abre la paleta invocando el servicio directamente en vez
 * de simular la tecla: Ctrl+K resulto intermitente en Chromium headless
 * (confirmado en desarrollo -- a veces el navegador headless no despacha el
 * evento de forma consistente, sin ningun error de JS de por medio). Esto
 * es una particularidad del entorno de automatizacion, no del producto --
 * Ctrl+K/Alt+Espacio es el atajo estandar de Odoo, ya probado en produccion
 * durante años. Esta prueba valida lo que realmente importa: que el
 * comando este bien registrado y abra el dialogo correcto.
 */
test('comando "Copiloto de inventario" esta registrado y abre el dialogo', async ({ page }) => {
  await page.goto('/odoo/contacts');
  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

  await page.evaluate(() => {
    // @ts-ignore
    window.odoo.__WOWL_DEBUG__.root.env.services.command.openMainPalette();
  });

  const searchInput = page.locator('.o_command_palette_search input');
  await expect(searchInput).toBeVisible({ timeout: 5000 });
  await searchInput.fill('copiloto');

  const item = page.getByText('Copiloto de inventario (IA local)');
  await expect(item).toBeVisible({ timeout: 5000 });
  await item.click();

  const dialog = page.locator('.modal-dialog:has-text("Copiloto de inventario")');
  await expect(dialog).toBeVisible({ timeout: 5000 });
});
