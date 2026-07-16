# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase
import re
from pathlib import Path


class AfiliacionTemplateTest(HttpCase):
    """Pruebas unitarias para la página de afiliación profesional."""

    def setUp(self):
        super().setUp()
        self.url_afiliacion = '/afiliacion'

    def test_01_afiliacion_page_loads(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        self.assertEqual(response.status_code, 200)

    def test_02_page_contains_bento_structure(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        self.assertIn('md_bento_portal', content)
        self.assertIn('o_portal_wrap', content)
        self.assertIn('container mt-4 mb-5', content)
        self.assertIn('md_data_card--afiliacion_main', content)
        self.assertIn('md_affiliacion_body', content)
        self.assertIn('afiliacion_form', content)
        self.assertNotIn('md_floating_nav', content)

    def test_03_form_attributes_correct(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        self.assertIn('method="POST"', content)
        self.assertIn('enctype="multipart/form-data"', content)
        self.assertIn('csrf_token', content)

    def test_04_general_fields_present(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        required_fields = [
            'nombre',
            'email',
            'telefono',
            'especialidad',
            'x_studio_contact_type',
            'x_studio_person_type',
            'x_studio_branch_office',
        ]
        for field in required_fields:
            self.assertIn(f'name="{field}"', content, f"Falta campo {field}")

    def test_05_file_fields_present(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        file_fields = [
            'x_studio_operation_notice',
            'x_studio_sanitary_license',
            'x_studio_sanitary_responsible_notice',
            'x_studio_ine',
            'x_studio_proof_of_address',
            'x_studio_professional_license',
            'x_studio_tax_status_certificate',
        ]
        for field in file_fields:
            self.assertIn(f'name="{field}"', content, f"Falta file field {field}")

    def test_06_sections_present(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        self.assertIn('Datos Generales', content)
        self.assertIn('COFEPRIS', content)
        self.assertIn('Documentos Legales', content)

    def test_07_submit_and_privacy_present(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        self.assertIn('name="privacy"', content)
        self.assertIn('aviso de privacidad', content.lower())
        self.assertIn('type="submit"', content)
        self.assertIn('Enviar solicitud', content)

    def test_08_success_screen_present(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        self.assertIn('success_screen', content)
        self.assertIn('md_affiliacion_success', content)

    def test_09_form_posts_to_same_route(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        form_match = re.search(r'<form[^>]*id="afiliacion_form"[^>]*>', content)
        self.assertIsNotNone(form_match)
        form_tag = form_match.group(0)
        self.assertFalse('action=' in form_tag or 'action =' in form_tag)

    def test_10_term_disponible_not_used(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        self.assertNotIn('Disponible', content)
        self.assertNotIn('disponible', content)

    def test_11_single_main_card_layout(self):
        response = self.url_open(self.url_afiliacion, timeout=60)
        content = response.text

        self.assertEqual(content.count('md_data_card--afiliacion_main'), 1)
        self.assertIn('md_affiliacion_section--general', content)
        self.assertIn('md_affiliacion_section--cofepris', content)
        self.assertIn('md_affiliacion_section--docs', content)
        self.assertIn('md_affiliacion_section--submit', content)

    def test_12_post_multipart_with_files_no_partner_write_error(self):
        """Prueba smoke de POST multipart para validar guardado sin crash."""
        get_response = self.url_open(self.url_afiliacion, timeout=60)
        self.assertEqual(get_response.status_code, 200)
        csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', get_response.text)
        self.assertIsNotNone(csrf_match, "No se encontró csrf_token en el formulario")

        email = "qa.afiliacion.multipart@medicinedepot.test"
        post_data = {
            'csrf_token': csrf_match.group(1),
            'nombre': 'QA Afiliacion Multipart',
            'email': email,
            'telefono': '9999999999',
            'especialidad': 'Card Integrado QA',
            'x_studio_contact_type': '',
            'x_studio_person_type': '',
            'x_studio_branch_office': '',
            'privacy': 'on',
        }
        files = {
            'x_studio_ine': ('ine_qa.txt', b'INE QA', 'text/plain'),
            'x_studio_tax_status_certificate': ('csf_qa.txt', b'CSF QA', 'text/plain'),
        }

        post_response = self.url_open(self.url_afiliacion, data=post_data, files=files, timeout=120)
        self.assertEqual(post_response.status_code, 200)
        payload = post_response.json()
        self.assertTrue(payload.get('success'))

        partner = self.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
        self.assertTrue(partner, "No se creó/actualizó partner tras POST multipart")

        if 'function' in partner._fields:
            self.assertEqual(partner.function, 'Card Integrado QA')

        for binary_field in ('x_studio_ine', 'x_studio_tax_status_certificate'):
            if binary_field in partner._fields:
                self.assertTrue(getattr(partner, binary_field), f"No se guardó {binary_field}")

    def test_13_focus_and_conditional_markup_present(self):
        views_dir = Path(__file__).resolve().parents[1] / 'views'
        afiliacion_xml = (views_dir / 'afiliacion_templates.xml').read_text(encoding='utf-8')
        portal_xml = (views_dir / 'portal_templates.xml').read_text(encoding='utf-8')

        self.assertNotIn('t-set="no_header"', afiliacion_xml)
        self.assertIn('id="wrap" class="o_portal_wrap', afiliacion_xml)
        self.assertIn('t-if="not is_affiliate"', afiliacion_xml)
        self.assertIn('id="documentos-pendientes"', afiliacion_xml)
        self.assertIn('t-if="has_missing_docs"', portal_xml)
        self.assertIn('md_aff_docs_alert', portal_xml)
        self.assertNotIn('partner.x_studio_branch_office == opt[0]', afiliacion_xml)
        self.assertNotIn('partner.x_studio_branch_office == opt[0]', portal_xml)
        self.assertIn('selected_branch_office == opt[0]', afiliacion_xml)
        self.assertIn('selected_branch_office == opt[0]', portal_xml)
