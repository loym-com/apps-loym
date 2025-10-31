# Copyright 2025 Loym

{
    "name": "Base App",
    "summary": "",
    "author": "Loym",
    "auto_install": True,
    "data": [
        "data/tmp.xml",
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/app_module_version_views.xml",
        "views/app_pricelist_views.xml",
        "views/app_usage_line_views.xml",
        "views/app_usage_month_views.xml",
        "views/ir_module_module_views.xml",
        # "views/menus.xml",
    ],
    "depends": [
        "analytic",
    ],
    "license": "Other proprietary",
    "post_init_hook": "post_init_hook",
    "version": "18.0.1.0.1",
    "website": "https://www.loym.com",
}
