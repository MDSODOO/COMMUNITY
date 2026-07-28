import { test, expect, Locator } from '@playwright/test';
import fs from 'fs';
import path from 'path';

/**
 * Auditoria de la configuracion nativa de Asistencias (hr_attendance) en
 * Ajustes > Attendances. NO modifica nada -- solo lee el estado actual de
 * cada campo del bloque `.app_settings_block[data-key="hr_attendance"]` y lo
 * exporta a docs/ATTENDANCE_BASELINE.md, entre los marcadores
 * BASELINE:START/END (la seccion de arquitectura del modulo custom, escrita
 * a mano debajo de esos marcadores, no se toca).
 *
 * Requisito de permisos: el usuario debe pertenecer a
 * hr_attendance.group_hr_attendance_manager -- esa vista (ver
 * res_config_settings_views.xml de hr_attendance) esta gateada con
 * `groups=` a nivel de <app>, no solo a nivel de campo. Sin ese grupo el tab
 * "Attendances" no existe en el DOM y el test fallara en el primer `expect`
 * con un mensaje claro en vez de un timeout generico.
 *
 * Audit of hr_attendance's native configuration under Settings >
 * Attendances. Read-only -- it only reads the current state of every field
 * inside `.app_settings_block[data-key="hr_attendance"]` and exports it to
 * docs/ATTENDANCE_BASELINE.md, between the BASELINE:START/END markers (the
 * custom-module architecture section written by hand below those markers
 * is left untouched).
 *
 * Permission requirement: the user must belong to
 * hr_attendance.group_hr_attendance_manager -- that view (see
 * hr_attendance's res_config_settings_views.xml) is gated with `groups=` at
 * the <app> level, not just per-field. Without that group the "Attendances"
 * tab does not exist in the DOM and the test fails at the first `expect`
 * with a clear message instead of a generic timeout.
 */

const BASELINE_DOC = path.join(__dirname, '..', 'docs', 'ATTENDANCE_BASELINE.md');
const START_MARKER = '<!-- BASELINE:START (auto-generado, no editar a mano / auto-generated, do not hand-edit) -->';
const END_MARKER = '<!-- BASELINE:END -->';

type FieldKind = 'select' | 'boolean' | 'text' | 'radio';

interface FieldSpec {
  name: string;
  label: string;
  kind: FieldKind;
}

// Campos tomados directamente de hr_attendance/models/res_config_settings.py
// y hr_attendance/views/res_config_settings_views.xml (Odoo 19 Community,
// verificado en el contenedor medicinedepot_dev_odoo).
// Fields taken directly from hr_attendance/models/res_config_settings.py and
// hr_attendance/views/res_config_settings_views.xml (Odoo 19 Community,
// verified inside the medicinedepot_dev_odoo container).
const FIELDS: FieldSpec[] = [
  { name: 'attendance_kiosk_mode', label: 'Modo Quiosco / Kiosk Mode', kind: 'select' },
  { name: 'attendance_from_systray', label: 'Asistencias desde el Backend / Attendances from Backend', kind: 'boolean' },
  { name: 'auto_check_out', label: 'Salida automatica / Automatic Check-Out', kind: 'boolean' },
  { name: 'auto_check_out_tolerance', label: 'Tolerancia salida automatica (hrs) / Auto check-out tolerance (hrs)', kind: 'text' },
  { name: 'absence_management', label: 'Gestion de ausencias / Absence Management', kind: 'boolean' },
  { name: 'attendance_device_tracking', label: 'Rastreo de dispositivo/ubicacion / Device & Location Tracking', kind: 'boolean' },
  { name: 'attendance_barcode_source', label: 'Fuente de codigo de barras (Kiosco) / Barcode source (Kiosk)', kind: 'select' },
  { name: 'attendance_kiosk_delay', label: 'Tiempo de mensaje (seg) / Display time (sec)', kind: 'text' },
  { name: 'attendance_kiosk_use_pin', label: 'Usar PIN en Quiosco / Use PIN in Kiosk', kind: 'boolean' },
  { name: 'hr_attendance_display_overtime', label: 'Mostrar horas extra / Display Extra Hours', kind: 'boolean' },
  { name: 'attendance_overtime_validation', label: 'Validacion de horas extra / Extra Hours Validation', kind: 'radio' },
];

interface FieldResult extends FieldSpec {
  value: string;
  visible: boolean;
}

/**
 * Lee el valor de un widget sin nunca depender de auto-wait/actionability:
 * cada rama usa `.count()` (sincronico, no reintenta) antes de leer, porque
 * asumir la forma del DOM (ej. un <select> nativo) y despues llamar
 * `.inputValue()` a ciegas cuelga ~30s por campo si la asuncion esta mal --
 * exactamente lo que paso en la primera corrida: los campos de tipo
 * "selection" en Ajustes de Odoo 19 se renderizan como un combobox
 * custom (input + overlay), no como <select>.
 *
 * Reads a widget's value without ever relying on auto-wait/actionability:
 * every branch uses `.count()` (synchronous, no retrying) before reading,
 * because assuming the DOM shape (e.g. a native <select>) and then blindly
 * calling `.inputValue()` hangs ~30s per field if the assumption is wrong --
 * exactly what happened on the first run: "selection"-type fields in Odoo
 * 19's Settings render as a custom combobox (input + overlay), not a
 * <select>.
 */
