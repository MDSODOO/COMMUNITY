import { test, expect } from '@playwright/test';
import { loginAs } from './utils/odoo';

/**
 * Prueba funcional de la logica de checkout dinamico agregada a
 * hr_attendance_ip_autologin (controllers/main.py: SessionAutoCheckout;
 * models/hr_employee.py: _auto_checkout_by_session,
 * _cron_auto_checkout_abandoned_sessions) -- complementa
 * test_attendance_ip_autologin.spec.ts, que cubre el check-in por IP.
 *
 * Functional test for the dynamic checkout logic added to
 * hr_attendance_ip_autologin -- complements test_attendance_ip_autologin.spec.ts,
 * which covers IP-based check-in.
 *
 * Deliberadamente NO reusa el check-in por IP para generar el estado
 * "empleado adentro": las asistencias de prueba se crean directo via ORM,
 * para que esta suite valide el checkout de forma aislada, sin depender de
 * que el check-in tambien funcione. Por la misma razon usa sucursales
 * (MDS TICUL, MDS CHETUMAL) distintas a la que ya usa
 * test_attendance_ip_autologin.spec.ts (MDS CANCUN), para no competir por
 * el mismo hr.employee si algun dia esta suite corre en paralelo.
 *
 * Deliberately does NOT reuse IP-based check-in to set up the "employee is
 * in" state: test attendances are created directly via ORM, so this suite
 * validates checkout in isolation, without depending on check-in also
 * working. For the same reason it uses different branches (MDS TICUL, MDS
 * CHETUMAL) than test_attendance_ip_autologin.spec.ts (MDS CANCUN), so
 * there's no risk of both files fighting over the same hr.employee if this
 * suite is ever parallelized.
 *
 * Hallazgos de la auditoria que motivo este modulo (ver
 * docs/ATTENDANCE_BASELINE.md y el codigo referenciado arriba):
 * - El boton "Cerrar sesion" del menu de usuario pega a
 *   /web/session/logout (type='http'), NO a /web/session/destroy
 *   (type='jsonrpc', usado por otros flujos como auth_timeout).
 * - Session.logout() llama a request.session.clear() ANTES del hook
 *   oficial ir.http._post_logout(), asi que ese hook ya ve al usuario
 *   publico -- por eso el checkout se captura en el propio controlador de
 *   logout (uid leido antes de super().logout()), no en _post_logout.
 * - No existe un modelo ir.sessions en esta instancia de Odoo 19 CE. La
 *   señal de "ultima actividad" que se usa es mail.presence.last_poll
 *   (modulo mail, ya instalado), actualizada por el heartbeat del bus
 *   longpolling del cliente web.
 * - hr.employee.attendance_state es un campo compute SIN store=True --
 *   no se puede usar en un dominio de busqueda (ValueError de Odoo).
 * - hr.attendance valida que un nuevo check_in no puede caer dentro (ni
 *   preceder) del rango de un registro YA CERRADO del mismo empleado --
 *   por eso esta suite limpia TODO el historial de los empleados de
 *   prueba antes de cada escenario, no solo los registros abiertos.
 *
 * Findings from the audit that motivated this module (see
 * docs/ATTENDANCE_BASELINE.md and the code referenced above):
 * - The "Log out" user-menu button hits /web/session/logout
 *   (type='http'), NOT /web/session/destroy (type='jsonrpc', used by
 *   other flows like auth_timeout).
 * - Session.logout() calls request.session.clear() BEFORE the official
 *   ir.http._post_logout() hook, so that hook already sees the public
 *   user -- that's why checkout is captured in the logout controller
 *   itself (uid read before super().logout()), not in _post_logout.
 * - No ir.sessions model exists in this Odoo 19 CE instance. The "last
 *   activity" signal used instead is mail.presence.last_poll (mail
 *   module, already installed), updated by the web client's bus
 *   longpolling heartbeat.
 * - hr.employee.attendance_state is a compute field WITHOUT store=True --
 *   can't be used in a search domain (Odoo raises ValueError).
 * - hr.attendance validates that a new check_in can't fall within (or
 *   precede) an ALREADY CLOSED record's range for the same employee --
 *   that's why this suite wipes the ENTIRE attendance history of its test
 *   employees before each scenario, not just the open records.
 */
test.use({ storageState: undefined });

const ADMIN_LOGIN = process.env.ODOO_ATTENDANCE_ADMIN_LOGIN;
const ADMIN_PASSWORD = process.env.ODOO_ATTENDANCE_ADMIN_PASSWORD;

