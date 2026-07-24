import base64
from decimal import Decimal

from odoo import fields, models, _
from odoo.exceptions import UserError
from .cfdi_catalogos import FORMA_PAGO_SELECTION, METODO_PAGO_SELECTION


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_forma_pago = fields.Selection(FORMA_PAGO_SELECTION, string='Forma de Pago (SAT)')
    l10n_mx_metodo_pago = fields.Selection(
        METODO_PAGO_SELECTION, string='Método de Pago (SAT)', default='PUE',
    )
    l10n_mx_cfdi_state = fields.Selection(
        [
            ('not_generated', 'No generado'),
            ('signed', 'Sellado (sin timbrar)'),
            ('stamped', 'Timbrado'),
            ('error', 'Error'),
        ],
        string='Estado CFDI',
        default='not_generated',
        copy=False,
    )
    l10n_mx_cfdi_xml = fields.Binary(string='XML CFDI', attachment=True, copy=False)
    l10n_mx_cfdi_xml_filename = fields.Char(copy=False)
    l10n_mx_cfdi_error = fields.Text(string='Error CFDI', copy=False, readonly=True)

    def _l10n_mx_check_required_fields(self):
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id
        missing = []
        if not company.vat:
            missing.append(_('RFC de la compañía'))
        if not company.l10n_mx_regimen_fiscal:
            missing.append(_('Régimen Fiscal de la compañía'))
        if not company.zip:
            missing.append(_('Código Postal de la compañía (Lugar de Expedición)'))
        if not partner.vat:
            missing.append(_('RFC del cliente'))
        if not partner.l10n_mx_regimen_fiscal:
            missing.append(_('Régimen Fiscal del cliente'))
        if not partner.l10n_mx_uso_cfdi:
            missing.append(_('Uso de CFDI del cliente'))
        if not partner.zip:
            missing.append(_('Código Postal del cliente'))
        if not self.l10n_mx_forma_pago:
            missing.append(_('Forma de Pago (SAT)'))
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            if not line.product_id.l10n_mx_clave_prod_serv:
                missing.append(_('Clave Prod/Serv (SAT) en el producto "%s"') % line.product_id.display_name)
            if not line.product_id.l10n_mx_clave_unidad:
                missing.append(_('Clave Unidad (SAT) en el producto "%s"') % line.product_id.display_name)
        if missing:
            raise UserError(_(
                'No se puede generar el CFDI, falta configurar:\n- %s'
            ) % '\n- '.join(missing))

    def _l10n_mx_build_conceptos(self):
        from satcfdi.create.cfd import cfdi40
        from satcfdi.create.cfd.catalogos import Impuesto, TipoFactor

        conceptos = []
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            # Simplificación v1: asume un único impuesto (IVA) por línea vía
            # tax_ids[0]. IEPS, retenciones o líneas exentas requieren extender
            # esto antes de usarse con datos reales de facturación.
            tax = line.tax_ids[:1]
            tasa = Decimal(str(tax.amount / 100)) if tax else Decimal('0')
            valor_unitario = Decimal(str(line.price_unit))
            cantidad = Decimal(str(line.quantity))
            importe = (valor_unitario * cantidad).quantize(Decimal('0.01'))
            conceptos.append(
                cfdi40.Concepto(
                    clave_prod_serv=line.product_id.l10n_mx_clave_prod_serv,
                    cantidad=cantidad,
                    clave_unidad=line.product_id.l10n_mx_clave_unidad,
                    descripcion=line.name or line.product_id.display_name,
                    valor_unitario=valor_unitario,
                    impuestos=cfdi40.Impuestos(
                        traslados=[cfdi40.Traslado(
                            impuesto=Impuesto.IVA,
                            tipo_factor=TipoFactor.TASA,
                            tasa_o_cuota=tasa,
                        )]
                    ) if tasa else None,
                )
            )
        return conceptos

    def action_generate_cfdi_xml(self):
        from satcfdi.create.cfd import cfdi40

        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                raise UserError(_('El CFDI solo aplica a facturas y notas de crédito de venta.'))
            if move.state != 'posted':
                raise UserError(_('La factura debe estar publicada (posted) antes de generar el CFDI.'))
            try:
                move._l10n_mx_check_required_fields()
                signer = move.company_id._l10n_mx_get_signer()
                comprobante = cfdi40.Comprobante(
                    emisor=cfdi40.Emisor(
                        rfc=move.company_id.vat,
                        nombre=move.company_id.name,
                        regimen_fiscal=move.company_id.l10n_mx_regimen_fiscal,
                    ),
                    lugar_expedicion=move.company_id.zip,
                    receptor=cfdi40.Receptor(
                        rfc=move.partner_id.vat,
                        nombre=move.partner_id.name,
                        uso_cfdi=move.partner_id.l10n_mx_uso_cfdi,
                        domicilio_fiscal_receptor=move.partner_id.zip,
                        regimen_fiscal_receptor=move.partner_id.l10n_mx_regimen_fiscal,
                    ),
                    metodo_pago=move.l10n_mx_metodo_pago,
                    forma_pago=move.l10n_mx_forma_pago,
                    serie=(move.name or '').split('/')[0] or 'FAC',
                    folio=str(move.id),
                    conceptos=move._l10n_mx_build_conceptos(),
                )
                comprobante.sign(signer)
                comprobante = comprobante.process()
                xml_bytes = comprobante.xml_bytes()
            except UserError:
                raise
            except Exception as exc:
                move.write({
                    'l10n_mx_cfdi_state': 'error',
                    'l10n_mx_cfdi_error': str(exc),
                })
                raise UserError(_('Error generando el CFDI: %s') % exc)

            move.write({
                'l10n_mx_cfdi_xml': base64.b64encode(xml_bytes),
                'l10n_mx_cfdi_xml_filename': f'CFDI_{move.name or move.id}.xml',
                'l10n_mx_cfdi_state': 'signed',
                'l10n_mx_cfdi_error': False,
            })
        return True
