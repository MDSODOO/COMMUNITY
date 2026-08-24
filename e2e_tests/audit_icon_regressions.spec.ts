import { test, expect, Page } from '@playwright/test';

/**
 * Auditoria E2E de iconografia (2026-08-06/07).
 *
 * Verifica si los iconos "x" (remover filtro de busqueda, .oi-close) y
 * "vista movil" (systray del editor de Website, .fa-mobile) renderizan su
 * glifo real o si el font-family que necesitan (odoo_ui_icons / FontAwesome)
 * esta siendo pisado por los overrides tipograficos globales de los modulos
 * custom (candidato principal: md_navbar_style/navbar_style.scss, que fuerza
 * "Inter" con !important sobre selectores genericos como .btn, span y
 * button dentro de .o_main_navbar).
 *
 * No basta con mirar screenshots: dos iconos "rotos" visualmente pueden
 * tener causas distintas (font-family pisado vs. clase de icono ausente vs.
 * fuente no cargada). Este spec extrae el font-family REAL con el que el
 * navegador esta pintando cada icono (host element y su pseudo-elemento
 * ::before, que es donde vive el glifo) para diferenciar entre esos casos.
 */

interface IconProbe {
  found: boolean;
  tag?: string;
  className?: string;
  ownFontFamily?: string;
  beforeContent?: string;
  beforeFontFamily?: string;
}

async function probeIcon(page: Page, selector: string): Promise<IconProbe> {
  const el = page.locator(selector).first();
  if ((await el.count()) === 0) {
    return { found: false };
  }
  return el.evaluate((node) => {
    const cs = getComputedStyle(node);
    const before = getComputedStyle(node, '::before');
    return {
      found: true,
      tag: node.tagName,
      className: (node as HTMLElement).className,
      ownFontFamily: cs.fontFamily,
      beforeContent: before.content,
      beforeFontFamily: before.fontFamily,
    };
  });
}

test.describe('Auditoria de iconografia rota (fa-times / oi-close / fa-mobile)', () => {
  test('Icono "x" de remover filtro en vista de lista (.o_facet_remove, .oi-close)', async ({ page }) => {
    // Ordenes de Compra: ruta ya confirmada funcional en utils/odoo.ts
    // (openImportWizard) — la vista de RFQ (/odoo/purchase) no aplica bien
    // las extensiones de vista, mejor no reutilizar esa ruta aqui tampoco.
    await page.goto('/odoo/purchase-orders');
    await page.locator('.o_searchview_input').first().waitFor({ state: 'visible', timeout: 15_000 });

    // Genera un facet propio en vez de depender de que la vista ya traiga
    // uno por defecto — mas robusto si algun dia cambian los filtros
    // default de esta accion.
    await page.locator('.o_searchview_input').first().click();
    await page.locator('.o_searchview_input').first().fill('a');
    await page.keyboard.press('Enter');

    const facetRemove = page.locator('.o_searchview_facet .o_facet_remove').first();
    await expect(facetRemove).toBeVisible({ timeout: 10_000 });

    const probe = await probeIcon(page, '.o_searchview_facet .o_facet_remove');
    // eslint-disable-next-line no-console
    console.log('[audit_icon] o_facet_remove ->', JSON.stringify(probe, null, 2));

    await page.screenshot({ path: 'screenshots/audit_icon_facet_remove.png' });

    expect(probe.found, 'no se encontro .o_facet_remove en el DOM').toBe(true);
    expect(probe.className ?? '').toContain('oi-close');
    // El marcado usa oi-close (Odoo UI Icons), NO FontAwesome — si esto
    // falla, el font-family real fue pisado por otra regla.
    expect(
      probe.ownFontFamily ?? '',
      `font-family real en .o_facet_remove: "${probe.ownFontFamily}" — se esperaba que incluyera "odoo_ui_icons"`
    ).toContain('odoo_ui_icons');
  });

  test('Icono de "Vista movil" en el editor de Website (.o_mobile_preview, .fa-mobile)', async ({ page }) => {
    await page.goto('/odoo/website');

    const toggle = page.locator('.o_mobile_preview span.fa-mobile').first();
    await expect(toggle).toBeVisible({ timeout: 20_000 });

    const probe = await probeIcon(page, '.o_mobile_preview span.fa-mobile');
    // eslint-disable-next-line no-console
    console.log('[audit_icon] o_mobile_preview fa-mobile ->', JSON.stringify(probe, null, 2));

    await page.screenshot({ path: 'screenshots/audit_icon_mobile_preview.png' });

    expect(probe.found, 'no se encontro .o_mobile_preview span.fa-mobile en el DOM').toBe(true);
    // El marcado nativo de website/mobile_preview_systray.xml usa
    // "fa fa-2x fa-mobile" (FontAwesome clasico), NO odoo_ui_icons.
    expect(
      probe.ownFontFamily ?? '',
      `font-family real en .o_mobile_preview .fa-mobile: "${probe.ownFontFamily}" — se esperaba que incluyera "FontAwesome"`
    ).toContain('FontAwesome');
  });
});
