import { test, expect } from '@playwright/test';

test('boton de copiloto de inventario funciona end-to-end', async ({ page }) => {
  await page.goto('/odoo/contacts');
  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

  const icon = page.locator('.o_ai_inventory_query_toggle');
  await expect(icon).toBeVisible({ timeout: 10000 });
  await icon.click();

  const dialog = page.locator('.modal-dialog:has-text("Copiloto de inventario")');
  await expect(dialog).toBeVisible({ timeout: 5000 });

  await page.screenshot({ path: '/tmp/claude-0/-root/8926d2e9-ead1-4b31-8c35-519fc76e1799/scratchpad/ai_dialog_open.png' });

  await dialog.locator('input[type="text"]').fill('cuanto hay a la mano del producto con codigo de barras 8051708031164?');
  await dialog.locator('button:has-text("Preguntar")').click();

  const alertBox = dialog.locator('.alert');
  await expect(alertBox).toBeVisible({ timeout: 60000 });
  const text = await alertBox.textContent();
  console.log('RESULTADO:', text);

  await page.screenshot({ path: '/tmp/claude-0/-root/8926d2e9-ead1-4b31-8c35-519fc76e1799/scratchpad/ai_dialog_result.png' });

  expect(text).toContain('A la mano');
});
