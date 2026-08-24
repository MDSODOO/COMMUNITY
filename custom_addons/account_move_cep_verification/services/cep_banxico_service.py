import base64
import csv
import io
import logging
import re
import zipfile
from datetime import date, datetime

from odoo import fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TRACE_CODE_RE = re.compile(r'^[A-Za-z0-9]{1,30}$')
REFERENCE_RE = re.compile(r'^\d{1,7}$')
BANK_CODE_RE = re.compile(r'^\d{3,5}$')

BANXICO_SCL_URL = 'https://www.banxico.org.mx/cep-scl/'


class CEPBanxicoService:
    """Gestiona la verificación manual de CEPs vía Banxico CEP-SCL (gratuito, sin API keys)."""

    def __init__(self, env):
        self.env = env

    # ------------------------------------------------------------------
    # Generación de archivo TXT para Banxico CEP-SCL
    # ------------------------------------------------------------------

    def generate_scl_import_file(self, moves):
        """
        Genera archivo .TXT con el formato requerido por Banxico CEP-SCL.

        Formato por fila:
            Fecha,ClaveRastreo,CodBancoEmisor,CodBancoReceptor,Monto

        Retorna: (contenido_str, nombre_archivo)
        """
        output = io.StringIO()
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(['Fecha', 'ClaveRastreo', 'CodBancoEmisor', 'CodBancoReceptor', 'Monto'])

        errors = []
        valid_rows = 0

        for move in moves:
            is_valid, err = self.validate_spei_data(
                move.transfer_trace_code,
                move.transfer_reference,
                move.emission_bank_code,
                move.receiving_bank_code,
                move.transfer_amount,
                move.transfer_operation_date,
            )
            if not is_valid:
                errors.append(f'• {move.name or move.id}: {err}')
                continue

            op_date = move.transfer_operation_date
            if isinstance(op_date, (date, datetime)):
                op_date = op_date.strftime('%Y-%m-%d')

            writer.writerow([
                op_date or '',
                move.transfer_trace_code or '',
                move.emission_bank_code or '',
                move.receiving_bank_code or '',
                f'{move.transfer_amount:.2f}' if move.transfer_amount else '',
            ])
            valid_rows += 1

        if errors:
            raise UserError(
                'Los siguientes movimientos tienen datos incompletos o inválidos:\n'
                + '\n'.join(errors)
            )

        if valid_rows == 0:
            raise UserError('No hay movimientos SPEI válidos para generar el archivo.')

        today = fields.Date.today().strftime('%Y%m%d')
        filename = f'cep_scl_{today}_{valid_rows}reg.txt'
        return output.getvalue(), filename

    # ------------------------------------------------------------------
    # Procesamiento de resultados ZIP de Banxico
    # ------------------------------------------------------------------

    def process_scl_results_zip(self, batch, zip_content_b64):
        """
        Procesa el ZIP descargado de Banxico CEP-SCL.

        - Los archivos en el ZIP se nombran con la clave de rastreo (ej. CEP_ABCD123.pdf).
        - Si la clave de rastreo aparece en algún archivo del ZIP → verified_manual.
        - Si no aparece → not_found_banxico.
        - Guarda PDFs/XMLs encontrados como ir.attachment en el account.move.

        Retorna dict con conteos: {found, not_found, total}
        """
        try:
            zip_bytes = base64.b64decode(zip_content_b64)
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except Exception as exc:
            raise UserError(f'Error al abrir el archivo ZIP: {exc}')

        all_zip_names = zf.namelist()
        all_zip_upper = [n.upper() for n in all_zip_names]
        found_count = 0
        not_found_count = 0

        for move in batch.move_ids:
            trace = (move.transfer_trace_code or '').upper().strip()
            if not trace:
                continue

            matching_indices = [i for i, name in enumerate(all_zip_upper) if trace in name]

            if matching_indices:
                for idx in matching_indices:
                    orig_name = all_zip_names[idx]
                    try:
                        file_bytes = zf.read(orig_name)
                        self.env['ir.attachment'].create({
                            'name': orig_name,
                            'datas': base64.b64encode(file_bytes).decode(),
                            'res_model': 'account.move',
                            'res_id': move.id,
                            'description': 'CEP Banxico CEP-SCL',
                        })
                    except Exception as exc:
                        _logger.warning('CEP-SCL: no se pudo adjuntar %s: %s', orig_name, exc)

                move.write({
                    'cep_verification_status': 'verified_manual',
                    'cep_verification_date': fields.Datetime.now(),
                    'cep_scl_batch_status': 'downloaded',
                    'cep_raw_response': f'Archivos CEP encontrados en ZIP: {[all_zip_names[i] for i in matching_indices]}',
                })
                found_count += 1

                self.env['cep.verification.log'].create({
                    'move_id': move.id,
                    'trace_code': move.transfer_trace_code,
                    'operation_date': move.transfer_operation_date,
                    'status': 'found',
                    'banxico_response': f'Encontrado en ZIP. Archivos: {[all_zip_names[i] for i in matching_indices]}',
                })
            else:
                move.write({
                    'cep_verification_status': 'not_found_banxico',
                    'cep_verification_date': fields.Datetime.now(),
                })
                not_found_count += 1

                self.env['cep.verification.log'].create({
                    'move_id': move.id,
                    'trace_code': move.transfer_trace_code,
                    'operation_date': move.transfer_operation_date,
                    'status': 'not_found',
                    'banxico_response': 'Clave de rastreo no encontrada en el ZIP de Banxico.',
                })

        batch.write({
            'status': 'imported',
            'transfers_found': found_count,
            'transfers_not_found': not_found_count,
        })

        return {
            'found': found_count,
            'not_found': not_found_count,
            'total': found_count + not_found_count,
        }

    # ------------------------------------------------------------------
    # Validación local (sin APIs externas)
    # ------------------------------------------------------------------

    def validate_spei_data(self, trace_code, reference, emission_bank,
                           receiving_bank, amount, operation_date):
        """
        Valida todos los campos SPEI requeridos por Banxico CEP-SCL.
        Retorna: (is_valid, error_message)
        """
        if not trace_code or not TRACE_CODE_RE.match(str(trace_code)):
            return False, 'Clave de rastreo inválida (1-30 caracteres alfanuméricos, sin espacios).'
        if reference and not REFERENCE_RE.match(str(reference)):
            return False, 'Número de referencia inválido (máx. 7 dígitos numéricos).'
        if not emission_bank or not BANK_CODE_RE.match(str(emission_bank)):
            return False, 'Código de banco emisor inválido (3-5 dígitos, ej. 40058).'
        if not receiving_bank or not BANK_CODE_RE.match(str(receiving_bank)):
            return False, 'Código de banco receptor inválido (3-5 dígitos).'
        if amount is not None and float(amount) <= 0:
            return False, 'El monto debe ser mayor a cero.'
        if operation_date and isinstance(operation_date, date) and operation_date > date.today():
            return False, 'La fecha de operación no puede ser futura.'
        return True, ''

    # ------------------------------------------------------------------
    # Instrucciones para el usuario
    # ------------------------------------------------------------------

    def get_manual_verification_instructions(self, filename):
        return (
            f'<h4>Pasos para verificar en Banxico CEP-SCL (GRATIS)</h4>'
            f'<ol>'
            f'<li><b>Descarga</b> el archivo <code>{filename}</code> usando el botón de arriba.</li>'
            f'<li>Abre <a href="{BANXICO_SCL_URL}" target="_blank"><b>Banxico CEP-SCL</b></a> en tu navegador.</li>'
            f'<li><b>Sube</b> el archivo .TXT en el portal de Banxico.</li>'
            f'<li>Anota el <b>token</b> que te asigna Banxico y guárdalo en el campo de abajo.</li>'
            f'<li>Espera el correo de Banxico con el enlace de descarga (puede tardar minutos u horas).</li>'
            f'<li>Descarga el <b>ZIP</b> con los CEPs encontrados.</li>'
            f'<li>Vuelve aquí, haz clic en <b>Avanzar al Paso 4</b> y sube el ZIP.</li>'
            f'</ol>'
            f'<p class="text-muted"><small>El servicio Banxico CEP-SCL es gratuito y oficial. '
            f'No requiere registro ni API key.</small></p>'
        )
