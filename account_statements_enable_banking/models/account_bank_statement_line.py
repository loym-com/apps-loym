from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    enable_banking_id = fields.Char(readonly=True, copy=False)

    _sql_constraints = [
        (
            "enable_banking_id",
            "unique(enable_banking_id)",
            "Enable Banking transaction can be imported only once",
        )
    ]
