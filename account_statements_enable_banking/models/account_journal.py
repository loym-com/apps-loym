import logging

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    enable_banking_config = fields.Many2one('enable.banking.config', string="Configuration", ondelete='restrict')
    enable_banking_valid_until = fields.Datetime(related='enable_banking_config.valid_until')
    enable_banking_status = fields.Selection([
        ('not_connected', 'Not Connected'),
        ('connected', 'Connected'),
        ('expired', 'Expired'),
        ('error', 'Error'),
    ], compute='_compute_enable_banking_status')
    enable_banking_account_id = fields.Char(readonly=True)

    @api.onchange('bank_statements_source')
    def _onchange_enable_banking_config(self):
        if self.bank_statements_source != 'enable_banking':
            self.enable_banking_config = False

    @api.depends('enable_banking_account_id', 'enable_banking_config.connection_status')
    def _compute_enable_banking_status(self):
        for record in self:
            if record.enable_banking_account_id:
                record.enable_banking_status = record.enable_banking_config.connection_status
            else:
                record.enable_banking_status = 'not_connected'

    def action_open_enable_banking_config(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.enable_banking_config.id,
            'res_model': 'enable.banking.config',
        }

    def __get_bank_statements_available_sources(self):
        res = super(AccountJournal, self).__get_bank_statements_available_sources()
        return res + [('enable_banking', _('Enable Banking'))]

    def action_configure_bank_journal(self):
        if self.bank_id.enable_banking_config_ids:
            self.enable_banking_config = self.bank_id.enable_banking_config_ids[0]
            self.bank_statements_source = 'enable_banking'

            return self.action_open_enable_banking_config()

        return {
            'name': _('Connect %s with Enable Banking', self.bank_account_id.display_name),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'context': {
                'default_journal_ids': [Command.link(self.id)],
                'default_bank_id': self.bank_id.id,
                'default_name': self.bank_id.name
            },
            'res_model': 'enable.banking.config',
            'target': 'new',
            'views': [[self.env.ref('account_statements_enable_banking.view_enable_banking_config_form_connect').id, 'form']],
        }

    def action_enable_banking_connect(self):
        return self.enable_banking_config.action_connect()
