import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const FIXTURES_DIR = path.join(__dirname, 'fixtures');
const TEST_IMAGE = path.join(FIXTURES_DIR, 'tiny_test_image.png');

test.describe('Vision: Identificar producto desde foto', () => {

    test('endpoint rechaza solicitud sin archivo', async ({ page }) => {
        await page.goto('/odoo/contacts');
        await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

        const csrfToken = await page.evaluate(() => {
            // @ts-ignore
            return window.odoo.csrf_token || '';
        });

        const response = await page.request.post('/ai/identify_product_from_photo', {
            multipart: { csrf_token: csrfToken },
        });
        expect(response.status()).toBe(400);
        const body = await response.json();
        expect(body.success).toBe(false);
        expect(body).toHaveProperty('error');
    });

    test('endpoint rechaza archivo de texto', async ({ page }) => {
        await page.goto('/odoo/contacts');
        await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

        const csrfToken = await page.evaluate(() => {
            // @ts-ignore
            return window.odoo.csrf_token || '';
        });

        const response = await page.request.post('/ai/identify_product_from_photo', {
            multipart: {
                csrf_token: csrfToken,
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
        expect(body.error).toBe('invalid_format');
    });

    test('endpoint rechaza archivo muy grande (9MB)', async ({ page }) => {
        await page.goto('/odoo/contacts');
        await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

        const csrfToken = await page.evaluate(() => {
            // @ts-ignore
            return window.odoo.csrf_token || '';
        });

        const largeBuffer = Buffer.alloc(9 * 1024 * 1024, 0xff);
        const response = await page.request.post('/ai/identify_product_from_photo', {
            multipart: {
                csrf_token: csrfToken,
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
    });

    test('POST /ai/identify_product_from_photo con fixture responde JSON valido', async ({ page }) => {
        test.skip(
            !fs.existsSync(TEST_IMAGE),
            `Fixture no encontrado: ${TEST_IMAGE}`
        );

        test.setTimeout(360_000);

        await page.goto('/odoo/contacts');
        await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

        const csrfToken = await page.evaluate(() => {
            // @ts-ignore
            return window.odoo.csrf_token || '';
        });

        const imageBuffer = fs.readFileSync(TEST_IMAGE);
        const response = await page.request.post('/ai/identify_product_from_photo', {
            multipart: {
                csrf_token: csrfToken,
                image: {
                    name: 'test_product.png',
                    mimeType: 'image/png',
                    buffer: imageBuffer,
                },
            },
            timeout: 310_000,
        });

        const body = await response.json();

        expect(body).toHaveProperty('success');
        expect(body).toHaveProperty('identification');
        expect(body.identification).toHaveProperty('nombre_comercial');
        expect(body.identification).toHaveProperty('principio_activo');
        expect(body.identification).toHaveProperty('presentacion');
        expect(body.identification).toHaveProperty('cantidad_solicitada');
        expect(body).toHaveProperty('confidence');
        expect(body).toHaveProperty('match_status');
        expect(typeof body.confidence).toBe('number');

        const responseText = JSON.stringify(body);
        expect(responseText).not.toContain('disponible');
        expect(responseText).not.toContain('Disponible');

        if (body.success && body.product) {
            expect(body.product).toHaveProperty('A_la_mano');
            expect(typeof body.product.A_la_mano).toBe('number');
            expect(body.product.A_la_mano).toBeGreaterThanOrEqual(0);
        }

        console.log('Respuesta del endpoint:', JSON.stringify(body, null, 2));
    });

});
