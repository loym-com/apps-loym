
from odoo import _, api, models, fields, tools, Command
from odoo.exceptions import UserError

from base64 import b64decode
from requests.exceptions import HTTPError
from datetime import datetime, timezone, timedelta

import jwt as pyjwt
import requests
import uuid
import calendar

import logging

_logger = logging.getLogger(__name__)

API_BASE = "https://api.enablebanking.com"


class EnableBankingConfig(models.Model):
    _name = "enable.banking.config"
    _inherit = ["mail.thread"]
    _description = "Enable Banking Configuration"

    # company_id = fields.Many2one(related="bank_id.company_id", store=True)
    active = fields.Boolean(default=True)
    name = fields.Char(required=True, default="Enable Banking Configuration")
    journal_ids = fields.One2many('account.journal', 'enable_banking_config', string="Journals", required=True, domain="[('type', '=', 'bank'), ('bank_id', '=', bank_id)]")
    bank_id = fields.Many2one('res.bank', required=True)

    application_id = fields.Char(string="Application ID")
    rsa_key = fields.Binary()
    rsa_key_filename = fields.Char()
    auth_code = fields.Char()

    state_id = fields.Char()

    valid_until = fields.Datetime(string='Access Expires', readonly=True)
    account_id = fields.Char(string='Account_id', readonly=True)

    account_type = fields.Selection([('business', 'Business'), ('personal', 'Personal')], string='Account Type', default="business")
    connection_status = fields.Selection([
        ('not_connected', 'Not Connected'),
        ('connected', 'Connected'),
        ('expired', 'Expired'),
        ('error', 'Error'),
    ], string='Status', default="not_connected", compute="_compute_connection_status", store=True)

    redirect_url = fields.Char(string="Redirect URL", compute="_compute_redirect_url", default=lambda self: self._redirect_url())

    statement_type = fields.Selection(
        selection=[("days", "Daily Statements"), ("weeks", "Weekly Statements"), ("months", "Monthly Statements")],
        default="days",
        required=True
    )
    last_fetch = fields.Datetime(readonly=True)

    cron_id = fields.Many2one('ir.cron', readonly=True)
    cron_active = fields.Boolean(string="Cron Active", related='cron_id.active', readonly=False)
    cron_nextcall = fields.Datetime(related='cron_id.nextcall', readonly=False)

    @api.onchange('statement_type')
    def _onchange_statement_type(self):
        self.cron_id.interval_type = self.statement_type

    @api.model
    def _redirect_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/account/enable-banking/return'

    def _compute_redirect_url(self):
        for record in self:
            record.redirect_url = record._redirect_url()

    @api.depends('valid_until')
    def _compute_connection_status(self):
        for record in self:
            if record.valid_until and record.valid_until >= fields.Datetime.now():
                record.connection_status = 'connected'
            elif record.valid_until and record.valid_until < fields.Datetime.now():
                record.connection_status = 'expired'
            else:
                record.connection_status = 'not_connected'

    @api.model
    def _get_enablebanking_jwt(self):
        if not all([self.rsa_key, self.application_id]):
            raise UserError(_('Both Application ID and RSA Private Key are required!'))

        iat = int(datetime.now().timestamp())

        jwt_body = {
            "iss": "enablebanking.com",
            "aud": "api.enablebanking.com",
            "iat": iat,
            "exp": iat + 3600,
        }

        jwt = pyjwt.encode(
            jwt_body,
            b64decode(self.rsa_key),
            algorithm="RS256",
            headers={"kid": self.application_id},
        )
        return jwt

    def enablebanking_api_request(self, endpoint, method='GET', body=None, params=None):
        jwt = self._get_enablebanking_jwt()
        base_headers = {"Authorization": f"Bearer {jwt}"}

        url = f'{API_BASE}/{endpoint}'
        response = requests.request(method, url, json=body, headers=base_headers, params=params)
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise UserError(f'{e}\n\n{response.text}')

        _logger.debug(response.text)
        return response.json()

    def enablebanking_api_application(self):
        return self.enablebanking_api_request('application')

    def enablebanking_api_auth(self):
        aspsp_name = self.bank_id.name
        aspsp_country = self.bank_id.country.code

        self.state_id = str(uuid.uuid4())
        valid_until = datetime.now(timezone.utc) + timedelta(days=90)

        lang = tools.get_lang(self.env).iso_code

        body = {
            "access": {
                "valid_until": valid_until.isoformat()
            },
            "aspsp": {"name": aspsp_name, "country": aspsp_country},
            "state": self.state_id,
            "redirect_url": self.redirect_url,
            'language': lang,
            "psu_type": self.account_type,
        }

        return self.enablebanking_api_request('auth', 'POST', body)

    def enablebanking_start_session(self, auth_code=False):
        auth_code = auth_code or self.auth_code
        body = {'code': auth_code}
        return self.enablebanking_api_request('sessions', 'POST', body)

    def action_connect(self):
        self._validate_settings()

        r = self.enablebanking_api_auth()
        auth_url = r["url"]

        return {
            "type": "ir.actions.act_url",
            "url": auth_url
        }

    def enablebanking_get_transactions(self, date_from, date_to, account_id):
        data_list = []
        params = {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'transaction_status': 'BOOK',
        }

        continuation_key = None
        while True:
            if continuation_key:
                params['continuation_key'] = continuation_key
            data = self.enablebanking_api_request(f'accounts/{account_id}/transactions', params=params)
            data_list += data.get('transactions')

            continuation_key = data.get("continuation_key")

            if not continuation_key:
                break

        return data_list

    def _prepare_statement_vals(self, raw_data, journal, date_from, date_to):
        line_ids = self._prepare_statement_line_vals(raw_data, journal, date_from, date_to)

        if not line_ids:
            return []

        statement_vals = [
            {
                'reference': 'Enable Banking Transactions',
                'line_ids': line_ids,
            }
        ]

        return statement_vals

    def _prepare_statement_line_vals(self, raw_data, journal, date_from, date_to):
        imported_ids = self.env['account.bank.statement.line'].search([]).mapped('enable_banking_id')

        lines = []
        for line in raw_data:
            if not line.get('status') == 'BOOK':
                continue

            enable_banking_id = line.get('entry_reference')
            if enable_banking_id in imported_ids:
                continue

            currency = line.get('transaction_amount', {}).get('currency')
            accepted_currency = journal.currency_id or journal.company_id.currency_id
            if not currency == accepted_currency.name:
                continue

            date = datetime.strptime(line.get('booking_date'), '%Y-%m-%d').date()

            if not (date_from <= date <= date_to):
                continue

            amount = float(line.get('transaction_amount', {}).get('amount'))

            indicator = line.get('credit_debit_indicator')
            partner_type = 'creditor' if indicator == 'DBIT' else 'debtor'

            partner_info = line.get(partner_type, {})
            partner_name = partner_info and partner_info.get('name')

            partner_account_info = line.get(f'{partner_type}_account', {})
            account_number = partner_account_info and partner_account_info.get('iban')

            payment_ref = '; '.join(line.get('remittance_information', []))

            lines.append(Command.create(
                {
                    "date": date,
                    "enable_banking_id": enable_banking_id,
                    "amount": amount if partner_type == 'debtor' else -amount,
                    "payment_ref": payment_ref,
                    "partner_name": partner_name,
                    "account_number": account_number,  # if no partner_id
                    # 'partner_id': self._get_partner(), # todo
                    "journal_id": journal.id,
                })
            )

        return lines

    def _fetch_transactions(self, date_from, date_to):
        for journal in self.journal_ids.filtered(lambda x: x.enable_banking_account_id):
            for date_from, date_to in self._generate_date_pairs(date_from, date_to):
                transaction_data = self.enablebanking_get_transactions(date_from, date_to, journal.enable_banking_account_id)
                statement_vals = self._prepare_statement_vals(transaction_data, journal, date_from, date_to)

                statement = self.env['account.bank.statement'].create(statement_vals)
                statement.balance_end_real = statement.balance_end

        self.last_fetch = fields.Datetime.now()

    def _validate_settings(self):
        aspsp_country = self.bank_id.country.code
        if not aspsp_country:
            raise UserError(_('Please select a valid country on bank %s', self.bank_id.name))

    def _generate_date_pairs(self, date_from, date_to):
        date_pairs = []

        while date_from <= date_to:
            current_date_to = date_from
            if self.statement_type == 'weeks':
                while current_date_to.weekday() != 6:
                    current_date_to += timedelta(days=1)
            elif self.statement_type == 'months':
                first_day_of_month, last_day_of_month = calendar.monthrange(current_date_to.year, current_date_to.month)
                current_date_to = current_date_to.replace(day=last_day_of_month)

            date_pairs.append((date_from, min(current_date_to, date_to)))
            date_from = current_date_to + timedelta(days=1)

        return date_pairs

    @api.model
    def scheduled_fetch(self):
        configs = self.search([("last_fetch", "<=", fields.Datetime.now()), ('last_fetch', '!=', False)])
        for config in configs:
            config._fetch_transactions(config.last_fetch.date(), fields.Date.today())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            cron = self.env['ir.cron'].sudo().create({
                'user_id': self.env.ref('base.user_root').id,
                'active': False,
                'interval_type': 'days',
                'interval_number': 1,
                'name': _("Pull Enable Banking Transactions"),
                'model_id': self.env['ir.model']._get_id(self._name),
                'state': 'code',
                'code': "model.scheduled_fetch()",
            })
            vals['cron_id'] = cron.id

        records = super().create(vals_list)
        records.journal_ids.bank_statements_source = 'enable_banking'
        return records
