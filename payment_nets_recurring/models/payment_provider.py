"""Recurring-specific extensions for Nets payment providers."""

from odoo import fields, models


class PaymentProvider(models.Model):
    """Enable tokenization support and recurring metadata for Nets."""

    _inherit = "payment.provider"

    nets_support_recurring = fields.Boolean(
        string="Supports Nets Recurring",
        default=True,
        readonly=True,
    )

    def _compute_feature_support_fields(self):
        """Mark Nets providers as tokenization-capable for recurring flows."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "nets").update({
            "support_tokenization": True,
        })
