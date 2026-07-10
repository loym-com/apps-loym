"""Payment transaction implementation for Nets Easy."""

from __future__ import annotations

import logging

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_nets.controllers.main import NetsController
from odoo.addons.payment_nets.services.nets_api import NetsAPI

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    """Implement Nets-specific payment flow in Odoo's payment framework."""

    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Create the payment request and return redirect values for checkout."""
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
        return_url = urls.url_join(base_url, "/payment/status")
        payload = {
            "reference": self.reference,
            "amount": self.amount,
            "currency": self.currency_id.name,
            "return_url": return_url,
            "webhook_url": webhook_url,
            "partner_email": self.partner_email,
        }
        payment_data = nets.create_payment(payload)

        self.provider_reference = payment_data.get("payment_id")
        checkout_url = payment_data.get("checkout_url")
        if not checkout_url:
            raise ValidationError(_("Nets: Missing checkout URL in payment response."))

        parsed_url = urls.url_parse(checkout_url)
        url_params = urls.url_decode(parsed_url.query)
        return {"api_url": checkout_url, "url_params": url_params}

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Resolve a Nets transaction from webhook notification data."""
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "nets" or len(tx) == 1:
            return tx

        reference = notification_data.get("reference") or notification_data.get("merchant_reference")
        provider_reference = notification_data.get("payment_id") or notification_data.get("id")
        search_domain = [("provider_code", "=", "nets")]
        if provider_reference:
            search_domain = [*search_domain, ("provider_reference", "=", provider_reference)]
        elif reference:
            search_domain = [*search_domain, ("reference", "=", reference)]
        else:
            raise ValidationError(_("Nets: Notification data is missing transaction identifiers."))

        tx = self.search(search_domain, limit=1)
        if not tx:
            raise ValidationError(_("Nets: No transaction found for notification data %s.", notification_data))
        return tx

    def _process_notification_data(self, notification_data):
        """Fetch payment status from Nets and update transaction state."""
        super()._process_notification_data(notification_data)
        if self.provider_code != "nets":
            return

        provider = self.provider_id
        nets = NetsAPI(
            api_key=provider.nets_api_key,
            secret_key=provider.nets_secret_key,
            environment=provider.nets_environment,
        )

        payment_id = self.provider_reference or notification_data.get("payment_id") or notification_data.get("id")
        if not payment_id:
            raise ValidationError(_("Nets: Missing provider reference for status retrieval."))

        payment_data = nets.get_payment(payment_id)
        self.provider_reference = payment_data.get("id", payment_id)

        payment_status = (payment_data.get("status") or "").lower()
        if payment_status in {"created", "pending", "in_progress"}:
            self._set_pending()
        elif payment_status in {"authorized", "reserved"}:
            self._set_authorized()
        elif payment_status in {"charged", "paid", "succeeded"}:
            self._set_done()
        elif payment_status in {"cancelled", "canceled"}:
            self._set_canceled(_("Nets: Payment was canceled."))
        elif payment_status in {"failed", "error", "declined"}:
            self._set_error(_("Nets: Payment failed with status %s.", payment_status))
        else:
            _logger.warning("Nets: unknown payment status '%s' for tx %s", payment_status, self.reference)
            self._set_error(_("Nets: Unknown payment status %s.", payment_status))
