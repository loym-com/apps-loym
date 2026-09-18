# -*- coding: utf-8 -*-
{
    'name': 'Bank Sync: Enable Banking',
    "summary": "Online bank statements for Enable Banking. Supports over 2500 banks in 28 countries in Europe. Online bank synchronization. Bank transactions sync.",
    'category': 'Accounting',
    'author': 'Winotto',
    'website': 'https://winotto.com',
    'version': '19.0.1.1',
    'depends': [
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/enable_banking_fetch_wizard_views.xml',
        'views/account_journal.xml',
        'views/enable_banking_config_views.xml',
        'views/account_bank_statement_views.xml',
        'views/account_bank_statement_line_views.xml',
        'views/account_journal_dashboard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['pyjwt']
    },
    'price': 99.00,
    'images': ['static/description/main_screenshot.png'],
}

