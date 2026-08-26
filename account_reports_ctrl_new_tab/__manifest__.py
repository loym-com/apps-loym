{
    'name': 'Account Reports Ctrl New Tab',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Open account report drilldowns in a new tab with Ctrl-click',
    'depends': [
        'account_reports',
    ],
    'assets': {
        'web.assets_backend': [
            'account_reports_ctrl_new_tab/static/src/account_reports_ctrl_new_tab.js',
        ],
    },
    'license': 'LGPL-3',
    'author': 'Loym',
}
