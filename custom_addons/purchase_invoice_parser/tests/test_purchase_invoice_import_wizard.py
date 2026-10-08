import base64
import unittest
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from io import BytesIO
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.purchase_invoice_parser.services.cfdi_parser import (
    CFDIDocument,
    CFDILine,
    CFDIParser,
)
from odoo.addons.purchase_invoice_parser.services.known_rfcs import KnownRFC
from odoo.addons.purchase_invoice_parser.services.addenda_parsers import (
    AddendaLot,
    BrudifarmaAddendaParser,
)
from odoo.addons.purchase_invoice_parser.services.lot_stock_resolver import (
    LotStockResolver,
)
from odoo.addons.purchase_invoice_parser.services.product_matcher import ProductMatcher
from odoo.addons.purchase_invoice_parser.services.pdf_lot_provider import (
    BrudifarmaProvider,
    GenericProvider,
    QuifamesaProvider,
    available_providers,
    get_provider,
)
from odoo.addons.purchase_invoice_parser.services.pdf_lot_parser import (
    parse_lots_by_article,
)
from odoo.addons.purchase_invoice_parser.services.zip_extractor import ZipExtractor


def _sample_cfdi(
    folio="1001",
    serie="A",
    rfc="AAA010101AAA",
    barcode="7501234567890",
    qty="15",
):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Serie="{serie}" Folio="{folio}" Fecha="2026-05-01T10:30:00"
    SubTotal="150.00" Total="150.00" Moneda="MXN">
  <cfdi:Emisor Rfc="{rfc}" Nombre="Proveedor Parser Test" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="RORS620929K71" Nombre="Medicine Depot"/>
  <cfdi:Conceptos>
    <cfdi:Concepto NoIdentificacion="{barcode}" Descripcion="Producto Parser Test"
        Cantidad="{qty}" ValorUnitario="10.00" Importe="150.00"
        ClaveUnidad="H87" Unidad="Pieza" ClaveProdServ="51100000">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Impuesto="002" TasaOCuota="0.000000" Importe="0.00"/>
        </cfdi:Traslados>
      </cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="00000000-0000-0000-0000-{folio.zfill(12)[-12:]}"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
