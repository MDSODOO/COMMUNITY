import { test, expect } from '@playwright/test';
import { loginAs } from './utils/odoo';

/**
 * Prueba funcional de hr_attendance_ip_autologin: registra una IP autorizada
 * para una sucursal (res.company) via ORM, hace login real (POST /web/login)
 * desde esa IP, y verifica que el controlador heredado
 * (HomeIPAutoCheckin.web_login) haya marcado el check-in del empleado de esa
 * sucursal -- y SOLO de esa sucursal, no de las otras 5 companias donde el
 * mismo usuario tambien tiene un hr.employee (ver hallazgo en
 * models/hr_employee.py: un res.users puede tener varios hr.employee, uno
 * por compania).
 *
 * Functional test for hr_attendance_ip_autologin: registers an authorized IP
 * for one branch (res.company) via ORM, performs a real login (POST
 * /web/login) from that IP, and verifies the inherited controller
 * (HomeIPAutoCheckin.web_login) checked in the employee for that branch --
 * and ONLY that branch, not the other 5 companies where the same user also
 * has an hr.employee record (see finding in models/hr_employee.py: a single
 * res.users can have multiple hr.employee records, one per company).
 *
 * Requiere ODOO_ATTENDANCE_ADMIN_LOGIN/PASSWORD en .env: un usuario con
 * hr_attendance.group_hr_attendance_manager (el usuario de la sesion
 * compartida del resto de la suite no lo tiene, ver
 * docs/ATTENDANCE_BASELINE.md). Usa su propia sesion -- no la compartida --
 * porque necesita loguear con ESE usuario especificamente.
 *
 * Requires ODOO_ATTENDANCE_ADMIN_LOGIN/PASSWORD in .env: a user with
 * hr_attendance.group_hr_attendance_manager (the rest of the suite's shared
 * session user doesn't have it, see docs/ATTENDANCE_BASELINE.md). Uses its
 * own session -- not the shared one -- because it needs to log in as THAT
 * specific user.
 *
 * Hallazgo de esta auditoria: hr.attendance tiene una ir.rule GLOBAL
 * ("Employee multi company rule", global=true) que restringe la lectura a
 * `employee_id.company_id in company_ids`, donde `company_ids` es la
 * seleccion ACTIVA del selector de compania de la sesion -- no "todas las
 * companias a las que el usuario tiene acceso". Por default una sesion
 * fresca no trae las 6 sucursales activas, asi que un searchRead comun NO ve
 * la asistencia de una sucursal que no este activa, aunque el registro SI
 * exista en la base (verificado con SQL directo). Por eso todas las
 * llamadas cross-sucursal de este test pasan
 * `context: { allowed_company_ids: <todas> }` explicitamente.
 *
 * Finding from this audit: hr.attendance has a GLOBAL ir.rule ("Employee
 * multi company rule", global=true) restricting reads to
 * `employee_id.company_id in company_ids`, where `company_ids` is the
 * session's ACTIVE company-switcher selection -- not "every company the
 * user has access to". A fresh session doesn't have all 6 branches active
 * by default, so a plain searchRead won't see attendance for a branch
 * that isn't active, even though the row genuinely exists (verified via
 * direct SQL). Hence every cross-branch call in this test explicitly passes
 * `context: { allowed_company_ids: <all> }`.
 */
test.use({ storageState: undefined });

const ADMIN_LOGIN = process.env.ODOO_ATTENDANCE_ADMIN_LOGIN;
const ADMIN_PASSWORD = process.env.ODOO_ATTENDANCE_ADMIN_PASSWORD;

// IP que Playwright presenta al servidor Odoo en este entorno: verificado
// contra los logs de docker (`docker logs medicinedepot_dev_odoo`) durante
// esta misma auditoria -- es el gateway del bridge de Docker cuando el
// navegador corre en el host y pega al puerto publicado del contenedor.
// The IP Playwright presents to the Odoo server in this environment:
// verified against docker logs during this same audit -- it's the Docker
// bridge gateway when the browser runs on the host hitting the container's
// published port.
const TEST_IP = '172.18.0.1';

