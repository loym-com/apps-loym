"""Tests for Nets payment provider integration."""

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_nets.controllers.main import NetsController
from odoo.addons.payment_nets.tests.common import NetsCommon


@tagged("post_install", "-at_install")
class TestPaymentNets(NetsCommon, PaymentHttpCommon):
    """Validate provider setup, transaction flow, and webhook processing."""

    def test_provider_is_configurable(self):
        """Provider should be created and configured with Nets credentials."""
        self.assertEqual(self.provider.code, "nets")
        self.assertEqual(self.provider.nets_environment, "test")
        self.assertTrue(self.provider.nets_api_key)
        self.assertTrue(self.provider.nets_secret_key)

    def test_transaction_rendering_creates_payment_request(self):
        """Creating rendering values should call Nets API and set provider reference."""
        tx = self._create_transaction(flow="redirect")
        with patch(
            "odoo.addons.payment_nets.services.nets_api.NetsAPI.create_payment",
            return_value={"payment_id": "pay_test_123", "checkout_url": "https://checkout.nets.test"},
        ):
            values = tx._get_specific_rendering_values({"reference": tx.reference})

        self.assertEqual(tx.provider_reference, "pay_test_123")
        self.assertEqual(values.get("api_url"), "https://checkout.nets.test")

    @mute_logger("odoo.addons.payment_nets.controllers.main")
    def test_webhook_marks_transaction_done(self):
        """Webhook callback should resolve and confirm transaction with mocked Nets status."""
        tx = self._create_transaction(flow="redirect")
        tx.provider_reference = "pay_test_123"
        webhook_url = self._build_url(NetsController._webhook_url)

        with patch(
            "odoo.addons.payment_nets.services.nets_api.NetsAPI.get_payment",
            return_value={"id": "pay_test_123", "status": "paid"},
        ):
            self._make_http_post_request(webhook_url, data=self.notification_data)

        self.assertEqual(tx.state, "done")