""".encode()


def _zip_bytes(entries):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for filename, data in entries.items():
            archive.writestr(filename, data)
    return buffer.getvalue()


class TestLotParserProvider(unittest.TestCase):
    def test_get_provider_defaults_to_generic(self):
        self.assertIsInstance(get_provider(None), GenericProvider)
        self.assertIsInstance(get_provider("missing"), GenericProvider)
        self.assertIsInstance(get_provider("quifamesa"), QuifamesaProvider)
        self.assertIsInstance(get_provider("brudifarma"), BrudifarmaProvider)
        self.assertIn(("generic", "Generico (3 formatos)"), available_providers())
        self.assertIn(("brudifarma", "Brudifarma (referencia interna)"), available_providers())

    def test_generic_provider_parses_current_formats(self):
        text = "\n".join([
            "7501234567890 PZA 15 Producto Parser Test",
            "Descuento 5",
            "Lotes: LOT-A/01-may-2027/10 LOT-B/01-jun-2027/5",
        ])

        lots = get_provider("generic")._parse_text(text)

        self.assertEqual(set(lots), {"7501234567890"})
        self.assertEqual(
            [lot["name"] for lot in lots["7501234567890"]],
            ["LOT-A", "LOT-B"],
        )
        self.assertEqual(
            lots["7501234567890"][0]["expiration_date"],
            date(2027, 5, 1),
        )
        self.assertEqual(lots["7501234567890"][0]["discount"], 5.0)

    def test_pdf_lot_parser_shim_uses_generic_provider(self):
        original_parse = GenericProvider.parse

        def fake_parse(self, pdf_bytes):
            return {
                "750": [{
                    "name": "LOT-SHIM",
                    "expiration_date": False,
                    "quantity": 1,
                }]
            }

        try:
            GenericProvider.parse = fake_parse
            self.assertEqual(
                parse_lots_by_article(b"dummy")["750"][0]["name"],
                "LOT-SHIM",
            )
        finally:
            GenericProvider.parse = original_parse

    def test_cfdi_parser_brudifarma_reads_iva_rate_from_concept_traslado(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" Total="116.00" SubTotal="100.00">
  <cfdi:Emisor Rfc="BRU971010227" Nombre="BRUDIFARMA"/>
  <cfdi:Receptor Rfc="RORS620929K71" Nombre="Medicine Depot"/>
  <cfdi:Conceptos>
    <cfdi:Concepto NoIdentificacion="REF-1" Descripcion="Producto A" Cantidad="1" ValorUnitario="100.00" Importe="100.00" ClaveUnidad="H87" Unidad="PZA" ClaveProdServ="51100000">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="16.00"/>
        </cfdi:Traslados>
      </cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
</cfdi:Comprobante>"""
        doc = CFDIParser().parse_bytes(xml)
        self.assertEqual(len(doc.lines), 1)
        self.assertTrue(doc.lines[0].iva_presente)
        self.assertEqual(doc.lines[0].factor_iva, "Tasa")
        self.assertEqual(doc.lines[0].tasa_iva, 0.16)
        self.assertEqual(doc.lines[0].importe_iva, 16.0)

    def test_cfdi_parser_brudifarma_uses_global_iva_fallback(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" Total="108.00" SubTotal="100.00">
  <cfdi:Emisor Rfc="BRU971010227" Nombre="BRUDIFARMA"/>
  <cfdi:Receptor Rfc="RORS620929K71" Nombre="Medicine Depot"/>
  <cfdi:Conceptos>
    <cfdi:Concepto NoIdentificacion="REF-1" Descripcion="Producto A" Cantidad="1" ValorUnitario="100.00" Importe="100.00" ClaveUnidad="H87" Unidad="PZA" ClaveProdServ="51100000"/>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="8.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.080000" Importe="8.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
</cfdi:Comprobante>"""
        doc = CFDIParser().parse_bytes(xml)
        self.assertEqual(len(doc.lines), 1)
        self.assertTrue(doc.lines[0].iva_presente)
        self.assertEqual(doc.lines[0].factor_iva, "Tasa")
        self.assertEqual(doc.lines[0].tasa_iva, 0.08)
        self.assertEqual(doc.lines[0].importe_iva, 8.0)

    def test_cfdi_parser_non_brudifarma_does_not_use_global_iva_fallback(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" Total="108.00" SubTotal="100.00">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="Proveedor Gen"/>
  <cfdi:Receptor Rfc="RORS620929K71" Nombre="Medicine Depot"/>
  <cfdi:Conceptos>
    <cfdi:Concepto NoIdentificacion="REF-1" Descripcion="Producto A" Cantidad="1" ValorUnitario="100.00" Importe="100.00" ClaveUnidad="H87" Unidad="PZA" ClaveProdServ="51100000"/>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="8.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.080000" Importe="8.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
</cfdi:Comprobante>"""
        doc = CFDIParser().parse_bytes(xml)
        self.assertEqual(len(doc.lines), 1)
        self.assertFalse(doc.lines[0].iva_presente)
        self.assertEqual(doc.lines[0].tasa_iva, 0.0)

    def test_cfdi_parser_brudifarma_enriches_line_from_addenda_material(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" Total="116.00" SubTotal="100.00">
  <cfdi:Emisor Rfc="BRU971010227" Nombre="BRUDIFARMA"/>
  <cfdi:Receptor Rfc="RORS620929K71" Nombre="Medicine Depot"/>
  <cfdi:Conceptos>
    <cfdi:Concepto NoIdentificacion="508036" Descripcion="Producto A" Cantidad="5" ValorUnitario="10.00" Importe="50.00" ClaveUnidad="H87" Unidad="PZA" ClaveProdServ="51151508"/>
  </cfdi:Conceptos>
  <cfdi:Addenda>
    <cfdi:MATERIAL CodigoSAP="508036" Lote="GP03EVG" Caducidad="30.11.2028" CBarra="7501008427347" Cantidad="5" Precio="10.00"/>
  </cfdi:Addenda>
</cfdi:Comprobante>"""
        doc = CFDIParser().parse_bytes(xml)

        self.assertEqual(doc.emisor_rfc, KnownRFC.BRUDIFARMA)
        self.assertEqual(len(doc.lines), 1)
        self.assertEqual(doc.lines[0].descripcion_lot, "GP03EVG")
        self.assertEqual(doc.lines[0].descripcion_caducidad, date(2028, 11, 30))
        self.assertEqual(doc.lines[0].barcode_hint, "7501008427347")
        self.assertEqual(doc.lines[0].cantidad, 5.0)
        self.assertEqual(len(doc.addenda_lots), 1)

    def test_cfdi_parser_quifamesa_uses_noidentificacion_as_barcode_hint(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" Total="58.00" SubTotal="50.00">
  <cfdi:Emisor Rfc="QFM861010BL0" Nombre="QUIFAMESA"/>
  <cfdi:Receptor Rfc="RORS620929K71" Nombre="Medicine Depot"/>
  <cfdi:Conceptos>
    <cfdi:Concepto NoIdentificacion="7501234567890" Descripcion="Producto QFM" Cantidad="2" ValorUnitario="25.00" Importe="50.00" ClaveUnidad="H87" Unidad="PZA" ClaveProdServ="51100000"/>
  </cfdi:Conceptos>
</cfdi:Comprobante>"""
        doc = CFDIParser().parse_bytes(xml)

        self.assertEqual(doc.emisor_rfc, KnownRFC.QUIFAMESA)
        self.assertEqual(len(doc.lines), 1)
        self.assertEqual(doc.lines[0].no_identificacion, "7501234567890")
        self.assertEqual(doc.lines[0].barcode_hint, "7501234567890")
        self.assertEqual(doc.lines[0].cantidad, 2.0)

    def test_brudifarma_provider_parses_internal_reference_layout(self):
        text = "\n".join([
            "5.000      H87 - PZA       51151508 508036",
            "GP03EVG Fecha de caducidad: 30.11.2028",
            "2.000      H87 - PZA       51121743 507913",
            "5KM186A Fecha de caducidad: 31.10.2027",
            "5.000      H87 - PZA       51142002 511089                         TAB Lote: X26LVU Fecha de caducidad:",
            "31.10.2028",
        ])
        lots = get_provider("brudifarma")._parse_text(text)

        self.assertIn("508036", lots)
        self.assertIn("507913", lots)
        self.assertIn("511089", lots)
        self.assertEqual(lots["508036"][0]["name"], "GP03EVG")
        self.assertEqual(lots["508036"][0]["expiration_date"], date(2028, 11, 30))
        self.assertEqual(lots["508036"][0]["quantity"], 5.0)
        self.assertEqual(lots["511089"][0]["name"], "X26LVU")
        self.assertEqual(lots["511089"][0]["expiration_date"], date(2028, 10, 31))


class TestAddendaParser(unittest.TestCase):
    def test_brudifarma_parser_accepts_namespaced_material_nodes(self):
        root = ET.fromstring(
            b"""<cfdi:Comprobante xmlns:cfdi='http://www.sat.gob.mx/cfd/4'>
                    <cfdi:Addenda>
                        <cfdi:MATERIAL CodigoSAP='7501234567890' Lote='LOT-NS' Caducidad='01.12.2027' Cantidad='10' Precio='2.5'/>
                    </cfdi:Addenda>
                </cfdi:Comprobante>"""
        )
        lots = BrudifarmaAddendaParser().parse(root)
        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0].lote, "LOT-NS")

    def test_brudifarma_parser_accepts_non_namespaced_material_nodes(self):
        root = ET.fromstring(
            b"""<cfdi:Comprobante xmlns:cfdi='http://www.sat.gob.mx/cfd/4'>
                    <cfdi:Addenda>
                        <MATERIAL CodigoSAP='7501234567890' Lote='LOT-PLAIN' Caducidad='01.12.2027' Cantidad='10' Precio='2.5'/>
                    </cfdi:Addenda>
                </cfdi:Comprobante>"""
        )
        lots = BrudifarmaAddendaParser().parse(root)
        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0].lote, "LOT-PLAIN")

    def test_brudifarma_parser_strips_fecha_de_caducidad_from_lote(self):
        root = ET.fromstring(
            b"""<cfdi:Comprobante xmlns:cfdi='http://www.sat.gob.mx/cfd/4'>
                    <cfdi:Addenda>
                        <MATERIAL CodigoSAP='7501234567890' Lote='LOT-PLAIN Fecha de caducidad: 01.12.2027' Caducidad='01.12.2027' Cantidad='10' Precio='2.5'/>
                    </cfdi:Addenda>
                </cfdi:Comprobante>"""
        )
        lots = BrudifarmaAddendaParser().parse(root)
        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0].lote, "LOT-PLAIN")


