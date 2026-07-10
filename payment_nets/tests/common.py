"""Shared test setup for payment_nets."""

from odoo.addons.payment.tests.common import PaymentCommon


class NetsCommon(PaymentCommon):
    """Base helpers and provider setup for Nets tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls._prepare_provider(
            "nets",
            update_values={
                "nets_api_key": "test-api-key",
                "nets_secret_key": "test-secret-key",
                "nets_environment": "test",
            },
        )
        cls.currency = cls.currency_euro
        cls.notification_data = {
            "reference": cls.reference,
            "payment_id": "pay_test_123",
        }
