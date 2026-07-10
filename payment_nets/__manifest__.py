# Copyright 2026 Loym
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

{
    "name": "payment_nets",
    "summary": "Nets Easy payment provider integration",
    "version": "19.0.1.0.0",
    "author": "Loym, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "website": "https://github.com/OCA",
    "category": "Accounting/Payment Providers",
    "depends": [
        "payment",
    ],
    "data": [
        "data/payment_method_data.xml",
        "views/payment_nets_templates.xml",
        "data/payment_provider_data.xml",
        "security/ir.model.access.csv",
        "views/payment_provider_views.xml",
    ],
    "installable": True,
    "application": False,
}