class TestZipExtractor(unittest.TestCase):
    def test_extract_valid_zip(self):
        zip_bytes = _zip_bytes({
            "factura.xml": b"<xml/>",
            "factura.pdf": b"%PDF",
            "nota.txt": b"ignored",
        })

        contents = ZipExtractor().extract(zip_bytes)

        self.assertFalse(contents.errors)
        self.assertEqual(len(contents.xml_files), 1)
        self.assertEqual(len(contents.pdf_files), 1)

    def test_extract_ignores_macos_metadata_pdf(self):
        xml = _sample_cfdi()
        real_pdf = b"%PDF-1.4\nreal-pdf"
        contents = ZipExtractor().extract(_zip_bytes({
            "A1001.xml": xml,
            "__MACOSX/._A1001.pdf": b"not-a-real-pdf",
            ".DS_Store": b"ignored",
            "A1001.pdf": real_pdf,
        }))
        doc = CFDIParser().parse_bytes(xml)

        pairs = contents.pair_xml_pdf([doc])

        self.assertFalse(contents.errors)
        self.assertEqual(contents.pdf_files, [("A1001.pdf", real_pdf)])
        self.assertEqual(pairs[0].pdf_filename, "A1001.pdf")
        self.assertEqual(pairs[0].pdf_bytes, real_pdf)

    def test_extract_skips_invalid_pdf_entries(self):
        contents = ZipExtractor().extract(_zip_bytes({
            "factura.xml": b"<xml/>",
            "factura.pdf": b"not-a-real-pdf",
        }))

        self.assertFalse(contents.pdf_files)
        self.assertIn("no parece un PDF valido", contents.errors[0])

    def test_extract_invalid_zip_reports_error(self):
        contents = ZipExtractor().extract(b"not-a-zip")

        self.assertIn("ZIP no es valido", contents.errors[0])
        self.assertFalse(contents.xml_files)

    def test_pair_by_filename(self):
        xml = _sample_cfdi()
        doc = CFDIParser().parse_bytes(xml)
        contents = ZipExtractor().extract(_zip_bytes({
            "A1001.xml": xml,
            "A1001.pdf": b"%PDF",
        }))

        pairs = contents.pair_xml_pdf([doc])

        self.assertEqual(pairs[0].pdf_filename, "A1001.pdf")

    def test_pair_by_folio(self):
        xml = _sample_cfdi(folio="5599", serie="F")
        doc = CFDIParser().parse_bytes(xml)
        contents = ZipExtractor().extract(_zip_bytes({
            "xml/random.xml": xml,
            "pdf/proveedor-F5599.pdf": b"%PDF",
        }))

        pairs = contents.pair_xml_pdf([doc])

        self.assertEqual(pairs[0].pdf_filename, "pdf/proveedor-F5599.pdf")

    def test_pair_single_fallback(self):
        xml = _sample_cfdi()
        doc = CFDIParser().parse_bytes(xml)
        contents = ZipExtractor().extract(_zip_bytes({
            "one.xml": xml,
            "other.pdf": b"%PDF",
        }))

        pairs = contents.pair_xml_pdf([doc])

        self.assertEqual(pairs[0].pdf_filename, "other.pdf")

    def test_no_xml_error(self):
        contents = ZipExtractor().extract(_zip_bytes({"only.pdf": b"%PDF"}))

        self.assertTrue(contents.errors)
        self.assertFalse(contents.xml_files)


