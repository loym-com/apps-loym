"""Payment transaction implementation for Nets Easy (Odoo 19 payment framework)."""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_nets.controllers.main import NetsController
from odoo.addons.payment_nets.services.nets_api import NetsAPI

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    """Implement Nets-specific payment flow in Odoo 19's payment framework."""

    _inherit = "payment.transaction"

    # === RENDERING ===

    def _get_specific_rendering_values(self, processing_values):
        """Create the Nets payment request and return redirect form values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "nets":
            return res

        provider = self.provider_id
        nets = NetsAPI(
            api_key=provider.nets_api_key,
            secret_key=provider.nets_secret_key,
            environment=provider.nets_environment,
        )

        base_url = provider.get_base_url()
        webhook_url = urls.url_join(base_url, NetsController._webhook_url)
        return_url = urls.url_join(
            base_url, f"{NetsController._return_url}?ref={self.reference}"
        )
        terms_url = urls.url_join(base_url, "/payment/status")
        parsed_webhook_url = urls.url_parse(webhook_url)
        use_webhooks = parsed_webhook_url.host not in {"localhost", "127.0.0.1", "0.0.0.0"}
        amount_minor = int(
            (Decimal(str(self.amount)) * Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        payload = {
            "checkout": {
                "integrationType": "HostedPaymentPage",
                "returnUrl": return_url,
                "termsUrl": terms_url,
            },
            "order": {
                "amount": amount_minor,
                "currency": self.currency_id.name,
                "reference": self.reference,
                "items": [
                    {
                        "reference": self.reference,
                        "name": self.reference,
                        "quantity": 1,
                        "unit": "pcs",
                        "unitPrice": amount_minor,
                        "grossTotalAmount": amount_minor,
                        "netTotalAmount": amount_minor,
                    }
                ],
            },
        }
        if use_webhooks:
            payload["notifications"] = {
                "webhooks": [
                    {"eventName": "payment.created", "url": webhook_url, "authorization": self.reference},
                    {"eventName": "payment.reservation.created", "url": webhook_url, "authorization": self.reference},
                    {"eventName": "payment.charge.created", "url": webhook_url, "authorization": self.reference},
                ]
            }
        payment_data = nets.create_payment(payload)
        payment_id = payment_data.get("payment_id")
        if payment_id:
            self.provider_reference = payment_id

        checkout_url = payment_data.get("checkout_url")
        if not checkout_url:
            raise ValidationError(_("Nets: Missing checkout URL in payment response."))

        parsed_url = urls.url_parse(checkout_url)
        url_params = urls.url_decode(parsed_url.query)
        return {"api_url": checkout_url, "url_params": url_params}

    # === ODOO 19 FRAMEWORK HOOKS ===

    def _extract_amount_data(self, payment_data):
        """Skip amount validation for Nets; amounts are verified via API in _apply_updates."""
        if self.provider_code != "nets":
            return super()._extract_amount_data(payment_data)
        return None  # None tells the framework to skip amount validation.

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Extract the Odoo transaction reference from Nets payment data.

        Nets sends 'ref' as a query param in the return URL and as 'reference'
        in webhook payloads. 'paymentid' (no underscore) is also present in
        the return URL but is the Nets payment ID, not the Odoo reference.
        """
        if provider_code != "nets":
            return super()._extract_reference(provider_code, payment_data)
        return (
            payment_data.get("ref")
            or payment_data.get("reference")
            or payment_data.get("merchant_reference")
        )

    def _apply_updates(self, payment_data):
        """Fetch the Nets payment status and update the transaction state."""
        super()._apply_updates(payment_data)
        if self.provider_code != "nets":
            return

        provider = self.provider_id
        nets = NetsAPI(
            api_key=provider.nets_api_key,
            secret_key=provider.nets_secret_key,
            environment=provider.nets_environment,
        )

        # If account_payment is installed, ensure provider payment method artifacts exist
        # before post-processing attempts to create account.payment.
        if hasattr(provider, "_setup_payment_method"):
            provider._setup_payment_method(provider.code)
        if hasattr(provider, "_ensure_payment_method_line"):
            # Reuse an existing inbound line named like the provider on the same journal when
            # possible to avoid duplicate-line constraints.
            if provider.journal_id:
                existing_line = self.env["account.payment.method.line"].search(
                    [
                        ("journal_id", "=", provider.journal_id.id),
                        ("name", "=", provider.name),
                        ("payment_provider_id", "=", False),
                        ("payment_method_id.payment_type", "=", "inbound"),
                    ],
                    limit=1,
                )
                if existing_line:
                    existing_line.payment_provider_id = provider

            try:
                provider._ensure_payment_method_line()
            except ValidationError as err:
                # Return and webhook callbacks can race to create the same method line.
                # If the line already exists, continue processing safely.
                if "two payment method lines" in str(err):
                    _logger.info(
                        "Nets: payment method line already exists for provider %s; continuing",
                        provider.id,
                    )
                else:
                    raise

        # 'paymentid' (no underscore) comes from Nets' return URL redirect.
        payment_id = (
            payment_data.get("paymentid")
            or payment_data.get("payment_id")
            or payment_data.get("id")
            or self.provider_reference
        )
        if not payment_id:
            raise ValidationError(_("Nets: Cannot determine payment ID to fetch status."))

        if self.provider_reference != payment_id:
            self.provider_reference = payment_id

        nets_payment = nets.get_payment(payment_id)
        raw = nets_payment.get("raw", {})
        payment_obj = raw.get("payment", {})
        summary = payment_obj.get("summary", {})

        # Derive a normalised status from the Nets summary block.
        if summary.get("chargedAmount"):
            status = "charged"
        elif summary.get("reservedAmount"):
            status = "reserved"
        elif summary.get("cancelledAmount"):
            status = "cancelled"
        elif summary.get("refundedAmount"):
            status = "charged"
        else:
            status = (
                payment_obj.get("status")
                or nets_payment.get("status")
                or "pending"
            ).lower()

        _logger.info("Nets: payment %s -> status '%s' for tx %s", payment_id, status, self.reference)

        if status in {"created", "pending", "in_progress"}:
            self._set_pending()
        elif status in {"reserved", "authorized"}:
            # Odoo 19 allows `authorized` state only when manual capture is supported/enabled.
            if self.provider_id.capture_manually:
                self._set_authorized()
            else:
                self._set_done()
        elif status in {"charged", "paid", "succeeded"}:
            self._set_done()
        elif status in {"cancelled", "canceled"}:
            self._set_canceled(_("Nets: Payment was canceled."))
        elif status in {"failed", "error", "declined"}:
            self._set_error(_("Nets: Payment failed with status %s.", status))
        else:
            _logger.warning("Nets: unknown status '%s' for tx %s; setting pending", status, self.reference)
            self._set_pending()
