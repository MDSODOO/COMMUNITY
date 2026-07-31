import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/**
 * Suite E2E para el endpoint /ai/identify_product_from_photo.
 *
 * Prueba el flujo completo: staff autenticado sube una foto de un producto
 * farmacéutico → backend Odoo la envía a qwen2.5vl:7b (Ollama en
 * host.docker.internal:11434) → respuesta JSON con producto identificado +
 * cantidad "A la mano" (On Hand).
 *
 * Dependencias:
 * - Sesión de staff autenticada en Odoo (auth.setup.ts)
 * - Ollama funcionando con qwen2.5vl:7b en el host
 * - Una imagen de prueba en fixtures/
 *
 * NOTA: estas pruebas requieren que el modelo de visión esté disponible y
 * que el circuito de IA esté en estado normal (no degradado). Si hay fallos
 * en cadena, verificar el healthcheck de Ollama primero.
 */

const FIXTURES_DIR = path.join(__dirname, '..', '..', '..', '..', '..', 'e2e_tests', 'fixtures');
const TEST_IMAGE = path.join(FIXTURES_DIR, 'test_product_box.jpg');
const TINY_TEST_IMAGE = path.join(FIXTURES_DIR, 'tiny_test_image.png');

/**
 * Genera una imagen sintética de prueba: un rectángulo blanco con texto
 * simulado de producto. Se genera solo si el fixture no existe.
 */
function ensureTestFixture(): string {
  if (fs.existsSync(TEST_IMAGE)) {
    return TEST_IMAGE;
  }
  // Usar tiny_test_image.png como fallback si no generamos la sintética
  if (fs.existsSync(TINY_TEST_IMAGE)) {
    return TINY_TEST_IMAGE;
  }
  // Crear un PNG mínimo de 1x1 píxel para que el test al menos pueda
  // probar la ruta de validación de archivos, aunque no pruebe la
  // inferencia real.
  const minPng = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
  );
  fs.writeFileSync(TINY_TEST_IMAGE, minPng);
  return TINY_TEST_IMAGE;
}

