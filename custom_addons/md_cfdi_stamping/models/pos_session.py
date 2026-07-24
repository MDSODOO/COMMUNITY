import base64
from collections import defaultdict
from decimal import Decimal

from odoo import fields, models, _
from odoo.exceptions import UserError

GENERIC_RECEPTOR_RFC = 'XAXX010101000'
GENERIC_RECEPTOR_NAME = 'PUBLICO EN GENERAL'


class PosSession(models.Model):
    _inherit = 'pos.session'

    l10n_mx_cfdi_state = fields.Selection(
        [
            ('not_generated', 'No generado'),
            ('signed', 'Sellado (sin timbrar)'),
            ('stamped', 'Timbrado'),
            ('error', 'Error'),
        ],
        string='Estado Factura Global',
        default='not_generated',
        copy=False,
    )
    l10n_mx_cfdi_xml = fields.Binary(string='XML Factura Global', attachment=True, copy=False)
    l10n_mx_cfdi_xml_filename = fields.Char(copy=False)
    l10n_mx_cfdi_error = fields.Text(string='Error Factura Global', copy=False, readonly=True)

    def _l10n_mx_global_invoice_orders(self):
        self.ensure_one()
        return self.order_ids.filtered(
            lambda o: o.state in ('paid', 'done', 'invoiced')
            and not o.account_move
            and (not o.partner_id or not o.partner_id.vat or o.partner_id.vat == GENERIC_RECEPTOR_RFC)
        )

    def _l10n_mx_build_global_conceptos(self, orders):
        from satcfdi.create.cfd import cfdi40
        from satcfdi.create.cfd.catalogos import Impuesto, TipoFactor

        grouped = defaultdict(lambda: {'cantidad': Decimal('0'), 'importe': Decimal('0'), 'tasa': Decimal('0'), 'product': None})
        for order in orders:
            for line in order.lines:
                product = line.product_id
                if not product.l10n_mx_clave_prod_serv or not product.l10n_mx_clave_unidad:
                    raise UserError(_(
                        'Falta Clave Prod/Serv o Clave Unidad (SAT) en el producto "%s".'
                    ) % product.display_name)
                tax = line.tax_ids_after_fiscal_position[:1] or line.tax_ids[:1]
                tasa = Decimal(str(tax.amount / 100)) if tax else Decimal('0')
                key = (product.id, tasa)
                bucket = grouped[key]
                bucket['product'] = product
                bucket['tasa'] = tasa
                bucket['cantidad'] += Decimal(str(line.qty))
                bucket['importe'] += Decimal(str(line.price_subtotal))

        conceptos = []
        for (product_id, tasa), bucket in grouped.items():
            product = bucket['product']
            cantidad = bucket['cantidad'] or Decimal('1')
            importe = bucket['importe'].quantize(Decimal('0.01'))
            valor_unitario = (importe / cantidad).quantize(Decimal('0.000001'))
            conceptos.append(
                cfdi40.Concepto(
                    clave_prod_serv=product.l10n_mx_clave_prod_serv,
                    cantidad=cantidad,
                    clave_unidad=product.l10n_mx_clave_unidad,
                    descripcion=product.display_name,
                    valor_unitario=valor_unitario,
                    impuestos=cfdi40.Impuestos(
                        traslados=[cfdi40.Traslado(
                            impuesto=Impuesto.IVA,
                            tipo_factor=TipoFactor.TASA,
                            tasa_o_cuota=bucket['tasa'],
                        )]
                    ) if bucket['tasa'] else None,
                )
            )
        return conceptos

    def action_generate_global_invoice_xml(self):
        from satcfdi.create.cfd import cfdi40

        for session in self:
            company = session.company_id
            if not company.vat or not company.l10n_mx_regimen_fiscal or not company.zip:
                raise UserError(_('Falta RFC, Régimen Fiscal o Código Postal en la compañía %s.') % company.name)

            orders = session._l10n_mx_global_invoice_orders()
            if not orders:
                raise UserError(_('No hay ventas de público en general pendientes de facturar en esta sesión.'))

            signer = company._l10n_mx_get_signer()

            session_date = fields.Datetime.to_datetime(session.start_at or session.create_date)
            try:
                comprobante = cfdi40.Comprobante(
                    emisor=cfdi40.Emisor(
                        rfc=company.vat,
                        nombre=company.name,
                        regimen_fiscal=company.l10n_mx_regimen_fiscal,
                    ),
                    lugar_expedicion=company.zip,
                    receptor=cfdi40.Receptor(
                        rfc=GENERIC_RECEPTOR_RFC,
                        nombre=GENERIC_RECEPTOR_NAME,
                        uso_cfdi='S01',
                        domicilio_fiscal_receptor=company.zip,
                        regimen_fiscal_receptor='616',
                    ),
                    metodo_pago='PUE',
                    forma_pago='01',
                    serie='FG',
                    folio=str(session.id),
                    informacion_global=cfdi40.InformacionGlobal(
                        periodicidad='01',
                        meses='%02d' % session_date.month,
                        ano=session_date.year,
                    ),
                    conceptos=session._l10n_mx_build_global_conceptos(orders),
                )
                comprobante.sign(signer)
                comprobante = comprobante.process()
                xml_bytes = comprobante.xml_bytes()
            except UserError:
                raise
            except Exception as exc:
                session.write({'l10n_mx_cfdi_state': 'error', 'l10n_mx_cfdi_error': str(exc)})
                raise UserError(_('Error generando la Factura Global: %s') % exc)

            session.write({
                'l10n_mx_cfdi_xml': base64.b64encode(xml_bytes),
                'l10n_mx_cfdi_xml_filename': f'FACTURA_GLOBAL_{session.name}.xml',
                'l10n_mx_cfdi_state': 'signed',
                'l10n_mx_cfdi_error': False,
            })
        return True
