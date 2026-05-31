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
ACCOUNT_TYPE_INDEX = {value: idx for idx, value in enumerate(ACCOUNT_TYPE_ORDER)}


def _group_value_key(value):
    if isinstance(value, models.BaseModel):
        return tuple(value.ids)
    if isinstance(value, list):
        return tuple(value)
    return value


def _sort_read_group_rows_by_account_type(rows, groupby, lazy):
    """Pivot uses lazy=False, where group_expand ordering is not applied by ORM."""
    if lazy or not rows:
        return rows

    groupby_specs = [groupby] if isinstance(groupby, str) else list(groupby or [])
    if not groupby_specs:
        return rows

    account_type_pos = next(
        (
            idx
            for idx, spec in enumerate(groupby_specs)
            if spec.split(":")[0].split(".")[0] == "account_type"
        ),
        None,
    )
    if account_type_pos is None:
        return rows

    account_type_groupby = groupby_specs[account_type_pos]
    prefix_specs = groupby_specs[:account_type_pos]

    prefix_order = {}
    for row in rows:
        prefix = tuple(_group_value_key(row.get(spec)) for spec in prefix_specs)
        prefix_order.setdefault(prefix, len(prefix_order))

    sorted_items = sorted(
        enumerate(rows),
        key=lambda item: (
            prefix_order[
                tuple(_group_value_key(item[1].get(spec)) for spec in prefix_specs)
            ],
            ACCOUNT_TYPE_INDEX.get(item[1].get(account_type_groupby), len(ACCOUNT_TYPE_INDEX)),
            item[0],
        ),
    )
    return [row for _, row in sorted_items]



class AccountAccount(models.Model):
    _inherit = "account.account"

    account_type = fields.Selection(group_expand="_group_expand_account_type")

    @models.api.model
    def _group_expand_account_type(self, values, domain):
        # Keep only groups that exist in resultset, but enforce wanted order.
        values_set = set(values or [])
        return [v for v in ACCOUNT_TYPE_ORDER if v in values_set]

    @models.api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        rows = super().read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
        return _sort_read_group_rows_by_account_type(rows, groupby, lazy)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    account_type = fields.Selection(group_expand="_group_expand_account_type")

    @models.api.model
    def _group_expand_account_type(self, values, domain):
        values_set = set(values or [])
        return [v for v in ACCOUNT_TYPE_ORDER if v in values_set]

    @models.api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        rows = super().read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
        return _sort_read_group_rows_by_account_type(rows, groupby, lazy)
