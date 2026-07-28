import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config({ path: path.join(__dirname, '.env') });

const BASE_URL = process.env.ODOO_URL ?? 'http://localhost:8069';
const STORAGE_STATE = path.join(__dirname, '.auth', 'odoo-session.json');

/**
 * Suite de auditoria UI para purchase_invoice_parser.
 * UI audit suite for purchase_invoice_parser.
 *
 * fullyParallel:false porque cada test crea registros en la misma base de
 * datos Odoo (Ordenes de Compra, wizards) y correr en paralelo generaria
 * colisiones de estado. / fullyParallel:false because every test writes
 * records into the same Odoo database — parallel runs would collide.
 */
export default defineConfig({
  testDir: './',
  testMatch: /.*\.spec\.ts/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['list'],
  ],
  outputDir: 'test-results',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    // Captura automatica SOLO si el test falla (Paso 3).
    // Automatic capture ONLY on test failure (Step 3).
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: STORAGE_STATE,
      },
      dependencies: ['setup'],
    },
  ],
});
