from odoo import fields, models


class MdRegulatoryReview(models.Model):
    _name = 'md.regulatory.review'
    _description = 'Candidato de homologación regulatoria (PLM) pendiente de revisión manual'
    _order = 'create_date desc'

    product_id = fields.Many2one('product.template', required=True, string='Producto')
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], default='pending', string='Estado', required=True)

    search_term = fields.Char(string='Término buscado en PLM')
    match_confidence = fields.Selection([
        ('high', 'Alta: marca coincide exacto'),
        ('low', 'Baja: sin coincidencia clara / ambiguo'),
    ], string='Confianza del match automático')
    candidate_label = fields.Char(string='Marca candidata (PLM)')
    candidate_description = fields.Text(string='Descripción (PLM)')
    candidate_pharma_form = fields.Char(string='Forma farmacéutica (PLM)')
    candidate_product_type = fields.Char(string='Tipo (OTC/Rx, según PLM)')
    plm_search_url = fields.Char(string='Buscar en PLM (verificación manual)')

    proposed_concentracion = fields.Char(string='Concentración a aplicar')
    proposed_forma_farmaceutica = fields.Char(string='Forma farmacéutica a aplicar')
    proposed_laboratorio = fields.Char(string='Línea/Laboratorio a aplicar')
    proposed_registro_sanitario = fields.Char(string='Registro sanitario a aplicar')
    proposed_substance_name = fields.Char(string='Sustancia activa a aplicar')

    reviewer_notes = fields.Text(string='Notas del revisor')

    def action_approve(self):
        substance_model = self.env['md.active.substance']
        line_model = self.env['md.product.line']
        for rec in self:
            vals = {}
            if rec.proposed_concentracion:
                vals['l10n_mx_concentracion'] = rec.proposed_concentracion
            if rec.proposed_forma_farmaceutica:
                vals['l10n_mx_forma_farmaceutica'] = rec.proposed_forma_farmaceutica
            if rec.proposed_registro_sanitario:
                vals['l10n_mx_registro_sanitario'] = rec.proposed_registro_sanitario
            if rec.proposed_laboratorio:
                line = line_model.search([('name', '=', rec.proposed_laboratorio)], limit=1)
                if not line:
                    line = line_model.create({'name': rec.proposed_laboratorio})
                vals['product_line_id'] = line.id
            if vals:
                rec.product_id.write(vals)
            if rec.proposed_substance_name:
                substance = substance_model.search([('name', '=', rec.proposed_substance_name)], limit=1)
                if not substance:
                    substance = substance_model.create({'name': rec.proposed_substance_name})
                rec.product_id.active_substance_ids = [(4, substance.id)]
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_pending(self):
        self.write({'state': 'pending'})
