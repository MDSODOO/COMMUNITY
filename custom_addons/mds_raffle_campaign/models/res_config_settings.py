from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mds_raffle_whatsapp_api_token = fields.Char(
        string='Token API (Meta Cloud API)',
        config_parameter='mds_raffle_campaign.whatsapp_api_token',
    )
    mds_raffle_whatsapp_phone_number_id = fields.Char(
        string='Phone Number ID',
        config_parameter='mds_raffle_campaign.whatsapp_phone_number_id',
    )
    mds_raffle_whatsapp_business_account_id = fields.Char(
        string='Business Account ID',
        config_parameter='mds_raffle_campaign.whatsapp_business_account_id',
    )
    mds_raffle_n8n_webhook_url = fields.Char(
        string='Webhook n8n (boletos creados)',
        config_parameter='mds_raffle_campaign.n8n_webhook_url',
    )