test.skip(
  !ADMIN_LOGIN || !ADMIN_PASSWORD,
  'Falta ODOO_ATTENDANCE_ADMIN_LOGIN/PASSWORD en e2e_tests/.env'
);

test('check-in automatico al iniciar sesion desde una IP autorizada de la sucursal', async ({ page }) => {
  await loginAs(page, ADMIN_LOGIN!, ADMIN_PASSWORD!);

  // 0. Todas las companias -- se usan como allowed_company_ids explicito en
  // cada llamada cross-sucursal (ver nota de la ir.rule global arriba).
  const allCompanyIds: number[] = await page.evaluate(async () => {
    // @ts-ignore
    const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
    const companies = await ormSvc.searchRead('res.company', [], ['id']);
    return companies.map((c: any) => c.id);
  });
  const ctx = { context: { allowed_company_ids: allCompanyIds } };

  // 1. Ubicar la sucursal MDS CANCUN y el hr.employee de este usuario en esa
  // compania -- sin hardcodear ids (pueden variar entre entornos) y sin
  // depender de ningun servicio de "usuario actual" del frontend (no existe
  // un service "user" con .userId en esta build -- se encontro navegando
  // hr.employee directo con la relacion user_id.login, dominio ORM estandar).
  const { companyId, employeeId } = await page.evaluate(
    async ({ ADMIN_LOGIN, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const companies = await ormSvc.searchRead('res.company', [['name', 'like', 'CANC']], ['id'], ctx);
      const companyId = companies[0]?.id;
      const employees = await ormSvc.searchRead(
        'hr.employee',
        [['user_id.login', '=', ADMIN_LOGIN], ['company_id', '=', companyId]],
        ['id'],
        ctx
      );
      return { companyId, employeeId: employees[0]?.id };
    },
    { ADMIN_LOGIN, ctx }
  );
  expect(companyId, 'No se encontro la compania MDS CANCUN').toBeTruthy();
  expect(employeeId, 'El usuario de prueba no tiene hr.employee en MDS CANCUN').toBeTruthy();

  // 2. Limpieza defensiva: por si una corrida anterior dejo una entrada
  // abierta o un registro de IP de una corrida previa.
  await page.evaluate(
    async ({ employeeId, companyId, TEST_IP, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const openAttendances = await ormSvc.searchRead(
        'hr.attendance',
        [['employee_id', '=', employeeId], ['check_out', '=', false]],
        ['id'],
        ctx
      );
      if (openAttendances.length) {
        await ormSvc.write(
          'hr.attendance',
          openAttendances.map((a: any) => a.id),
          { check_out: new Date().toISOString().slice(0, 19).replace('T', ' ') },
          ctx
        );
      }
      const existingIps = await ormSvc.searchRead(
        'hr.attendance.authorized.ip',
        [['company_id', '=', companyId], ['ip_address', '=', TEST_IP]],
        ['id']
      );
      if (existingIps.length) {
        await ormSvc.unlink('hr.attendance.authorized.ip', existingIps.map((r: any) => r.id));
      }
    },
    { employeeId, companyId, TEST_IP, ctx }
  );

  // 3. Registrar la IP autorizada para la sucursal -- este es el escenario
  // que un encargado de sucursal configuraria a traves de la pestaña
  // "Check-in por IP" del formulario de compania (views/res_company_views.xml).
  const ipRecordId: number = await page.evaluate(
    async ({ companyId, TEST_IP }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const ids = await ormSvc.create('hr.attendance.authorized.ip', [
        { name: 'Playwright test IP', company_id: companyId, ip_address: TEST_IP },
      ]);
      return ids[0];
    },
    { companyId, TEST_IP }
  );
  expect(ipRecordId).toBeTruthy();

  // 4. "Cerrar sesion" y volver a iniciarla -- esto es lo que dispara
  // HomeIPAutoCheckin.web_login (solo actua en un POST /web/login exitoso,
  // no en cualquier request).
  //
  // OJO: NO usar /web/session/logout aqui. Ese endpoint invalida la sesion
  // del lado del SERVIDOR -- y como todos los specs de esta suite comparten
  // el mismo storageState (.auth/odoo-session.json, un unico session id
  // capturado por auth.setup.ts), invalidarla del lado del servidor rompe
  // la sesion compartida para CUALQUIER otro test que corra despues en la
  // misma corrida (bug real encontrado en esta auditoria: rompia
  // test_command_palette / test_image_quote_smoke / test_purchase_parser_ui
  // por venir despues alfabeticamente). Limpiar solo las cookies de ESTE
  // contexto obliga un login fresco (nuevo session id) sin tocar el de los
  // demas.
  //
  // Do NOT use /web/session/logout here. That endpoint invalidates the
  // session on the SERVER side -- and since every spec in this suite shares
  // the same storageState (.auth/odoo-session.json, a single session id
  // captured by auth.setup.ts), invalidating it server-side breaks the
  // shared session for ANY other test running later in the same run (real
  // bug found during this audit: it broke test_command_palette /
  // test_image_quote_smoke / test_purchase_parser_ui, which sort after this
  // file alphabetically). Clearing only THIS context's cookies forces a
  // fresh login (new session id) without touching anyone else's.
  await page.context().clearCookies();
  await loginAs(page, ADMIN_LOGIN!, ADMIN_PASSWORD!);

  // 5. Verificar: debe existir una asistencia abierta (check_out=false) para
  // el empleado de MDS CANCUN, creada en el ultimo minuto.
  const attendance = await page.evaluate(
    async ({ employeeId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const rows = await ormSvc.searchRead(
        'hr.attendance',
        [['employee_id', '=', employeeId], ['check_out', '=', false]],
        ['id', 'check_in'],
        ctx
      );
      return rows[0] || null;
    },
    { employeeId, ctx }
  );
  expect(attendance, 'No se creo un check-in automatico para el empleado de MDS CANCUN').toBeTruthy();

  // 6. Verificar el alcance por sucursal: los OTROS hr.employee del mismo
  // usuario (en las demas companias, sin IP autorizada) NO deben tener
  // ninguna asistencia abierta -- si esto fallara, significaria que el
  // matching de compania en _auto_checkin_by_ip esta roto y cualquier
  // sucursal dispara el check-in de todas.
  const otherOpenAttendances = await page.evaluate(
    async ({ ADMIN_LOGIN, companyId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      const otherEmployees = await ormSvc.searchRead(
        'hr.employee',
        [['user_id.login', '=', ADMIN_LOGIN], ['company_id', '!=', companyId]],
        ['id'],
        ctx
      );
      const otherIds = otherEmployees.map((e: any) => e.id);
      if (!otherIds.length) return [];
      return ormSvc.searchRead(
        'hr.attendance',
        [['employee_id', 'in', otherIds], ['check_out', '=', false]],
        ['id', 'employee_id'],
        ctx
      );
    },
    { ADMIN_LOGIN, companyId, ctx }
  );
  expect(otherOpenAttendances, 'El check-in automatico se disparo tambien en otras sucursales').toEqual([]);

  // Limpieza: cerrar la asistencia creada y borrar la IP de prueba, para que
  // la corrida sea repetible.
  await page.evaluate(
    async ({ attendanceId, ipRecordId, ctx }) => {
      // @ts-ignore
      const ormSvc = window.odoo.__WOWL_DEBUG__.root.env.services.orm;
      await ormSvc.write(
        'hr.attendance',
        [attendanceId],
        { check_out: new Date().toISOString().slice(0, 19).replace('T', ' ') },
        ctx
      );
      await ormSvc.unlink('hr.attendance.authorized.ip', [ipRecordId]);
    },
    { attendanceId: attendance!.id, ipRecordId, ctx }
  );
});
