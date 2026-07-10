"""Payment provider extension for Nets Easy."""

from odoo import fields, models


class PaymentProvider(models.Model):
    """Add Nets as a provider in the Odoo payment framework."""

    _inherit = "payment.provider"

    code = fields.Selection(selection_add=[("nets", "Nets")], ondelete={"nets": "set default"})
    nets_api_key = fields.Char(string="Nets API Key", groups="base.group_system")
    nets_secret_key = fields.Char(string="Nets Secret Key", groups="base.group_system")
    nets_environment = fields.Selection(
        selection=[("test", "Test"), ("production", "Production")],
        string="Nets Environment",
        default="test",
        required_if_provider="nets",
    )

    def _get_default_payment_method_codes(self):
        """Return payment methods enabled by default for Nets providers."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != "nets":
            return default_codes
        return ["card"]
