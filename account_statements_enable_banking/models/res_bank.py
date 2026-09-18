
from odoo import _, api, fields, models, Command


class ResBank(models.Model):
    _inherit = "res.bank"

    enable_banking_config_ids = fields.One2many('enable.banking.config', 'bank_id')