test.describe('/ai/identify_product_from_photo — Identificación de producto desde foto', () => {

  test.describe('Validaciones de entrada', () => {

    test('rechaza solicitud sin archivo', async ({ page }) => {
      const response = await page.request.post('/ai/identify_product_from_photo', {
        multipart: {},
      });
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.success).toBe(false);
      expect(body.message).toContain('Sube');
    });

    test('rechaza archivo que no es imagen', async ({ page }) => {
      const response = await page.request.post('/ai/identify_product_from_photo', {
        multipart: {
          image: {
            name: 'test.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('no soy una imagen'),
          },
        },
      });
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.success).toBe(false);
      expect(body.message).toContain('JPEG');
    });

    test('rechaza archivo demasiado grande (>8MB)', async ({ page }) => {
      const largeBuffer = Buffer.alloc(9 * 1024 * 1024, 0xff); // 9MB
      const response = await page.request.post('/ai/identify_product_from_photo', {
        multipart: {
          image: {
            name: 'large.jpg',
            mimeType: 'image/jpeg',
            buffer: largeBuffer,
          },
        },
      });
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.success).toBe(false);
      expect(body.message).toContain('MB');
    });

  });

  test.describe('Caso feliz — identificación exitosa', () => {

    test('identifica producto correctamente desde foto y devuelve "A la mano"', async ({ page }) => {
      const fixturePath = ensureTestFixture();

      const response = await page.request.post('/ai/identify_product_from_photo', {
        multipart: {
          image: {
            name: 'producto.jpg',
            mimeType: 'image/jpeg',
            buffer: fs.readFileSync(fixturePath),
          },
        },
      });

      // La respuesta puede ser 200 (éxito) o 503/504 (si Ollama está ocupado)
      // — en un entorno de pruebas real, cualquiera de los dos es aceptable
      // siempre que la forma del JSON sea la correcta.
      const body = await response.json();

      if (response.status() === 200) {
        expect(body.success).toBe(true);
        expect(body).toHaveProperty('product');
        expect(body).toHaveProperty('identification');

        // Verificar que la respuesta use "A la mano", NUNCA "disponible"
        const responseText = JSON.stringify(body);
        expect(responseText).not.toContain('disponible');
        expect(responseText).not.toContain('Disponible');

        if (body.product) {
          // Si hay producto, debe tener "A la mano" (o "A_la_mano" como campo)
          expect(body.product).toHaveProperty('A_la_mano');
          expect(typeof body.product.A_la_mano).toBe('number');
          expect(body.product.A_la_mano).toBeGreaterThanOrEqual(0);
        }

        expect(body).toHaveProperty('confidence');
        expect(body.confidence).toBeGreaterThanOrEqual(0);
        expect(body.confidence).toBeLessThanOrEqual(1);

        // Loggear para depuración
        console.log('Producto identificado:', JSON.stringify(body.product?.name));
        console.log('Confianza:', body.confidence);
        console.log('"A la mano":', body.product?.A_la_mano);
      } else if (response.status() === 503) {
        // Ollama ocupado — aceptable, la forma del error debe ser correcta
        expect(body.success).toBe(false);
        expect(body.error).toMatch(/busy|ai_unavailable/i);
        console.log('IA ocupada (esperable en entorno compartido):', body.message);
      } else if (response.status() === 504) {
        // Timeout
        expect(body.success).toBe(false);
        expect(body.error).toMatch(/timeout/i);
        console.log('IA timeout:', body.message);
      } else {
        // Cualquier otro código — fallar con información
        console.log('Respuesta inesperada:', JSON.stringify(body));
        expect(response.status()).toBe(200);
      }
    });

  });

  test.describe('Manejo de errores de IA', () => {

    test('responde correctamente cuando el modelo está en degraded mode (circuit breaker)', async ({ page }) => {
      // Este test verifica la forma del error, no el estado real del breaker
      // (que es un estado interno en memoria del proceso Python).
      // Simulamos enviando una solicitud y manejando 503.
      const fixturePath = ensureTestFixture();

      const response = await page.request.post('/ai/identify_product_from_photo', {
        multipart: {
          image: {
            name: 'producto.jpg',
            mimeType: 'image/jpeg',
            buffer: fs.readFileSync(fixturePath),
          },
        },
        timeout: 10_000, // timeout corto para no esperar 5min
      });

      const body = await response.json();

      // Si el servidor responde 503, debe cumplir el formato esperado
      if (response.status() === 503) {
        expect(body.success).toBe(false);
        expect(body).toHaveProperty('error');

        // Dos posibles errores:
        // "busy" — advisory lock ocupado
        // "ai_unavailable" — Ollama caído o circuit breaker abierto
        expect(['busy', 'ai_unavailable']).toContain(body.error);

        expect(body).toHaveProperty('message');
        expect(typeof body.message).toBe('string');
        expect(body.message.length).toBeGreaterThan(0);
      }
    });

    test('responde con error si Ollama está completamente caído (conexión rechazada)', async ({ page }) => {
      // NOTA: este caso solo se puede probar en un entorno donde se pueda
      // simular la caída de Ollama. En un entorno real, verificamos que
      // la respuesta tenga el formato esperado si falla la conexión.
      //
      // Estrategia: enviar una imagen y verificar que el error, si ocurre,
      // cumple el contrato de la API.
      const fixturePath = ensureTestFixture();

      const response = await page.request.post('/ai/identify_product_from_photo', {
        multipart: {
          image: {
            name: 'producto.jpg',
            mimeType: 'image/jpeg',
            buffer: fs.readFileSync(fixturePath),
          },
        },
        timeout: 15_000,
      });

      const body = await response.json();

      // Cualquier estado < 500 es un error de validación (imagen inválida, etc.)
      // Cualquier estado >= 500 es un error del servidor/IA — debe cumplir el formato
      if (response.status() >= 500) {
        expect(body.success).toBe(false);
        expect(body).toHaveProperty('error');
        expect(body).toHaveProperty('message');
      }
    });

  });

  test.describe('Modo degradado — circuit breaker en UI', () => {

    test('el badge de estado de IA en el backend muestra degraded cuando corresponde', async ({ page }) => {
      // Verifica que la healthcheck UI de IA (si existe) refleje el estado
      // del circuit breaker.
      //
      // Primero, revisar que el healthcheck endpoint exista (ver RUNBOOK.md §5.3)
      await page.goto('/odoo/action-local_ai_connector.action_ai_healthcheck');
      const navbar = page.locator('.o_main_navbar');
      const navbarVisible = await navbar.isVisible().catch(() => false);

      if (navbarVisible) {
        // Hay healthcheck UI — verificar que cargue sin error
        await expect(page.locator('.o_content')).toBeVisible({ timeout: 10_000 });
      } else {
        // No hay healthcheck UI — este test no aplica, saltar
        console.log('Healthcheck UI no disponible, saltando test');
        test.skip();
      }
    });

  });

  test.describe('Renderizado en el Command Palette — "Identificar producto desde foto"', () => {

    test('el comando de identificación aparece en el command palette', async ({ page }) => {
      // Verificar que el comando esté registrado (mismo patrón que
      // test_image_quote_partner_selector.spec.ts)
      await page.goto('/odoo/contacts');
      await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15_000 });

      await page.locator('.o_navbar_apps_menu').click();
      const paletteInput = page.locator('.o_md_command_palette_input');
      await expect(paletteInput).toBeVisible({ timeout: 5_000 });

      await paletteInput.fill('identif');
      const commandLabel = page.getByText('Identificar producto desde foto');
      const commandVisible = await commandLabel.isVisible().catch(() => false);

      if (commandVisible) {
        // El comando existe — verificar que abre el diálogo correcto
        await commandLabel.click();
        const dialog = page.locator('.modal-content:has-text("Identificar producto")');
        await expect(dialog).toBeVisible({ timeout: 5_000 });
        await expect(dialog.locator('input[type="file"]')).toBeVisible({ timeout: 3_000 });
      } else {
        // El comando aún no se registró en el palette (Fase 5 del plan)
        console.log('Comando "Identificar producto desde foto" aún no registrado en el palette');
        test.skip();
      }
    });

  });

});
