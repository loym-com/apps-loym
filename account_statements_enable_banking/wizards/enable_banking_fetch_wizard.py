
from odoo import fields, models


class EnableBankingFetchWizard(models.TransientModel):
    _name = "enable.banking.fetch.wizard"
    _description = "Enable Banking Fetch Wizard"

    date_from = fields.Date(string="From", required=True, default=fields.Date.today)
    date_to = fields.Date(string="To", required=True, default=fields.Date.today)

    def action_fetch(self):
        self.ensure_one()
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        active_record = self.env[active_model].browse(active_id)
        if active_model == "account.journal":
            config = active_record.enable_banking_config
        else:
            config = active_record

        config._fetch_transactions(self.date_from, self.date_to)
        action = self.env.ref("account.action_bank_statement_tree").sudo().read([])[0]
        action["domain"] = [("journal_id", "in", config.journal_ids.ids)]
        return action