test.skip(
  !ADMIN_LOGIN || !ADMIN_PASSWORD,
  'Falta ODOO_ATTENDANCE_ADMIN_LOGIN/PASSWORD en e2e_tests/.env'
);

async function getAllCompanyIdsCtx(page: import('@playwright/test').Page) {
  const ids: number[] = await page.evaluate(async () => {
    // @ts-ignore
    const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
    const companies = await ormSvc.searchRead('res.company', [], ['id']);
    return companies.map((c: any) => c.id);
  });
  return { context: { allowed_company_ids: ids } };
}

async function getEmployeeForCompany(
  page: import('@playwright/test').Page,
  companyNameLike: string,
  ctx: object
) {
  return page.evaluate(
    async ({ ADMIN_LOGIN, companyNameLike, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const employees = await ormSvc.searchRead(
        'hr.employee',
        [['user_id.login', '=', ADMIN_LOGIN], ['company_id.name', 'like', companyNameLike]],
        ['id', 'user_id'],
        ctx
      );
      return { employeeId: employees[0]?.id as number | undefined, userId: employees[0]?.user_id?.[0] as number | undefined };
    },
    { ADMIN_LOGIN, companyNameLike, ctx }
  );
}

// Limpia TODO el historial de asistencia del empleado (no solo lo abierto)
// -- ver hallazgo en el docblock de arriba sobre la validacion de rangos
// de hr.attendance.
async function wipeAttendanceHistory(page: import('@playwright/test').Page, employeeId: number, ctx: object) {
  await page.evaluate(
    async ({ employeeId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const rows = await ormSvc.searchRead('hr.attendance', [['employee_id', '=', employeeId]], ['id'], ctx);
      if (rows.length) await ormSvc.unlink('hr.attendance', rows.map((r: any) => r.id), ctx);
    },
    { employeeId, ctx }
  );
}

function toOdooDatetime(d: Date): string {
  return d.toISOString().slice(0, 19).replace('T', ' ');
}

test('logout explicito cierra el check-in automaticamente', async ({ page }) => {
  await loginAs(page, ADMIN_LOGIN!, ADMIN_PASSWORD!);
  const ctx = await getAllCompanyIdsCtx(page);

  const { employeeId } = await getEmployeeForCompany(page, 'TICUL', ctx);
  expect(employeeId, 'No se encontro el empleado de administrador en MDS TICUL').toBeTruthy();

  await wipeAttendanceHistory(page, employeeId!, ctx);

  // Crear el "empleado esta adentro" directo por ORM -- no depende del
  // check-in por IP, solo del estado que el checkout debe encontrar.
  const attendanceId: number = await page.evaluate(
    async ({ employeeId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const ids = await ormSvc.create('hr.attendance', [{ employee_id: employeeId }], ctx);
      return ids[0];
    },
    { employeeId, ctx }
  );

  // Logout explicito -- la ruta REAL que dispara el boton "Cerrar sesion"
  // (ver hallazgo del docblock: /web/session/logout, no /web/session/destroy).
  await page.goto('/web/session/logout');
  await page.waitForLoadState('domcontentloaded');

  // Limpiar cookies antes de re-loguear: el logout roto/roto la sesion
  // (session.should_rotate), y reusar la cookie jar vieja arrastra un
  // CSRF token atado a una sesion ya muerta.
  await page.context().clearCookies();
  await loginAs(page, ADMIN_LOGIN!, ADMIN_PASSWORD!);

  const attendance = await page.evaluate(
    async ({ attendanceId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const rows = await ormSvc.searchRead('hr.attendance', [['id', '=', attendanceId]], ['id', 'check_in', 'check_out'], ctx);
      return rows[0];
    },
    { attendanceId, ctx }
  );
  expect(attendance.check_out, 'El logout explicito no cerro el check-in').toBeTruthy();

  await wipeAttendanceHistory(page, employeeId!, ctx);
});

test('cron cierra check-in abandonados usando mail.presence.last_poll, sin falsos positivos en sesiones activas', async ({ page }) => {
  await loginAs(page, ADMIN_LOGIN!, ADMIN_PASSWORD!);
  const ctx = await getAllCompanyIdsCtx(page);

  const { employeeId, userId } = await getEmployeeForCompany(page, 'CHETUMAL', ctx);
  expect(employeeId, 'No se encontro el empleado de administrador en MDS CHETUMAL').toBeTruthy();

  await wipeAttendanceHistory(page, employeeId!, ctx);

  const cronId: number = await page.evaluate(async () => {
    // @ts-ignore
    const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
    const crons = await ormSvc.searchRead('ir.cron', [['cron_name', 'like', 'abandonad']], ['id']);
    return crons[0]?.id;
  });
  expect(cronId, 'No se encontro el cron de checkout por abandono').toBeTruthy();

  // check_in 9h atras, last_poll 8.5h atras -- ambos vencen el umbral de
  // 8h default, pero last_poll es POSTERIOR a check_in (escenario
  // realista: el empleado entro, trabajo un rato con la pestaña abierta,
  // y el heartbeat se detuvo despues -- nunca son el mismo instante, ver
  // la guarda en _cron_auto_checkout_abandoned_sessions).
  const nineHoursAgo = toOdooDatetime(new Date(Date.now() - 9 * 3600 * 1000));
  const eightAndHalfHoursAgo = toOdooDatetime(new Date(Date.now() - 8.5 * 3600 * 1000));

  const staleAttendanceId: number = await page.evaluate(
    async ({ employeeId, nineHoursAgo, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const ids = await ormSvc.create('hr.attendance', [{ employee_id: employeeId, check_in: nineHoursAgo }], ctx);
      return ids[0];
    },
    { employeeId, nineHoursAgo, ctx }
  );

  await page.evaluate(
    async ({ userId, eightAndHalfHoursAgo }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const presences = await ormSvc.searchRead('mail.presence', [['user_id', '=', userId]], ['id']);
      if (presences.length) {
        await ormSvc.write('mail.presence', presences.map((p: any) => p.id), { last_poll: eightAndHalfHoursAgo, last_presence: eightAndHalfHoursAgo });
      } else {
        await ormSvc.create('mail.presence', [{ user_id: userId, last_poll: eightAndHalfHoursAgo, last_presence: eightAndHalfHoursAgo }]);
      }
    },
    { userId, eightAndHalfHoursAgo }
  );

  // Disparar el cron manualmente -- boton "Run Manually" del form de
  // ir.cron (method_direct_trigger), sin esperar 30 minutos reales.
  await page.evaluate(async (cronId) => {
    // @ts-ignore
    const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
    await ormSvc.call('ir.cron', 'method_direct_trigger', [[cronId]]);
  }, cronId);

  const staleAfterCron = await page.evaluate(
    async ({ staleAttendanceId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const rows = await ormSvc.searchRead('hr.attendance', [['id', '=', staleAttendanceId]], ['id', 'check_in', 'check_out'], ctx);
      return rows[0];
    },
    { staleAttendanceId, ctx }
  );
  expect(staleAfterCron.check_out, 'El cron no cerro la sesion abandonada (last_poll 8.5h atras)').toBeTruthy();
  expect(staleAfterCron.check_out, 'El cron debio usar last_poll como check_out, no "ahora"').toBe(eightAndHalfHoursAgo);

  // Control: una asistencia con presencia RECIENTE no debe cerrarse.
  // check_in reciente para no solaparse con el registro ya cerrado arriba.
  const fiveMinutesAgo = toOdooDatetime(new Date(Date.now() - 5 * 60 * 1000));
  const nowStr = toOdooDatetime(new Date());

  const freshAttendanceId: number = await page.evaluate(
    async ({ employeeId, fiveMinutesAgo, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const ids = await ormSvc.create('hr.attendance', [{ employee_id: employeeId, check_in: fiveMinutesAgo }], ctx);
      return ids[0];
    },
    { employeeId, fiveMinutesAgo, ctx }
  );
  await page.evaluate(
    async ({ userId, nowStr }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const presences = await ormSvc.searchRead('mail.presence', [['user_id', '=', userId]], ['id']);
      await ormSvc.write('mail.presence', presences.map((p: any) => p.id), { last_poll: nowStr, last_presence: nowStr });
    },
    { userId, nowStr }
  );

  await page.evaluate(async (cronId) => {
    // @ts-ignore
    const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
    await ormSvc.call('ir.cron', 'method_direct_trigger', [[cronId]]);
  }, cronId);

  const freshAfterCron = await page.evaluate(
    async ({ freshAttendanceId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const rows = await ormSvc.searchRead('hr.attendance', [['id', '=', freshAttendanceId]], ['id', 'check_out'], ctx);
      return rows[0];
    },
    { freshAttendanceId, ctx }
  );
  expect(freshAfterCron.check_out, 'El cron cerro por error una sesion con presencia reciente (falso positivo)').toBeFalsy();

  await wipeAttendanceHistory(page, employeeId!, ctx);
});
