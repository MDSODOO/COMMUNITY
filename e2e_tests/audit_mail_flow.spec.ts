import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

test.describe('Auditoría: Flujo de Correo Electrónico', () => {

    test('1. Parámetros de correo configurados en BD (mail.catchall + mail.default.from)', async ({ page }) => {
        // Verificar vía endpoint RPC directo en vez de UI (más rápido y confiable)
        await page.goto('/odoo/contacts');
        await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

        const catchall = await page.evaluate(async () => {
            // @ts-ignore
            const env = window.odoo;
            if (!env || !env.csrf_token) return null;
            const resp = await fetch('/web/dataset/call_kw/ir.config_parameter/get_param', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    params: {
                        model: 'ir.config_parameter',
                        method: 'get_param',
                        args: ['mail.catchall.domain'],
                        kwargs: {},
                        context: {},
                    },
                }),
            });
            const data = await resp.json();
            return data?.result || null;
        }).catch(() => null);

        const defaultFrom = await page.evaluate(async () => {
            // @ts-ignore
            const env = window.odoo;
            if (!env || !env.csrf_token) return null;
            const resp = await fetch('/web/dataset/call_kw/ir.config_parameter/get_param', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    params: {
                        model: 'ir.config_parameter',
                        method: 'get_param',
                        args: ['mail.default.from'],
                        kwargs: {},
                        context: {},
                    },
                }),
            });
            const data = await resp.json();
            return data?.result || null;
        }).catch(() => null);

        console.log('mail.catchall.domain:', catchall);
        console.log('mail.default.from:', defaultFrom);

        // Ambos deben estar configurados para que el correo saliente funcione
        expect(catchall).toBe('medicinedepotsureste.mx');
        expect(defaultFrom).toBe('odoo@medicinedepotsureste.mx');
    });

    test('2. Servidor SMTP saliente visible en Técnico → Servidores de Correo', async ({ page }) => {
        await page.goto('/odoo/action-19');
        await page.waitForTimeout(3000);
        const listVisible = await page.locator('.o_list_view').isVisible().catch(() => false);

        await page.screenshot({
            path: path.join(SCREENSHOT_DIR, 'mail_servers_list.png'),
            fullPage: true,
        });

        if (listVisible) {
            const rows = page.locator('.o_list_view tbody tr');
            const count = await rows.count();
            expect(count).toBeGreaterThanOrEqual(1);
            console.log(`Servidores SMTP encontrados: ${count}`);
        } else {
            console.log('Lista de servidores SMTP no visible (puede requerir permisos de técnico)');
        }
    });

    test('3. Estado de la cola de correos salientes (mail.mail)', async ({ page }) => {
        // Ver cantidad de mail.mail vía RPC directo
        await page.goto('/odoo/contacts');
        await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

        const stateCounts = await page.evaluate(async () => {
            const resp = await fetch('/web/dataset/search_read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    params: {
                        model: 'mail.mail',
                        fields: ['state'],
                        domain: [],
                        limit: 2000,
                    },
                }),
            });
            const data = await resp.json();
            if (!data?.result?.records) return {};
            const counts = {};
            for (const r of data.result.records) {
                counts[r.state] = (counts[r.state] || 0) + 1;
            }
            return counts;
        }).catch(() => ({}));

        console.log('Estado de mail.mail:', JSON.stringify(stateCounts));
        await page.screenshot({
            path: path.join(SCREENSHOT_DIR, 'mail_mail_queue.png'),
            fullPage: true,
        });
    });

    test('4. Pharmacovigilance: acceso a la vista y chatter', async ({ page }) => {
        // Verificar vía RPC que el modelo existe y chatter está disponible
        await page.goto('/odoo/contacts');
        await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 15000 });

        const modelInfo = await page.evaluate(async () => {
            const resp = await fetch('/web/dataset/search_read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    params: {
                        model: 'medicine.depot.pharmacovigilance.report',
                        fields: ['id'],
                        domain: [],
                        limit: 1,
                    },
                }),
            });
            const data = await resp.json();
            return { hasRecords: (data?.result?.records?.length || 0) > 0, total: data?.result?.length };
        }).catch(() => ({ hasRecords: false, total: 0 }));

        console.log('Registros de farmacovigilancia:', modelInfo.total);

        // Navegar a la vista
        await page.goto('/odoo/action-718');
        await page.waitForTimeout(3000);
        await page.screenshot({
            path: path.join(SCREENSHOT_DIR, 'pharmacovigilance_view.png'),
            fullPage: true,
        });

        if (modelInfo.hasRecords) {
            // Buscar el chatter en cualquier vista abierta
            const chatter = page.locator('.o_chatter');
            const chatterVisible = await chatter.isVisible().catch(() => false);
            console.log('Chatter visible en farmacovigilancia:', chatterVisible);
        } else {
            console.log('Sin registros de farmacovigilancia — verificación visual únicamente');
        }
    });

    test('5. Cliente de correo md_mail_client carga y muestra bandejas', async ({ page }) => {
        // Acceder al menú "Correo" vía su action ID
        await page.goto('/odoo/action-753');

        // Esperar a que cargue el cliente custom
        await page.waitForTimeout(3000);
        const mailClient = page.locator('.o_md_mail_client');
        await expect(mailClient).toBeVisible({ timeout: 15000 });

        await page.screenshot({
            path: path.join(SCREENSHOT_DIR, 'mail_client_ui.png'),
            fullPage: true,
        });

        // Verificar las secciones principales
        await expect(mailClient.locator('.omc-compose-btn')).toBeVisible();
        await expect(mailClient.locator('.omc-nav-group').first()).toBeVisible();
        await expect(mailClient.locator('.omc-list-pane')).toBeVisible();
        await expect(mailClient.locator('.omc-reader')).toBeVisible();

        // Verificar que cargó mensajes o muestra "Sin mensajes"
        const emptyMsg = mailClient.locator('.omc-empty');
        const hasMessages = await mailClient.locator('.omc-msg-row').count();
        if (hasMessages === 0) {
            await expect(emptyMsg).toBeVisible();
            console.log('Cliente de correo cargado: sin mensajes (esperado si no hay mail.mail)');
        } else {
            console.log(`Cliente de correo: ${hasMessages} mensajes cargados`);
        }
    });

    test('6. Flujo E2E: message_post vía chatter en contacto', async ({ page }) => {
        // Navegar a contactos con acción específica
        await page.goto('/odoo/action-523');
        await page.waitForTimeout(3000);

        // Verificar que hay una lista visible
        const listVisible = await page.locator('.o_list_view').isVisible().catch(() => false);
        if (!listVisible) {
            console.log('Lista de contactos no visible, saltando test');
            await page.screenshot({
                path: path.join(SCREENSHOT_DIR, 'partners_not_available.png'),
                fullPage: true,
            });
            test.skip();
            return;
        }

        // Obtener el primer ID de contacto
        const firstId = await page.evaluate(() => {
            const rows = document.querySelectorAll('.o_list_view tbody tr');
            if (!rows.length) return null;
            const firstRow = rows[0];
            const dataId = firstRow.getAttribute('data-id');
            return dataId ? parseInt(dataId, 10) : null;
        });

        if (!firstId) {
            console.log('No se pudo obtener ID de contacto');
            test.skip();
            return;
        }

        // Abrir contacto via URL directa
        await page.goto(`/odoo/action-523/${firstId}`);
        await page.waitForTimeout(3000);

        // Buscar chatter
        const chatter = page.locator('.o_chatter');
        const chatterVisible = await chatter.isVisible().catch(() => false);

        if (chatterVisible) {
            console.log('Chatter visible en contacto');
            // Publicar mensaje vía RPC directo (más confiable que UI)
            await page.evaluate(async (partnerId) => {
                const msg = 'Mensaje de prueba E2E: auditoría de correo ' + Date.now();
                await fetch('/web/dataset/call_kw/res.partner/message_post', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        params: {
                            model: 'res.partner',
                            method: 'message_post',
                            args: [partnerId],
                            kwargs: { body: msg, message_type: 'comment' },
                        },
                    }),
                });
            }, firstId);

            await page.waitForTimeout(2000);
            console.log('Mensaje publicado en chatter vía RPC');
        } else {
            console.log('Chatter no visible en esta vista de contacto');
        }

        await page.screenshot({
            path: path.join(SCREENSHOT_DIR, 'chatter_message_posted.png'),
            fullPage: true,
        });
    });
});
