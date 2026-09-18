# -*- coding: utf-8 -*-

from odoo.http import request, Controller, route
from odoo import _
import logging
from dateutil.parser import parse
_logger = logging.getLogger(__name__)


class EnableBankingController(Controller):

    @route(['/account/enable-banking/return'], type='http', auth='user', methods=['GET'])
    def enable_banking_callback(self, **post):
        auth_code = post.get('code')
        state = post.get('state')

        config = request.env['enable.banking.config'].search([('state_id', '=', state)], limit=1)
        config.write({'auth_code': auth_code})

        session_data = config.enablebanking_start_session()

        valid_until = session_data.get('access', {}).get('valid_until')
        valid_until = parse(valid_until)
        config.write({'valid_until': valid_until.replace(tzinfo=None)})

        config.cron_id.active = True

        for journal in config.journal_ids:
            iban = journal.bank_account_id.sanitized_acc_number
            for account in session_data.get('accounts', {}):
                if account.get('account_id', {}).get('iban') == iban:
                    journal.enable_banking_account_id = account.get('uid')

        accounts_not_found = config.journal_ids.filtered(lambda j: not j.enable_banking_account_id)
        if accounts_not_found:
            odoobot_id = request.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
            ibans_not_found = accounts_not_found.bank_account_id.mapped('sanitized_acc_number')
            config.message_post(body=_('Account(s) %s not found with the service provider', ', '.join(ibans_not_found)), author_id=odoobot_id)

        action_id = request.env.ref('account_statements_enable_banking.enable_banking_config_action')
        menu_id = request.env.ref('account_statements_enable_banking.enable_banking_config_menu')

        url = f'/web#id={config.id}&menu_id={menu_id.id}&action={action_id.id}&model=enable.banking.config&view_type=form'

        return request.redirect(url)

