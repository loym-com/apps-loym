"""Shared test setup for payment_nets_recurring."""

from odoo.addons.payment.tests.common import PaymentCommon


class NetsRecurringCommon(PaymentCommon):
    """Prepare Nets provider and baseline values for recurring tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls._prepare_provider(
            "nets",
            update_values={
                "nets_api_key": "test-api-key",
                "nets_secret_key": "test-secret-key",
                "nets_environment": "test",
                "allow_tokenization": True,
            },
        )
        cls.payment_method_id = cls.env.ref(
            "payment_nets.payment_method_nets", raise_if_not_found=False
        ) or cls.env.ref("payment.payment_method_card")
        cls.currency = cls.currency_euro