@tagged("post_install", "-at_install")
class TestPurchaseInvoiceImportWizardZipFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Proveedor Parser Test",
            "supplier_rank": 1,
            "vat": "AAA010101AAA",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Producto Parser Test",
            "type": "product",
            "purchase_ok": True,
            "tracking": "lot",
            "barcode": "7501234567890",
        })

    def _wizard(self, values=None):
        vals = values or {}
        return self.env["purchase.invoice.import.wizard"].create(vals)

    def _wizard_with_line(self, quantity=15):
        return self._wizard({
            "partner_id": self.partner.id,
            "cfdi_folio": "TEST-001",
            "state": "review",
            "line_ids": [(0, 0, {
                "no_identificacion": "7501234567890",
                "descripcion": self.product.display_name,
                "product_id": self.product.id,
                "cantidad": quantity,
                "valor_unitario": 10.0,
                "tasa_iva": 0.0,
            })],
        })

    def _add_wizard_lot(self, line, name, quantity, state="missing"):
        return self.env["purchase.invoice.import.wizard.lot"].create({
            "line_id": line.id,
            "name": name,
            "quantity": quantity,
            "state": state,
        })

    def test_action_parse_xml_individual_still_works(self):
        wizard = self._wizard({
            "xml_file": base64.b64encode(_sample_cfdi()),
            "xml_filename": "A1001.xml",
        })

        wizard.action_parse_xml()

        self.assertEqual(wizard.state, "review")
        self.assertEqual(wizard.upload_mode, "individual")
        self.assertEqual(wizard.partner_id, self.partner)
        self.assertEqual(wizard.line_ids.product_id, self.product)

    def test_product_matcher_uses_default_code_for_brudifarma(self):
        product = self.env["product.product"].create({
            "name": "Producto BRUDI Ref",
            "type": "product",
            "purchase_ok": True,
            "tracking": "none",
            "default_code": "508036",
            "barcode": False,
        })
        matcher = ProductMatcher(self.env)
        found, conf, method = matcher.find_product(
            no_identificacion="508036",
            descripcion="Producto BRUDI Ref",
            partner_id=self.partner.id,
            supplier_rfc="BRU971010227",
        )

        self.assertEqual(found, product)
        self.assertEqual(method, "brudifarma_default_code")
        self.assertGreaterEqual(conf, 0.95)

    def test_product_matcher_brudifarma_does_not_fallback_to_name(self):
        product = self.env["product.product"].create({
            "name": "Producto BRUDI Nombre",
            "type": "product",
            "purchase_ok": True,
            "tracking": "none",
            "default_code": "NO-COINCIDE",
            "barcode": False,
        })
        matcher = ProductMatcher(self.env)
        found, conf, method = matcher.find_product(
            no_identificacion="508036",
            descripcion=product.display_name,
            partner_id=self.partner.id,
            supplier_rfc="BRU971010227",
        )

        self.assertFalse(found)
        self.assertEqual(conf, 0.0)
        self.assertEqual(method, "brudifarma_unresolved_code")

    def test_load_pair_brudifarma_resolves_product_using_addenda_cbarra(self):
        product = self.env["product.product"].create({
            "name": "Producto BRUDI CBarra",
            "type": "product",
            "purchase_ok": True,
            "tracking": "lot",
            "default_code": "OTRA-REF",
            "barcode": "7501008427347",
        })
        doc = CFDIDocument(
            emisor_rfc="BRU971010227",
            emisor_nombre="BRUDIFARMA",
            lines=[
                CFDILine(
                    no_identificacion="508036",
                    descripcion="Producto BRUDI CBarra",
                    cantidad=5.0,
                    valor_unitario=10.0,
                    importe=50.0,
                    clave_unidad="H87",
                    unidad="PZA",
                    clave_prod_serv="51151508",
                    tasa_iva=0.0,
                    importe_iva=0.0,
                    factor_iva="Tasa",
                    iva_presente=True,
                ),
            ],
            addenda_lots=[
                AddendaLot(
                    codigo_sap="508036",
                    lote="GP03EVG",
                    caducidad=date(2028, 11, 30),
                    cantidad=5.0,
                    precio=10.0,
                    cbarra="7501008427347",
                ),
            ],
        )
        wizard = self._wizard()
        wizard._load_pair(
            xml_bytes=b"<cfdi:Comprobante xmlns:cfdi='http://www.sat.gob.mx/cfd/4'/>",
            xml_filename="brudi.xml",
            doc=doc,
        )

        self.assertEqual(wizard.line_ids.product_id, product)
        self.assertEqual(wizard.line_ids.product_match_method, "brudifarma_addenda_cbarra")

    def test_load_pair_brudifarma_prioritizes_addenda_lote_field_over_descripcion(self):
        product = self.env["product.product"].create({
            "name": "Producto BRUDI Addenda Prioridad",
            "type": "product",
            "purchase_ok": True,
            "tracking": "lot",
            "default_code": "512177",
            "barcode": "75050740",
        })
        doc = CFDIDocument(
            emisor_rfc="BRU971010227",
            emisor_nombre="BRUDIFARMA",
            lines=[
                CFDILine(
                    no_identificacion="512177",
                    descripcion="TOBRAMICINA ... Lote: DESDE-DESCRIP Fecha de caducidad: 31.07.2027",
                    descripcion_lot="DESDE-DESCRIP",
                    descripcion_caducidad=date(2027, 7, 31),
                    cantidad=5.0,
                    valor_unitario=10.0,
                    importe=50.0,
                    clave_unidad="H87",
                    unidad="PZA",
                    clave_prod_serv="51101582",
                    tasa_iva=0.0,
                    importe_iva=0.0,
                    factor_iva="Tasa",
                    iva_presente=True,
                ),
            ],
            addenda_lots=[
                AddendaLot(
                    codigo_sap="512177",
                    lote="25363P",
                    caducidad=date(2027, 7, 31),
                    cantidad=5.0,
                    precio=10.0,
                    cbarra="75050740",
                ),
            ],
        )
        wizard = self._wizard()
        wizard._load_pair(
            xml_bytes=b"<cfdi:Comprobante xmlns:cfdi='http://www.sat.gob.mx/cfd/4'/>",
            xml_filename="brudi_addenda_priority.xml",
            doc=doc,
        )

        self.assertEqual(wizard.line_ids.product_id, product)
        self.assertEqual(len(wizard.line_ids.lot_ids), 1)
        self.assertEqual(wizard.line_ids.lot_ids.name, "25363P")
        self.assertIn("Addenda XML (BRUDIFARMA)", wizard.lots_summary)

    def test_load_pair_brudifarma_uses_addenda_even_if_pdf_is_uploaded(self):
        self.env["res.partner"].create({
            "name": "BRUDIFARMA TEST PRIORITY",
            "supplier_rank": 1,
            "vat": "BRU971010227",
        })
        self.env["product.product"].create({
            "name": "Producto BRUDI Addenda PDF",
            "type": "product",
            "purchase_ok": True,
            "tracking": "lot",
            "default_code": "512177",
            "barcode": "75050740",
        })
        doc = CFDIDocument(
            emisor_rfc="BRU971010227",
            emisor_nombre="BRUDIFARMA",
            lines=[
                CFDILine(
                    no_identificacion="512177",
                    descripcion="TOBRAMICINA ... Lote: DESDE-DESCRIP Fecha de caducidad: 31.07.2027",
                    descripcion_lot="DESDE-DESCRIP",
                    descripcion_caducidad=date(2027, 7, 31),
                    cantidad=5.0,
                    valor_unitario=10.0,
                    importe=50.0,
                    clave_unidad="H87",
                    unidad="PZA",
                    clave_prod_serv="51101582",
                    tasa_iva=0.0,
                    importe_iva=0.0,
                    factor_iva="Tasa",
                    iva_presente=True,
                ),
            ],
            addenda_lots=[
                AddendaLot(
                    codigo_sap="512177",
                    lote="25363P",
                    caducidad=date(2027, 7, 31),
                    cantidad=5.0,
                    precio=10.0,
                    cbarra="75050740",
                ),
            ],
        )
        wizard = self._wizard({
            "pdf_file": base64.b64encode(b"%PDF-1.4 fake brudi"),
            "pdf_filename": "brudi.pdf",
        })
        with patch.object(BrudifarmaProvider, "parse", side_effect=AssertionError("PDF parse no esperado")):
            wizard._load_pair(
                xml_bytes=b"<cfdi:Comprobante xmlns:cfdi='http://www.sat.gob.mx/cfd/4'/>",
                xml_filename="brudi_pdf_should_not_override_addenda.xml",
                doc=doc,
            )

        self.assertEqual(len(wizard.line_ids.lot_ids), 1)
        self.assertEqual(wizard.line_ids.lot_ids.name, "25363P")
        self.assertIn("Addenda XML (BRUDIFARMA)", wizard.lots_summary)

    def test_brudifarma_purchase_order_flow_does_not_create_new_products(self):
        brudi_partner = self.env["res.partner"].create({
            "name": "BRUDIFARMA TEST",
            "supplier_rank": 1,
            "vat": "BRU971010227",
        })
        product = self.env["product.product"].create({
            "name": "Producto BRUDI Sin Alta Nueva",
            "type": "product",
            "purchase_ok": True,
            "tracking": "lot",
            "default_code": "508036",
            "barcode": False,
        })
        product_count_before = self.env["product.product"].search_count([])

        doc = CFDIDocument(
            emisor_rfc="BRU971010227",
            emisor_nombre="BRUDIFARMA TEST",
            folio="BRUDI-PO-001",
            fecha="2026-05-19",
            lines=[
                CFDILine(
                    no_identificacion="508036",
                    descripcion="Producto BRUDI Sin Alta Nueva",
                    cantidad=5.0,
                    valor_unitario=10.0,
                    importe=50.0,
                    clave_unidad="H87",
                    unidad="PZA",
                    clave_prod_serv="51151508",
                    tasa_iva=0.0,
                    importe_iva=0.0,
                    factor_iva="Tasa",
                    iva_presente=True,
                ),
            ],
        )
        wizard = self._wizard()
        wizard._load_pair(
            xml_bytes=b"<cfdi:Comprobante xmlns:cfdi='http://www.sat.gob.mx/cfd/4'/>",
            xml_filename="brudi_no_new_products.xml",
            doc=doc,
        )
        self.assertEqual(wizard.partner_id, brudi_partner)
        self.assertEqual(wizard.line_ids.product_id, product)

        # Producto con tracking='lot': el Hard Stop de lotes exige un lote válido.
        self._add_wizard_lot(wizard.line_ids, "LOT-BRUDI-NO-NEW-PROD", 5)

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])
        product_count_after = self.env["product.product"].search_count([])

        self.assertEqual(product_count_after, product_count_before)
        self.assertEqual(order.order_line.product_id, product)

    def test_action_parse_zip_single_pair(self):
        zip_bytes = _zip_bytes({
            "A1001.xml": _sample_cfdi(),
            "A1001.pdf": b"%PDF",
        })
        wizard = self._wizard({
            "upload_mode": "zip",
            "zip_file": base64.b64encode(zip_bytes),
            "zip_filename": "facturas.zip",
        })

        with patch.object(GenericProvider, "parse", return_value={}), patch.object(
            GenericProvider, "diagnose", return_value=""
        ):
            wizard.action_parse_zip()

        self.assertEqual(wizard.state, "review")
        self.assertEqual(wizard.zip_total_pairs, 1)
        self.assertEqual(wizard.zip_current_pair_index, 1)
        self.assertEqual(wizard.xml_filename, "A1001.xml")
        self.assertEqual(wizard.pdf_filename, "A1001.pdf")

    def test_parse_pdf_uses_brudifarma_provider_when_rfc_matches(self):
        wizard = self._wizard({
            "partner_id": self.partner.id,
            "emisor_rfc": "BRU971010227",
            "cfdi_folio": "BRU-TEST",
            "state": "review",
            "pdf_file": base64.b64encode(b"%PDF dummy content"),
            "line_ids": [(0, 0, {
                "no_identificacion": "508036",
                "descripcion": self.product.display_name,
                "product_id": self.product.id,
                "cantidad": 5,
                "valor_unitario": 10.0,
                "tasa_iva": 0.0,
            })],
        })

        parsed_lots = {
            "508036": [{
                "name": "LOT-BRUDI-1",
                "expiration_date": date(2028, 11, 30),
                "quantity": 5,
                "discount": 0.0,
            }],
        }

        with patch.object(BrudifarmaProvider, "parse", return_value=parsed_lots):
            wizard.action_parse_pdf()

        self.assertTrue(wizard.pdf_parsed)
        self.assertEqual(len(wizard.line_ids.lot_ids), 1)
        self.assertEqual(wizard.line_ids.lot_ids.name, "LOT-BRUDI-1")

    def test_action_parse_zip_multiple_pairs_then_create_orders(self):
        zip_bytes = _zip_bytes({
            "A1001.xml": _sample_cfdi(folio="1001"),
            "A1002.xml": _sample_cfdi(folio="1002"),
        })
        wizard = self._wizard({
            "upload_mode": "zip",
            "zip_file": base64.b64encode(zip_bytes),
            "zip_filename": "facturas.zip",
        })

        wizard.action_parse_zip()
        self.assertEqual(wizard.cfdi_folio, "A1001")

        # Producto con tracking='lot': el Hard Stop de lotes exige un lote válido
        # en cada par XML/PDF antes de crear su OC.
        self._add_wizard_lot(wizard.line_ids, "LOT-ZIP-1001", 15)
        wizard.action_create_purchase_order()
        self.assertEqual(wizard.state, "review")
        self.assertEqual(wizard.zip_current_pair_index, 2)
        self.assertEqual(wizard.cfdi_folio, "A1002")

        self._add_wizard_lot(wizard.line_ids, "LOT-ZIP-1002", 15)
        action = wizard.action_create_purchase_order()
        self.assertEqual(wizard.state, "done")
        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(len(wizard._zip_created_po_ids()), 2)

    def test_multi_lot_pdf_keeps_one_purchase_line(self):
        wizard = self._wizard_with_line(quantity=15)
        line = wizard.line_ids
        self._add_wizard_lot(line, "LOT-A", 10)
        self._add_wizard_lot(line, "LOT-B", 5)

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])

        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_id, self.product)
        self.assertEqual(order.order_line.product_qty, 15)
        if "lot_id" in order.order_line._fields:
            self.assertFalse(
                order.order_line.lot_id,
                "No debe escoger un lote arbitrario cuando el PDF trae varios.",
            )

    def test_single_lot_pdf_assigns_lot_without_extra_lines(self):
        if "lot_id" not in self.env["purchase.order.line"]._fields:
            self.skipTest("purchase_lot_selection no esta instalado")
        wizard = self._wizard_with_line(quantity=15)
        line = wizard.line_ids
        self._add_wizard_lot(line, "LOT-UNICO", 15)

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])

        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_id, self.product)
        self.assertEqual(order.order_line.lot_id.name, "LOT-UNICO")

    def test_parse_pdf_multi_lot_flow_keeps_single_purchase_line(self):
        wizard = self._wizard_with_line(quantity=15)
        wizard.pdf_file = base64.b64encode(b"%PDF dummy content")
        line = wizard.line_ids
        parsed_lots = {
            "7501234567890": [
                {
                    "name": "LOT-PDF-A",
                    "expiration_date": date(2027, 5, 1),
                    "quantity": 10,
                    "discount": 0.0,
                },
                {
                    "name": "LOT-PDF-B",
                    "expiration_date": date(2027, 6, 1),
                    "quantity": 5,
                    "discount": 0.0,
                },
            ],
        }

        with patch.object(GenericProvider, "parse", return_value=parsed_lots):
            wizard.action_parse_pdf()

        self.assertTrue(wizard.pdf_parsed)
        self.assertEqual(len(line.lot_ids), 2)
        self.assertIn("Productos con más de un lote", wizard.lots_summary)
        self.assertIn("conservará una línea por concepto CFDI", wizard.lots_summary)

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])

        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_id, self.product)
        self.assertEqual(order.order_line.product_qty, 15)
        if "lot_id" in order.order_line._fields:
            self.assertFalse(
                order.order_line.lot_id,
                "La OC no debe elegir un lote arbitrario cuando el PDF trae varios.",
            )

    def test_create_po_clears_supplier_taxes_when_xml_has_no_iva(self):
        tax_16 = self.env["account.tax"].search([
            ("type_tax_use", "=", "purchase"),
            ("company_id", "=", self.env.company.id),
            ("amount_type", "=", "percent"),
            ("amount", "=", 16.0),
        ], limit=1)
        if not tax_16:
            tax_16 = self.env["account.tax"].create({
                "name": "IVA Compras 16 Test",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 16.0,
            })
        self.product.write({"supplier_taxes_id": [(6, 0, tax_16.ids)]})

        wizard = self._wizard({
            "partner_id": self.partner.id,
            "cfdi_folio": "TEST-NO-IVA",
            "state": "review",
            "line_ids": [(0, 0, {
                "no_identificacion": "7501234567890",
                "descripcion": self.product.display_name,
                "product_id": self.product.id,
                "cantidad": 1,
                "valor_unitario": 10.0,
                "tasa_iva": 0.0,
                "factor_iva": "",
                "iva_presente": False,
            })],
        })
        # Producto con tracking='lot': el Hard Stop de lotes exige un lote válido.
        self._add_wizard_lot(wizard.line_ids, "LOT-NO-IVA", 1)

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])

        self.assertFalse(order.order_line.tax_ids)
        self.assertEqual(order.company_id, wizard.target_company_id)

    def test_create_po_allows_iva_zero_when_tax_not_configured(self):
        tax_16 = self.env["account.tax"].search([
            ("type_tax_use", "=", "purchase"),
            ("company_id", "=", self.env.company.id),
            ("amount_type", "=", "percent"),
            ("amount", "=", 16.0),
        ], limit=1)
        if not tax_16:
            tax_16 = self.env["account.tax"].create({
                "name": "IVA Compras 16 Test",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 16.0,
            })
        self.product.write({"supplier_taxes_id": [(6, 0, tax_16.ids)]})

        zero_taxes = self.env["account.tax"].search([
            ("type_tax_use", "=", "purchase"),
            ("company_id", "=", self.env.company.id),
            ("amount", "=", 0.0),
            ("active", "=", True),
        ])
        zero_taxes.write({"active": False})

        wizard = self._wizard({
            "partner_id": self.partner.id,
            "target_company_id": self.env.company.id,
            "cfdi_folio": "TEST-IVA-0",
            "state": "review",
            "line_ids": [(0, 0, {
                "no_identificacion": "7501234567890",
                "descripcion": self.product.display_name,
                "product_id": self.product.id,
                "cantidad": 1,
                "valor_unitario": 10.0,
                "tasa_iva": 0.0,
                "factor_iva": "Tasa",
                "iva_presente": True,
            })],
        })
        # Producto con tracking='lot': el Hard Stop de lotes exige un lote válido.
        self._add_wizard_lot(wizard.line_ids, "LOT-IVA-0", 1)

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])
        self.assertFalse(order.order_line.tax_ids)

    def test_create_po_raises_when_iva_not_found_for_matriz(self):
        # Fuerza etiqueta de compañía con "Matriz" para validar el mensaje al usuario.
        self.env.company.write({"name": "Matriz Test"})
        existing_amounts = set(
            self.env["account.tax"].search([
                ("type_tax_use", "=", "purchase"),
                ("company_id", "=", self.env.company.id),
                ("amount_type", "=", "percent"),
            ]).mapped("amount")
        )
        candidate_pct = None
        for pct in [91.2345, 73.9876, 17.6543, 12.3456]:
            if pct not in existing_amounts:
                candidate_pct = pct
                break
        self.assertIsNotNone(candidate_pct)

        wizard = self._wizard({
            "partner_id": self.partner.id,
            "target_company_id": self.env.company.id,
            "cfdi_folio": "TEST-MISSING-TAX-MATRIZ",
            "state": "review",
            "line_ids": [(0, 0, {
                "no_identificacion": "7501234567890",
                "descripcion": self.product.display_name,
                "product_id": self.product.id,
                "cantidad": 1,
                "valor_unitario": 10.0,
                "tasa_iva": candidate_pct / 100.0,
                "factor_iva": "Tasa",
                "iva_presente": True,
            })],
        })

        with self.assertRaises(UserError) as err:
            wizard.action_create_purchase_order()
        self.assertIn("Matriz", str(err.exception))

    def test_create_po_prefers_iva_compras_named_tax(self):
        existing_amounts = set(
            self.env["account.tax"].search([
                ("type_tax_use", "=", "purchase"),
                ("company_id", "=", self.env.company.id),
                ("amount_type", "=", "percent"),
            ]).mapped("amount")
        )
        candidate_pct = None
        for pct in [97.1234, 83.4567, 61.4321, 43.2198]:
            if pct not in existing_amounts:
                candidate_pct = pct
                break
        self.assertIsNotNone(candidate_pct)

        generic_tax = self.env["account.tax"].create({
            "name": "IVA Prueba General",
            "type_tax_use": "purchase",
            "amount_type": "percent",
            "amount": candidate_pct,
            "company_id": self.env.company.id,
            "sequence": 1,
        })
        compras_tax = self.env["account.tax"].create({
            "name": "IVA Prueba Compras",
            "type_tax_use": "purchase",
            "amount_type": "percent",
            "amount": candidate_pct,
            "company_id": self.env.company.id,
            "sequence": 99,
        })

        wizard = self._wizard({
            "partner_id": self.partner.id,
            "target_company_id": self.env.company.id,
            "cfdi_folio": "TEST-IVA-COMPRAS-PREF",
            "state": "review",
            "line_ids": [(0, 0, {
                "no_identificacion": "7501234567890",
                "descripcion": self.product.display_name,
                "product_id": self.product.id,
                "cantidad": 1,
                "valor_unitario": 10.0,
                "tasa_iva": candidate_pct / 100.0,
                "factor_iva": "Tasa",
                "iva_presente": True,
            })],
        })
        # Producto con tracking='lot': el Hard Stop de lotes exige un lote válido.
        self._add_wizard_lot(wizard.line_ids, "LOT-IVA-COMPRAS-PREF", 1)

        action = wizard.action_create_purchase_order()
        order = self.env["purchase.order"].browse(action["res_id"])

        self.assertIn(compras_tax.id, order.order_line.tax_ids.ids)
        self.assertNotIn(generic_tax.id, order.order_line.tax_ids.ids)

    def test_addenda_population_keeps_pdf_parsed_flag_false(self):
        wizard = self._wizard_with_line(quantity=15)
        line = wizard.line_ids
        wizard._do_populate_addenda_lots([
            AddendaLot(
                codigo_sap="7501234567890",
                lote="LOT-ADDENDA-1",
                caducidad=date(2027, 5, 1),
                cantidad=15,
                precio=10.0,
            ),
        ])

        self.assertFalse(wizard.pdf_parsed)
        self.assertEqual(len(line.lot_ids), 1)
        self.assertIn("Addenda XML", wizard.lots_summary)

    def test_addenda_population_does_not_duplicate_lots_on_repeated_line_code(self):
        wizard = self._wizard({
            "partner_id": self.partner.id,
            "cfdi_folio": "TEST-ADDENDA-DUP",
            "state": "review",
            "line_ids": [
                (0, 0, {
                    "no_identificacion": "7501234567890",
                    "descripcion": "Linea 1",
                    "product_id": self.product.id,
                    "cantidad": 10,
                    "valor_unitario": 10.0,
                    "tasa_iva": 0.0,
                }),
                (0, 0, {
                    "no_identificacion": "7501234567890",
                    "descripcion": "Linea 2",
                    "product_id": self.product.id,
                    "cantidad": 10,
                    "valor_unitario": 10.0,
                    "tasa_iva": 0.0,
                }),
            ],
        })
        wizard._do_populate_addenda_lots([
            AddendaLot(
                codigo_sap="7501234567890",
                lote="LOT-A",
                caducidad=date(2027, 5, 1),
                cantidad=10,
                precio=1.0,
            ),
            AddendaLot(
                codigo_sap="7501234567890",
                lote="LOT-B",
                caducidad=date(2027, 6, 1),
                cantidad=10,
                precio=1.0,
            ),
        ])

        total_lots = sum(len(line.lot_ids) for line in wizard.line_ids)
        self.assertEqual(total_lots, 2)
        self.assertIn("sin auto-distribución", wizard.lots_summary)

    def test_addenda_population_skips_rows_without_codigo_sap(self):
        wizard = self._wizard_with_line(quantity=15)
        wizard._do_populate_addenda_lots([
            AddendaLot(
                codigo_sap="",
                lote="LOT-NO-CODE",
                caducidad=date(2027, 5, 1),
                cantidad=10,
                precio=1.0,
            ),
        ])

        self.assertFalse(wizard.line_ids.lot_ids)
        self.assertIn("sin CodigoSAP", wizard.lots_summary)

    def test_addenda_population_fallbacks_to_product_barcode(self):
        product = self.env["product.product"].create({
            "name": "Producto BRUDI Barcode Fallback",
            "type": "product",
            "purchase_ok": True,
            "tracking": "lot",
            "default_code": "BRUDI-X",
            "barcode": "7502223111431",
        })
        wizard = self._wizard({
            "partner_id": self.partner.id,
            "cfdi_folio": "TEST-ADDENDA-BARCODE",
            "state": "review",
            "line_ids": [(0, 0, {
                "no_identificacion": "CODIGO-NO-MATCH",
                "descripcion": "Linea barcode",
                "product_id": product.id,
                "cantidad": 5,
                "valor_unitario": 10.0,
                "tasa_iva": 0.0,
            })],
        })
        wizard._do_populate_addenda_lots([
            AddendaLot(
                codigo_sap="OTRO-CODIGO",
                lote="26DP42",
                caducidad=date(2028, 4, 30),
                cantidad=5.0,
                precio=1.0,
                cbarra="7502223111431",
            ),
        ])

        self.assertEqual(len(wizard.line_ids.lot_ids), 1)
        self.assertEqual(wizard.line_ids.lot_ids.name, "26DP42")

    def test_addenda_population_merges_duplicate_material_rows(self):
        wizard = self._wizard_with_line(quantity=15)
        line = wizard.line_ids
        wizard._do_populate_addenda_lots([
            AddendaLot(
                codigo_sap="7501234567890",
                lote="LOT-DUP",
                caducidad=date(2027, 5, 1),
                cantidad=2.0,
                precio=1.0,
            ),
            AddendaLot(
                codigo_sap="7501234567890",
                lote="LOT-DUP",
                caducidad=date(2027, 5, 1),
                cantidad=3.0,
                precio=1.0,
            ),
        ])

        self.assertEqual(len(line.lot_ids), 1)
        self.assertEqual(line.lot_ids.quantity, 5.0)
        self.assertIn("Filas Addenda desduplicadas", wizard.lots_summary)

    def test_addenda_population_matches_existing_numeric_lot_with_leading_zeros(self):
        existing_lot = self.env["stock.lot"].create({
            "name": "0006092",
            "product_id": self.product.id,
            "company_id": self.env.company.id,
        })
        wizard = self._wizard({
            "partner_id": self.partner.id,
            "cfdi_folio": "TEST-ADDENDA-LOT-ZEROS",
            "state": "review",
            "line_ids": [(0, 0, {
                "no_identificacion": "501486",
                "descripcion": "Linea lote numerico",
                "product_id": self.product.id,
                "cantidad": 5,
                "valor_unitario": 10.0,
                "tasa_iva": 0.0,
            })],
        })
        wizard._do_populate_addenda_lots([
            AddendaLot(
                codigo_sap="501486",
                lote="6092",
                caducidad=date(2028, 3, 31),
                cantidad=5.0,
                precio=1.0,
            ),
        ])

        self.assertEqual(len(wizard.line_ids.lot_ids), 1)
        self.assertEqual(wizard.line_ids.lot_ids.state, "found")
        self.assertEqual(wizard.line_ids.lot_ids.existing_lot_id, existing_lot)

    def test_manual_missing_lot_creation_button_is_not_exposed(self):
        view = self.env.ref("purchase_invoice_parser.view_cfdi_import_wizard_form")

        self.assertNotIn("action_create_missing_lots", view.arch_db)
        self.assertNotIn("Crear lotes faltantes", view.arch_db)
        self.assertIn('invisible="not pdf_file or pdf_parsed"', view.arch_db)

    def test_lot_stock_resolver_creates_global_lot(self):
        resolver = LotStockResolver(self.env, self.env.company.id)

        lot = resolver.ensure(self.product, "LOT-GLOBAL-PARSER")

        self.assertEqual(lot.name, "LOT-GLOBAL-PARSER")
        self.assertFalse(lot.company_id)

    def test_lot_stock_resolver_globalizes_company_lot(self):
        company_lot = self.env["stock.lot"].create({
            "name": "LOT-COMPANY-PARSER",
            "product_id": self.product.id,
            "company_id": self.env.company.id,
        })
        resolver = LotStockResolver(self.env, self.env.company.id)

        lot = resolver.ensure(self.product, "LOT-COMPANY-PARSER")

        self.assertEqual(lot.id, company_lot.id)
        self.assertFalse(lot.company_id)
