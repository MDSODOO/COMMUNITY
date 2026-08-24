import base64
import io
import zipfile
from datetime import date, timedelta

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCEPBanxicoService(TransactionCase):

    def _get_service(self):
        from odoo.addons.account_move_cep_verification.services.cep_banxico_service import CEPBanxicoService
        return CEPBanxicoService(self.env)

    def _make_move(self, trace_code='ABC12345', reference='1234567',
                   emission_bank='40058', receiving_bank='40102',
                   amount=1200.50, op_date=None):
        partner = self.env['res.partner'].search([], limit=1)
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'transfer_type': 'spei',
            'transfer_trace_code': trace_code,
            'transfer_reference': reference,
            'emission_bank_code': emission_bank,
            'receiving_bank_code': receiving_bank,
            'transfer_amount': amount,
            'transfer_operation_date': op_date or date.today() - timedelta(days=1),
        })

    def _make_zip(self, filenames):
        """Crea un ZIP en memoria con los nombres de archivo dados."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            for name in filenames:
                zf.writestr(name, b'CEP PDF content')
        return base64.b64encode(buf.getvalue()).decode()

    # ------------------------------------------------------------------
    # Validación local de datos SPEI
    # ------------------------------------------------------------------

    def test_validate_spei_data_valid(self):
        svc = self._get_service()
        ok, err = svc.validate_spei_data('ABC12345', '1234567', '40058', '40102', 100.0,
                                         date.today() - timedelta(days=1))
        self.assertTrue(ok)
        self.assertEqual(err, '')

    def test_validate_trace_code_regex_invalid(self):
        svc = self._get_service()
        ok, err = svc.validate_spei_data('CLAVE CON ESPACIOS', '1234567', '40058', '40102', 100.0, None)
        self.assertFalse(ok)
        self.assertIn('rastreo', err.lower())

    def test_validate_trace_code_too_long(self):
        svc = self._get_service()
        ok, err = svc.validate_spei_data('A' * 31, '1234567', '40058', '40102', 100.0, None)
        self.assertFalse(ok)

    def test_validate_trace_code_max_length_ok(self):
        svc = self._get_service()
        ok, _ = svc.validate_spei_data('A' * 30, '1234567', '40058', '40102', 100.0, None)
        self.assertTrue(ok)

    def test_validate_reference_7_digits(self):
        svc = self._get_service()
        ok, _ = svc.validate_spei_data('ABC123', '1234567', '40058', '40102', 100.0, None)
        self.assertTrue(ok)

    def test_validate_reference_non_numeric_fails(self):
        svc = self._get_service()
        ok, err = svc.validate_spei_data('ABC123', 'REF-ABC', '40058', '40102', 100.0, None)
        self.assertFalse(ok)
        self.assertIn('referencia', err.lower())

    def test_validate_bank_code_invalid(self):
        svc = self._get_service()
        ok, err = svc.validate_spei_data('ABC123', '1234567', 'XX', '40102', 100.0, None)
        self.assertFalse(ok)
        self.assertIn('emisor', err.lower())

    def test_validate_amount_zero_fails(self):
        svc = self._get_service()
        ok, err = svc.validate_spei_data('ABC123', '1234567', '40058', '40102', 0, None)
        self.assertFalse(ok)
        self.assertIn('monto', err.lower())

    def test_validate_future_date_fails(self):
        svc = self._get_service()
        ok, err = svc.validate_spei_data('ABC123', '1234567', '40058', '40102', 100.0,
                                         date.today() + timedelta(days=1))
        self.assertFalse(ok)
        self.assertIn('fecha', err.lower())

    # ------------------------------------------------------------------
    # Generación de archivo TXT
    # ------------------------------------------------------------------

    def test_generate_scl_import_file(self):
        svc = self._get_service()
        move = self._make_move('CLAVE123', '1234567', '40058', '40102', 1500.00)
        content, filename = svc.generate_scl_import_file(move)
        self.assertIn('CLAVE123', content)
        self.assertIn('40058', content)
        self.assertIn('40102', content)
        self.assertIn('1500.00', content)
        self.assertTrue(filename.endswith('.txt'))

    def test_generate_scl_import_file_has_header(self):
        svc = self._get_service()
        move = self._make_move()
        content, _ = svc.generate_scl_import_file(move)
        first_line = content.split('\n')[0]
        self.assertIn('ClaveRastreo', first_line)

    def test_generate_scl_import_file_no_valid_moves_raises(self):
        svc = self._get_service()
        partner = self.env['res.partner'].search([], limit=1)
        # Move sin datos SPEI completos
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'transfer_type': 'spei',
        })
        with self.assertRaises(UserError):
            svc.generate_scl_import_file(move)

    def test_wizard_generates_downloadable_txt(self):
        move = self._make_move()
        wizard = self.env['cep.scl.batch.wizard'].create({
            'move_ids': [(6, 0, move.ids)],
        })
        wizard.action_generate_txt()
        self.assertIsNotNone(wizard.txt_file)
        self.assertTrue(wizard.txt_filename.endswith('.txt'))
        self.assertEqual(wizard.step, 'generate')

    # ------------------------------------------------------------------
    # Procesamiento de resultados ZIP
    # ------------------------------------------------------------------

    def test_process_scl_results_marks_found(self):
        svc = self._get_service()
        move = self._make_move('CLAVE123ABC')
        batch = self.env['cep.scl.batch'].create({
            'batch_token': 'TOKEN-TEST-001',
            'move_ids': [(6, 0, move.ids)],
            'status': 'submitted',
        })
        # ZIP con archivo cuyo nombre contiene la clave de rastreo
        zip_b64 = self._make_zip(['CEP_CLAVE123ABC.pdf', 'CEP_CLAVE123ABC.xml'])
        result = svc.process_scl_results_zip(batch, zip_b64)

        self.assertEqual(result['found'], 1)
        self.assertEqual(result['not_found'], 0)
        move.invalidate_recordset()
        self.assertEqual(move.cep_verification_status, 'verified_manual')
        self.assertEqual(move.cep_scl_batch_status, 'downloaded')

    def test_process_scl_results_marks_not_found(self):
        svc = self._get_service()
        move = self._make_move('CLAVE_NO_EXISTE')
        batch = self.env['cep.scl.batch'].create({
            'batch_token': 'TOKEN-TEST-002',
            'move_ids': [(6, 0, move.ids)],
            'status': 'submitted',
        })
        # ZIP sin archivo para esta clave
        zip_b64 = self._make_zip(['CEP_OTRA_CLAVE.pdf'])
        result = svc.process_scl_results_zip(batch, zip_b64)

        self.assertEqual(result['found'], 0)
        self.assertEqual(result['not_found'], 1)
        move.invalidate_recordset()
        self.assertEqual(move.cep_verification_status, 'not_found_banxico')

    def test_process_scl_results_updates_batch_status(self):
        svc = self._get_service()
        move = self._make_move('CEP_FOUND_KEY')
        batch = self.env['cep.scl.batch'].create({
            'batch_token': 'TOKEN-TEST-003',
            'move_ids': [(6, 0, move.ids)],
            'status': 'submitted',
        })
        zip_b64 = self._make_zip(['CEP_FOUND_KEY.pdf'])
        svc.process_scl_results_zip(batch, zip_b64)
        self.assertEqual(batch.status, 'imported')
        self.assertEqual(batch.transfers_found, 1)

    def test_process_scl_results_creates_log_entries(self):
        svc = self._get_service()
        move = self._make_move('KEY_LOG_TEST')
        batch = self.env['cep.scl.batch'].create({
            'batch_token': 'TOKEN-TEST-004',
            'move_ids': [(6, 0, move.ids)],
            'status': 'submitted',
        })
        zip_b64 = self._make_zip(['CEP_KEY_LOG_TEST.pdf'])
        svc.process_scl_results_zip(batch, zip_b64)

        log = self.env['cep.verification.log'].search([('move_id', '=', move.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, 'found')

    def test_process_scl_results_invalid_zip_raises(self):
        svc = self._get_service()
        move = self._make_move()
        batch = self.env['cep.scl.batch'].create({
            'batch_token': 'TOKEN-TEST-005',
            'move_ids': [(6, 0, move.ids)],
        })
        with self.assertRaises(UserError):
            svc.process_scl_results_zip(batch, base64.b64encode(b'not a zip').decode())

    def test_process_scl_attaches_files_to_move(self):
        svc = self._get_service()
        move = self._make_move('ATTACH_TEST')
        batch = self.env['cep.scl.batch'].create({
            'batch_token': 'TOKEN-TEST-006',
            'move_ids': [(6, 0, move.ids)],
            'status': 'submitted',
        })
        zip_b64 = self._make_zip(['CEP_ATTACH_TEST.pdf'])
        svc.process_scl_results_zip(batch, zip_b64)

        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', move.id),
        ], limit=1)
        self.assertTrue(attachment)

    # ------------------------------------------------------------------
    # Lote CEP-SCL
    # ------------------------------------------------------------------

    def test_cep_scl_batch_creation(self):
        move = self._make_move()
        batch = self.env['cep.scl.batch'].create({
            'batch_token': 'TOKEN-BATCH-001',
            'move_ids': [(6, 0, move.ids)],
        })
        self.assertEqual(batch.total_transfers, 1)
        self.assertEqual(batch.status, 'draft')

    def test_cep_scl_batch_total_compute(self):
        move1 = self._make_move('TRACE001')
        move2 = self._make_move('TRACE002')
        batch = self.env['cep.scl.batch'].create({
            'move_ids': [(6, 0, [move1.id, move2.id])],
        })
        self.assertEqual(batch.total_transfers, 2)
