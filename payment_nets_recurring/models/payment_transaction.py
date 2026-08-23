"""Recurring agreement and tokenization flow for Nets transactions."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from odoo import _, fields, models

from odoo.addons.payment_nets_recurring.services.nets_recurring_api import NetsRecurringAPI


class PaymentTransaction(models.Model):
    """Create Nets recurring agreements and charge them through tokens."""

    _inherit = "payment.transaction"

    nets_recurring_agreement_id = fields.Char(
        string="Nets Recurring Agreement ID",
        copy=False,
    )

    def _send_payment_request(self):
        """Charge Nets recurring agreements for token-based transactions."""
        if self.provider_code != "nets":
            return super()._send_payment_request()

        self.ensure_one()
        if not self.token_id:
            return super()._send_payment_request()

        recurring_api = self._nets_get_recurring_api()
        amount_minor = int(
            (Decimal(str(self.amount)) * Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        payload = {
            "order": {
                "amount": amount_minor,
                "currency": self.currency_id.name,
                "reference": self.reference,
            }
        }
        try:
            payment_data = recurring_api.charge_recurring_agreement(self.token_id.provider_ref, payload)
            payment_data.setdefault("reference", self.reference)
            self._process("nets", payment_data)
        except Exception as err:  # ValidationError is handled by payment.transaction state methods.
            self._set_error(str(err))

    def _apply_updates(self, payment_data):
        """After Nets update, create recurring agreement when tokenization is requested."""
        super()._apply_updates(payment_data)
        if self.provider_code != "nets":
            return
        if not self.tokenize or self.token_id:
            return
        if self.state not in {"authorized", "done"}:
            return

        agreement_id = (
            payment_data.get("recurring_agreement_id")
            or payment_data.get("agreement_id")
            or payment_data.get("subscription_id")
        )
        if not agreement_id:
            recurring_api = self._nets_get_recurring_api()
            agreement_payload = {
                "paymentId": self.provider_reference,
                "reference": self.reference,
                "customer": {
                    "email": self.partner_email,
                },
            }
            agreement_data = recurring_api.create_recurring_agreement(agreement_payload)
            agreement_id = agreement_data.get("agreement_id")

        if agreement_id:
            self.nets_recurring_agreement_id = agreement_id

    def _extract_token_values(self, payment_data):
        """Create payment.token values from Nets recurring agreement metadata."""
        if self.provider_code != "nets":
            return super()._extract_token_values(payment_data)

        agreement_id = (
            payment_data.get("recurring_agreement_id")
            or payment_data.get("agreement_id")
            or payment_data.get("subscription_id")
            or self.nets_recurring_agreement_id
        )
        if not agreement_id:
            return {}

        suffix = agreement_id[-6:] if len(agreement_id) >= 6 else agreement_id
        return {
            "provider_ref": agreement_id,
            "payment_details": f"Nets agreement {suffix}",
        }

    def _nets_get_recurring_api(self):
        """Return an API client for Nets recurring endpoints."""
        self.ensure_one()
        provider = self.provider_id
        return NetsRecurringAPI(
            api_key=provider.nets_api_key,
            secret_key=provider.nets_secret_key,
            environment=provider.nets_environment,
        )