async function readWidgetValue(widget: Locator, kind: FieldKind): Promise<string> {
  if (kind === 'boolean') {
    const checkbox = widget.locator('input[type="checkbox"]');
    if (await checkbox.count()) {
      return (await checkbox.isChecked()) ? 'true' : 'false';
    }
    return '(sin checkbox / no checkbox found)';
  }

  if (kind === 'radio') {
    const checked = widget.locator('input[type="radio"]:checked');
    if (await checked.count()) {
      return (await checked.getAttribute('value')) || '(ninguno seleccionado / none selected)';
    }
    return '(sin radio / no radio found)';
  }

  // 'select' y 'text': probar <select> nativo primero, luego input/textarea,
  // y como ultimo recurso el texto visible del widget completo.
  // 'select' and 'text': try a native <select> first, then input/textarea,
  // and as a last resort the widget's whole visible text.
  const select = widget.locator('select');
  if (await select.count()) {
    return (await select.inputValue()) || '(vacio / empty)';
  }

  const input = widget.locator('input, textarea').first();
  if (await input.count()) {
    const val = await input.inputValue().catch(() => null);
    if (val !== null) return val.trim() || '(vacio / empty)';
  }

  const text = (await widget.textContent()) || '';
  return text.trim() || '(vacio / empty)';
}

test('auditoria de Ajustes > Asistencias (hr_attendance)', async ({ page }) => {
  await page.goto('/odoo/settings');
  await expect(page.locator('.o_main_navbar')).toBeVisible({ timeout: 20_000 });

  // El tab de la izquierda solo existe si el usuario tiene
  // hr_attendance.group_hr_attendance_manager (ver docstring arriba).
  // The left-side tab only exists if the user has
  // hr_attendance.group_hr_attendance_manager (see docstring above).
  const attendanceTab = page.locator('a.tab[data-key="hr_attendance"]');
  await expect(
    attendanceTab,
    'Tab "Attendances" no encontrado -- probablemente el usuario no tiene ' +
      'hr_attendance.group_hr_attendance_manager. / "Attendances" tab not found -- ' +
      'the user is probably missing hr_attendance.group_hr_attendance_manager.'
  ).toBeVisible({ timeout: 15_000 });
  await attendanceTab.click();

  const block = page.locator('.app_settings_block[data-key="hr_attendance"]');
  await expect(block).toBeVisible({ timeout: 10_000 });

  const results: FieldResult[] = [];

  for (const field of FIELDS) {
    const widget = block.locator(`.o_field_widget[name="${field.name}"]`).first();
    const visible = await widget.isVisible().catch(() => false);
    const value = visible ? await readWidgetValue(widget, field.kind) : '(no visible / not visible)';
    results.push({ ...field, value, visible });
  }

  const screenshotPath = path.join(__dirname, '..', 'screenshots', 'attendance_settings_baseline.png');
  await page.locator('.app_settings_block[data-key="hr_attendance"]').screenshot({ path: screenshotPath });

  const timestamp = new Date().toISOString();
  const rows = results
    .map((r) => `| \`${r.name}\` | ${r.label} | ${r.visible ? r.value : '_(campo condicional, no visible con la config. actual / conditional field, not visible with current config)_'} |`)
    .join('\n');

  const block_md = [
    START_MARKER,
    '',
    `**Generado / Generated:** ${timestamp}`,
    '',
    '**Instancia / Instance:** ' + (process.env.ODOO_URL ?? 'http://localhost:8069') + ` (DB: ${process.env.ODOO_DB ?? 'medicinedepot_dev'})`,
    '',
    '| Campo / Field | Descripcion / Description | Valor actual / Current value |',
    '|---|---|---|',
    rows,
    '',
    `Captura / Screenshot: \`${path.relative(path.join(__dirname, '..'), screenshotPath)}\``,
    '',
    END_MARKER,
  ].join('\n');

  let existing = '';
  try {
    existing = fs.readFileSync(BASELINE_DOC, 'utf-8');
  } catch {
    existing = '';
  }

  let updated: string;
  if (existing.includes(START_MARKER) && existing.includes(END_MARKER)) {
    const before = existing.split(START_MARKER)[0];
    const after = existing.split(END_MARKER)[1];
    updated = `${before}${block_md}${after}`;
  } else {
    // No deberia pasar si docs/ATTENDANCE_BASELINE.md ya trae los marcadores
    // (ver seccion de arquitectura escrita a mano). Si el archivo no existe
    // todavia, se crea solo con el bloque de baseline.
    // Shouldn't happen if docs/ATTENDANCE_BASELINE.md already has the
    // markers (see the hand-written architecture section). If the file
    // doesn't exist yet, it's created with just the baseline block.
    updated = `# Baseline de configuracion de Asistencias / Attendance configuration baseline\n\n${block_md}\n`;
  }

  fs.mkdirSync(path.dirname(BASELINE_DOC), { recursive: true });
  fs.writeFileSync(BASELINE_DOC, updated, 'utf-8');

  console.log(`Baseline exportado a ${BASELINE_DOC}`);
});
