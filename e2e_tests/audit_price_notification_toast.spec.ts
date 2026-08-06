import { test, expect, Page } from '@playwright/test';
import { execSync } from 'child_process';

/**
 * Verificacion del botón de notificaciones de precio (purchase_invoice_parser).
 * Price notification systray verification.
 *
 * Cubre las tres piezas que se auditaron/implementaron:
 *   1. Badge contador superpuesto al icono (no en flujo, al lado).
 *   2. Toast efimero de 4s disparado por el bus.
 *   3. Cierre al hacer click fuera (bug del __owl__.bdom interno).
 *
 * Los eventos de bus NO se simulan con un _sendone falso: se invoca
 * `_notify_price_changes`, el mismo metodo que corre en produccion al
 * confirmar una OC, para que la prueba cubra tambien la construccion del
 * payload y el ruteo por canal res.partner.
 */

const CREATED_IDS: number[] = [];

function odooShell(script: string, env: Record<string, string> = {}): string {
  const envPrefix = Object.entries(env)
    .map(([k, v]) => `-e ${k}=${v}`)
    .join(' ');
  const cmd =
    `PW=$(docker exec medicinedepot_dev_odoo printenv PASSWORD); ` +
    `docker exec -i ${envPrefix} medicinedepot_dev_odoo ` +
    `odoo shell -c /etc/odoo/odoo.conf -d medicinedepot_dev ` +
    `--db_host=db --db_user=odoo --db_password="$PW" --no-http < ${script}`;
  return execSync(cmd, { shell: '/bin/bash', encoding: 'utf-8', timeout: 120_000 });
}

/** Dispara `count` cambios de precio reales y devuelve los ids creados. */
function emitPriceChanges(count: number): number[] {
  const out = odooShell(
    '/opt/medicinedepot-odoo19-migration/e2e_tests/fixtures/emit_price_event.py',
    { COUNT: String(count) },
  );
  const m = out.match(/RESULT:CREATED:([\d,]*)/);
  if (!m) throw new Error(`El disparador no creo notificaciones. Salida:\n${out}`);
  const ids = m[1].split(',').filter(Boolean).map(Number);
  CREATED_IDS.push(...ids);
  return ids;
}

/**
 * Espera a que el componente del systray este montado y suscrito al bus.
 *
 * NO se instrumenta window.WebSocket: desde Odoo 16 el bus abre su socket
 * dentro de un SharedWorker, en otro contexto de ejecucion, asi que un parche
 * en `window` de la pagina nunca lo ve (esa fue la causa de que la primera
 * version de esta suite fallara en 4 tests por timeout).
 *
 * Proxy fiable: <li.pip_price_notification> solo se renderiza cuando
 * state.visible pasa a true, y eso ocurre despues de que el primer
 * get_unread() resolvio -- momento en el que bus.subscribe() (sincrono, en
 * setup()) ya se ejecuto hace rato.
 */
async function waitForBus(page: Page) {
  await page.waitForSelector('.pip_price_notification', {
    state: 'attached',
    timeout: 30_000,
  });
  // Margen para que el SharedWorker complete el handshake de suscripcion.
  // Si se emite antes, el evento igual se recupera: bus.bus persiste las
  // notificaciones y el cliente manda `last` al conectar. El margen solo
  // evita depender de ese camino de recuperacion en cada corrida.
  await page.waitForTimeout(2_000);
}


/**
 * Abre el panel de precios por la ruta REAL del usuario.
 *
 * md_navbar_style consolido este boton dentro del Control Center y dejo el
 * trigger nativo con opacity:0 / pointer-events:none en la barra exterior.
 * Clickearlo directamente falla ("<li> intercepts pointer events") y ademas
 * no representa lo que hace una persona: hay que abrir el Control Center y
 * pulsar el tile "Precios".
 */
async function openPricePanel(page: Page) {
  await page.locator('.o_mds_control_center_toggle').click();
  const tile = page.locator('.o_mds_cc_tile', { hasText: 'Precios' });
  await expect(tile).toBeVisible({ timeout: 10_000 });
  await tile.click();
  await expect(page.locator('.pip_dropdown')).toBeVisible({ timeout: 10_000 });
}


/**
 * Contraste WCAG. Se calcula en Node, NO dentro de page.evaluate().
 *
 * La primera version inyectaba el codigo de estas funciones como strings y
 * las reconstruia con eval() en la pagina; fallaba con "Cannot read
 * properties of null" porque el escape del regex no sobrevivia el viaje. El
 * navegador solo tiene que devolver dos strings de color: la aritmetica se
 * hace aqui, donde se puede depurar.
 */
