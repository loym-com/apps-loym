# models/account_type_group_order.py
from odoo import fields, models

ACCOUNT_TYPE_ORDER = [
    "asset_receivable",
    "asset_cash",
    "asset_current",
    "asset_non_current",
    "asset_prepayments",
    "asset_fixed",
    "liability_payable",
    "liability_credit_card",
    "liability_current",
    "liability_non_current",
    "equity",
    "equity_unaffected",
    "income",
    "income_other",
    "expense",
    "expense_depreciation",
    "expense_direct_cost",
    "off_balance",
]


class AccountAccount(models.Model):
    _inherit = "account.account"

    account_type = fields.Selection(group_expand="_group_expand_account_type")

    @models.api.model
    def _group_expand_account_type(self, values, domain):
        # Keep only groups that exist in resultset, but enforce wanted order.
        values_set = set(values or [])
        return [v for v in ACCOUNT_TYPE_ORDER if v in values_set]


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    account_type = fields.Selection(group_expand="_group_expand_account_type")

    @models.api.model
    def _group_expand_account_type(self, values, domain):
        values_set = set(values or [])
        return [v for v in ACCOUNT_TYPE_ORDER if v in values_set]
