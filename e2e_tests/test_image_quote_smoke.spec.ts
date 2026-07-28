import { test, expect } from '@playwright/test';

/**
 * Smoke test estructural: la vista de "Cotizaciones por imagen (IA)" carga
 * sin error para staff. No depende de datos especificos (el flujo real de
 * imagen->extraccion->match->cotizacion se valido manualmente end-to-end
 * el 2026-07-28 -- ver docs/AI_MODEL_ODOO_CONFIG.md §7.1 -- una prueba
 * automatizada de ese flujo completo necesitaria fixtures propios, no
 * datos creados a mano en dev).
 */
test('vista de cotizaciones por imagen carga sin error', async ({ page }) => {
  await page.goto('/odoo/action-local_ai_connector.action_image_quote_request');
  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });
  await expect(page.locator('.o_list_view, .o_kanban_view')).toBeVisible({ timeout: 15000 });
});