function contrast(fg: string, bg: string): number {
  const parse = (c: string) => {
    const m = c.match(/[\d.]+/g);
    if (!m || m.length < 3) throw new Error(`Color no parseable: "${c}"`);
    return m.slice(0, 3).map(Number);
  };
  const lum = (rgb: number[]) => {
    const [r, g, b] = rgb.map((v) => {
      const sv = v / 255;
      return sv <= 0.03928 ? sv / 12.92 : Math.pow((sv + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const l1 = lum(parse(fg));
  const l2 = lum(parse(bg));
  return Number(((Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)).toFixed(2));
}

/**
 * Devuelve color de texto y fondo REALMENTE pintado detras del elemento.
 *
 * getComputedStyle().backgroundColor da rgba(0,0,0,0) en elementos
 * transparentes; medir contra eso produce ratios inventados. Se sube por los
 * ancestros hasta el primer fondo con alfa > 0.5.
 */
async function measure(page: Page, selector: string) {
  const { fg, bg } = await page.locator(selector).first().evaluate((el) => {
    const alphaOf = (c: string) => {
      const m = c.match(/[\d.]+/g);
      return m && m.length >= 4 ? Number(m[3]) : 1;
    };
    let node: HTMLElement | null = el as HTMLElement;
    let found = '';
    while (node && node !== document.documentElement) {
      const c = getComputedStyle(node).backgroundColor;
      if (alphaOf(c) > 0.5) {
        found = c;
        break;
      }
      node = node.parentElement;
    }
    return {
      fg: getComputedStyle(el).color,
      bg: found || getComputedStyle(document.body).backgroundColor || 'rgb(255, 255, 255)',
    };
  });
  return { fg, bg, ratio: contrast(fg, bg) };
}

async function setDarkMode(page: Page, on: boolean) {
  const isDark = await page.evaluate(() =>
    document.documentElement.classList.contains('o_md_dark_mode'),
  );
  if (isDark === on) return;
  // Ruta real del usuario: el tile del Control Center. El toggle nativo de
  // md_dark_mode esta oculto (display:none) por la consolidacion.
  await page.locator('.o_mds_control_center_toggle').click();
  await page.locator('.o_mds_cc_tile', { hasText: 'Modo Oscuro' }).click();
  await page.keyboard.press('Escape');
  await page.waitForFunction(
    (want) => document.documentElement.classList.contains('o_md_dark_mode') === want,
    on,
    { timeout: 10_000 },
  );
  await page.waitForTimeout(400);
}

test.beforeEach(async ({ page }) => {
  await page.goto('/odoo');
  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 30_000 });
});

test.afterAll(() => {
  // La prueba crea registros reales; se limpian para no dejar ruido en la
  // bandeja del usuario.
  if (!CREATED_IDS.length) return;
  const ids = CREATED_IDS.join(',');
  execSync(
    `PW=$(docker exec medicinedepot_dev_odoo printenv PASSWORD); ` +
      `docker exec -i medicinedepot_dev_odoo odoo shell -c /etc/odoo/odoo.conf ` +
      `-d medicinedepot_dev --db_host=db --db_user=odoo --db_password="$PW" --no-http ` +
      `<<< 'env["purchase.price.notification"].browse([${ids}]).unlink(); env.cr.commit()'`,
    { shell: '/bin/bash', encoding: 'utf-8', timeout: 120_000 },
  );
});

test('el contador aparece sobre el boton del Control Center', async ({ page }) => {
  // El badge del systray nativo existe y es correcto, pero md_navbar_style
  // deja ese trigger con opacity:0 -- el usuario nunca lo ve. Lo que hay que
  // verificar es la burbuja repintada sobre el Control Center.
  await waitForBus(page);
  const toggle = page.locator('.o_mds_control_center_toggle');
  await expect(toggle).toBeVisible({ timeout: 20_000 });

  emitPriceChanges(1);

  const badge = page.locator('.o_mds_cc_toggle_badge');
  await expect(badge).toBeVisible({ timeout: 20_000 });

  const count = parseInt((await badge.innerText()).trim(), 10);
  expect(count).toBeGreaterThan(0);

  const icon = toggle.locator('i.fa-sliders');
  const iconBox = (await icon.boundingBox())!;
  const badgeBox = (await badge.boundingBox())!;

  // Superpuesto al icono, no en flujo a su lado.
  expect(badgeBox.x).toBeLessThan(iconBox.x + iconBox.width);
  expect(badgeBox.y).toBeLessThan(iconBox.y + iconBox.height / 2);

  // La regla de tipografia del navbar no debe desbordarlo.
  const styles = await badge.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { fontSize: cs.fontSize, transform: cs.textTransform, ls: cs.letterSpacing };
  });
  expect(parseFloat(styles.fontSize)).toBeLessThanOrEqual(10);
  expect(styles.transform).toBe('none');

  // Y el badge cabe dentro de su circulo.
  expect(badgeBox.width).toBeLessThanOrEqual(28);

  await page.screenshot({
    path: 'screenshots/pip_cc_badge.png',
    clip: {
      x: Math.max(0, iconBox.x - 40),
      y: Math.max(0, iconBox.y - 20),
      width: 120,
      height: 60,
    },
  });
  console.log(`[badge] contador=${count} fontSize=${styles.fontSize} w=${badgeBox.width}`);
});

test('el tile de Precios dentro del panel tambien muestra el contador', async ({ page }) => {
  await waitForBus(page);
  emitPriceChanges(1);
  await expect(page.locator('.o_mds_cc_toggle_badge')).toBeVisible({ timeout: 20_000 });

  await page.locator('.o_mds_control_center_toggle').click();
  const tile = page.locator('.o_mds_cc_tile', { hasText: 'Precios' });
  await expect(tile).toBeVisible();
  await expect(tile.locator('.o_mds_cc_badge')).toBeVisible();

  await page.screenshot({ path: 'screenshots/pip_cc_panel_badge.png' });
});

test('un cambio de precio dispara un toast que se cierra solo a los 4s', async ({ page }) => {
  await waitForBus(page);

  const toast = page.locator('.o_notification');
  await expect(toast).toHaveCount(0);

  emitPriceChanges(1);

  // Aparece
  await expect(toast).toHaveCount(1, { timeout: 20_000 });
  const appearedAt = Date.now();

  const body = await toast.innerText();
  // Contenido real: producto, precios y proveedor — no un placeholder.
  expect(body).toMatch(/→/);
  expect(body).toMatch(/%/);
  expect(body.trim().length).toBeGreaterThan(10);

  await page.screenshot({ path: 'screenshots/pip_toast_visible.png' });

  // Un costo al alza va en rojo (danger): erosiona margen.
  await expect(
    toast.locator('.text-bg-danger, .border-danger, .bg-danger').first(),
  ).toBeVisible({ timeout: 5_000 });

  // Se cierra solo. autocloseDelay=4000 => debe seguir vivo a los 2.5s
  // y haber desaparecido antes de los 8s.
  await page.waitForTimeout(2_500);
  await expect(toast).toHaveCount(1);

  await expect(toast).toHaveCount(0, { timeout: 8_000 });
  const lifetimeMs = Date.now() - appearedAt;

  // Margen amplio a proposito: mide latencia de render + polling de
  // Playwright, no solo el timer. Lo que se valida es "efimero, ~4s",
  // no una precision de milisegundos que el navegador no garantiza.
  expect(lifetimeMs).toBeGreaterThan(3_000);
  expect(lifetimeMs).toBeLessThan(9_000);
  console.log(`[toast] vida observada: ${lifetimeMs}ms`);
});

test('varios cambios simultaneos se agrupan en un solo toast', async ({ page }) => {
  await waitForBus(page);

  const toast = page.locator('.o_notification');
  await expect(toast).toHaveCount(0);

  const ids = emitPriceChanges(3);
  test.skip(ids.length < 2, 'La OC de prueba no tiene suficientes lineas');

  await expect(toast).toHaveCount(1, { timeout: 20_000 });
  const body = await toast.innerText();
  expect(body).toMatch(new RegExp(`${ids.length}\\s+actualizaciones`, 'i'));

  await page.screenshot({ path: 'screenshots/pip_toast_batched.png' });

  // Un solo toast, no una avalancha de N.
  await page.waitForTimeout(1_000);
  await expect(toast).toHaveCount(1);
});

test('el panel se cierra al hacer click fuera', async ({ page }) => {
  await waitForBus(page);
  emitPriceChanges(1);

  const dropdown = page.locator('.pip_dropdown');
  await openPricePanel(page);

  // Click en una zona neutra del contenido principal.
  await page.locator('.o_action_manager').click({ position: { x: 300, y: 300 } });

  await expect(dropdown).toHaveCount(0, { timeout: 5_000 });

  // Y NO se reabre: el workaround retirado de md_navbar_style
  // re-clickeaba el trigger, lo que provocaba un doble toggle.
  await page.waitForTimeout(1_000);
  await expect(dropdown).toHaveCount(0);
});

test('el panel muestra contenido real con variacion porcentual', async ({ page }) => {
  await waitForBus(page);
  emitPriceChanges(1);

  const dropdown = page.locator('.pip_dropdown');
  await openPricePanel(page);

  const firstItem = dropdown.locator('.pip_item').first();
  await expect(firstItem).toBeVisible();

  const delta = firstItem.locator('.pip_delta');
  await expect(delta).toBeVisible();
  const deltaText = await delta.innerText();
  expect(deltaText).toMatch(/[+-]?\d+\.\d%|nuevo/);

  await page.screenshot({ path: 'screenshots/pip_panel_content.png' });
  console.log(`[panel] primera fila: ${(await firstItem.innerText()).replace(/\n/g, ' | ')}`);
});


// ── Tonos en modo claro y oscuro ────────────────────────────────────────
for (const mode of ['claro', 'oscuro'] as const) {
  const dark = mode === 'oscuro';

  test(`tonos legibles del toast en modo ${mode}`, async ({ page }) => {
    await waitForBus(page);
    await setDarkMode(page, dark);

    emitPriceChanges(1);
    const toast = page.locator('.o_notification');
    await expect(toast).toHaveCount(1, { timeout: 20_000 });

    await page.screenshot({ path: `screenshots/pip_toast_${mode}.png` });

    // Odoo 19 NO tiene .o_notification_title: el titulo se concatena dentro
    // de .o_notification_content (ver notification.xml, con un TODO del
    // propio Odoo para eliminarlo). Medir un selector inexistente hacia que
    // el test colgara 60s en lugar de fallar con algo util.
    const body = await measure(page, '.o_notification .o_notification_content');
    const surface = await measure(page, '.o_notification');
    console.log(`[toast ${mode}] texto fg=${body.fg} bg=${body.bg} ratio=${body.ratio}`);
    console.log(`[toast ${mode}] superficie bg=${surface.bg}`);

    const shown = await page.locator('.o_notification_content').innerText();
    console.log(`[toast ${mode}] contenido="${shown.replace(/\n/g, ' ')}"`);
    // Contenido real, no placeholder: precios y variacion.
    expect(shown).toMatch(/→/);
    expect(shown).toMatch(/%/);

    // WCAG AA para texto normal.
    expect(body.ratio).toBeGreaterThanOrEqual(4.5);
  });

  test(`tonos legibles del panel y del contador en modo ${mode}`, async ({ page }) => {
    await waitForBus(page);
    await setDarkMode(page, dark);

    emitPriceChanges(1);
    await expect(page.locator('.o_mds_cc_toggle_badge')).toBeVisible({ timeout: 20_000 });

    const badge = await measure(page, '.o_mds_cc_toggle_badge');
    console.log(`[badge ${mode}] fg=${badge.fg} bg=${badge.bg} ratio=${badge.ratio}`);
    // Texto pequeño en negrita: AA large (3:1) es el umbral aplicable.
    expect(badge.ratio).toBeGreaterThanOrEqual(3);

    await openPricePanel(page);
    await page.screenshot({ path: `screenshots/pip_panel_${mode}.png` });

    const product = await measure(page, '.pip_dropdown .pip_item .pip_product');
    const newPrice = await measure(page, '.pip_dropdown .pip_item .pip_new');
    const delta = await measure(page, '.pip_dropdown .pip_item .pip_delta');
    const meta = await measure(page, '.pip_dropdown .pip_item .pip_meta');

    for (const [name, m] of Object.entries({ product, newPrice, delta, meta })) {
      console.log(`[panel ${mode}] ${name} fg=${m.fg} bg=${m.bg} ratio=${m.ratio}`);
    }

    expect(product.ratio).toBeGreaterThanOrEqual(4.5);
    expect(newPrice.ratio).toBeGreaterThanOrEqual(3);
    expect(delta.ratio).toBeGreaterThanOrEqual(3);
    expect(meta.ratio).toBeGreaterThanOrEqual(3);
  });
}
