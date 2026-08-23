"""Recurring charge helper methods for Nets payment tokens."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_nets_recurring.services.nets_recurring_api import NetsRecurringAPI


class PaymentToken(models.Model):
    """Implement token-based recurring charges for Nets agreements."""

    _inherit = "payment.token"

    def charge(self, amount, currency):
        """Charge an existing Nets recurring agreement.

        :param float amount: Amount in major units.
        :param recordset currency: `res.currency` record.
        :return: Nets API payment result payload.
        :rtype: dict
        """
        self.ensure_one()
        if self.provider_code != "nets":
            raise ValidationError(_("Only Nets tokens can be charged by this method."))
        if not self.provider_ref:
            raise ValidationError(_("Nets token is missing provider reference."))

        amount_minor = int(
            (Decimal(str(amount)) * Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        api = NetsRecurringAPI(
            api_key=self.provider_id.nets_api_key,
            secret_key=self.provider_id.nets_secret_key,
            environment=self.provider_id.nets_environment,
        )
        return api.charge_recurring_agreement(
            agreement_id=self.provider_ref,
            payload={
                "order": {
                    "amount": amount_minor,
                    "currency": currency.name,
                }
            },
        )
