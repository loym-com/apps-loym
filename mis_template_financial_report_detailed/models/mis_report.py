# Copyright 2022 APPSTOGROW AS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import OrderedDict
import re
from odoo import api, fields, models


class MisReport(models.Model):
    _inherit = "mis.report"

    def generate_reports(self):
        sequence = 0

        """ PROFIT & LOSS (mis.report) """

        report_pl = self.create({
            'name': 'Profit & Loss, detailed',
            'style_id': self.env.ref('mis_template_financial_report.style_default').id,
        })

        income_kpi, sequence = self._create_account_type_kpis('income', report_pl, sequence)
        expense_kpi, sequence = self._create_account_type_kpis('expense', report_pl, sequence)
        pl_kpi, sequence = self._create_kpi_with_sequence({
            'name': 'pl',
            'description': 'PROFIT & LOSS',
            'expression': '{} + {}'.format(income_kpi.name, expense_kpi.name),
            'auto_expand_accounts': False,
            'style_id': self.env.ref('mis_template_financial_report.style_header').id,
            'report_id': report_pl.id,
        }, sequence)

        """ BALANCE SHEET (mis.report) """

        report_bs = self.create({
            'name': 'Balance Sheet, detailed',
            'style_id': self.env.ref('mis_template_financial_report.style_default').id,
        })

        asset_kpi, sequence = self._create_account_type_kpis('asset', report_bs, sequence)

        equity_kpi, sequence = self._create_account_type_kpis('equity', report_bs, sequence)
        liability_kpi, sequence = self._create_account_type_kpis('liability', report_bs, sequence)
        unregistered_pl_kpi, sequence = self._create_kpi_with_sequence({
            'name': 'unregistered_pl',
            'description': 'Unregistered Profit & Loss',
            'expression': '-(total_asset + total_equity + total_liability)',
            'auto_expand_accounts': False,
            'style_id': self.env.ref('mis_template_financial_report.style_header').id,
            'report_id': report_bs.id,
        }, sequence)
        equity_liability_kpi, sequence = self._create_kpi_with_sequence({
            'name': 'bal_pl',
            'description': 'EQUITY & LIABILITY',
            'expression': '{} + {} + {}'.format(equity_kpi.name, liability_kpi.name, 'unregistered_pl'),
            'auto_expand_accounts': False,
            'style_id': self.env.ref('mis_template_financial_report.style_header').id,
            'report_id': report_bs.id,
        }, sequence)

        """ PROFIT & LOSS (mis.report.instance) """

        instance_pl = self._create_instance({
            'name': 'Profit & Loss, last 2 years',
            'report_id': report_pl.id,
        })
        pl_period_last_year = self._create_instance_period({
            'name': 'Last Year',
            'offset': -1,
            'report_instance_id': instance_pl.id,
        })
        pl_period_2nd_last_year = self._create_instance_period({
            'name': '2nd Last Year',
            'offset': -2,
            'report_instance_id': instance_pl.id,
        })

        """ BALANCE SHEET (mis.report.instance) """

        instance_bs = self._create_instance({
            'name': 'Balance Sheet, last 2 years',
            'report_id': report_bs.id,
        })
        bs_period_last_year = self._create_instance_period({
            'name': 'Last Year',
            'offset': -1,
            'report_instance_id': instance_bs.id,
        })
        bs_period_2nd_last_year = self._create_instance_period({
            'name': '2nd Last Year',
            'offset': -2,
            'report_instance_id': instance_bs.id,
        })

    def _create_account_type_kpis(self, internal_group, mis_report, sequence):
        kpis = []
        account_types = [
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ]
        # Create KPIs
        for account_type in account_types:
            if not account_type[0].startswith(internal_group):
                continue
            kpi, sequence = self._create_account_type_kpi(account_type, mis_report, sequence)
            kpis.append(kpi)
        # Create KPI with the total
        kpi_names = [kpi.name for kpi in kpis]
        expression = ' + '.join(kpi_names)
        total_kpi, sequence = self._create_kpi_with_sequence({
            'name': f"total_{internal_group}",
            'description': internal_group.upper(),
            'expression': expression,
            'auto_expand_accounts': False,
            'style_id': self.env.ref('mis_template_financial_report.style_header').id,
            'report_id': mis_report.id,
        }, sequence)
        return total_kpi, sequence

    def _create_account_type_kpi(self, account_type, mis_report, sequence):
        expression = 'bale'
        account_type = {"code": account_type[0], "name": account_type[1]}
        if account_type["code"].startswith(('income', 'expense')):
            expression = '-balp'
        account_type_kpi_values = {
            'name': account_type["code"],
            'description': account_type["name"],
            'expression': expression + "[('account_type', '=', '{code}')][]".format(code=account_type["code"]),
            'auto_expand_accounts': True,
            'auto_expand_accounts_style_id': self.env.ref('mis_template_financial_report.style_details').id,
            'style_id': self.env.ref('mis_template_financial_report.style_header').id,
            'report_id': mis_report.id,
        }
        kpi, sequence = self._create_kpi_with_sequence(account_type_kpi_values, sequence)
        return kpi, sequence

    def _create_kpi_with_sequence(self, values, sequence):
        sequence += 1
        kpi_values = {
            'type': 'num',
            'compare_method': 'pct',
            'accumulation_method': 'sum',
            'sequence': sequence,
        }
        kpi_values.update(values)
        kpi = self.env['mis.report.kpi'].create(kpi_values)
        return kpi, sequence

    def _create_instance(self, values):
        instance_values = {
            'comparison_mode': True,
            'no_auto_expand_accounts': False,
            'display_columns_description': True,
            'target_move': 'all',
        }
        instance_values.update(values)
        return self.env['mis.report.instance'].create(instance_values)

    def _create_instance_period(self, values):
        period_values = {
            'source': 'actuals',
            'mode': 'relative',
            'type': 'y',
            'duration': 1,
        }
        period_values.update(values)
        return self.env['mis.report.instance.period'].create(period_values)
