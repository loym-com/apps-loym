"""Tests for recurring token flows in payment_nets_recurring."""

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment_nets_recurring.tests.common import NetsRecurringCommon


@tagged("post_install", "-at_install")
class TestPaymentNetsRecurring(NetsRecurringCommon):
    """Validate recurring agreement and tokenized charge flows."""

    def test_token_creation_from_recurring_agreement(self):
        tx = self._create_transaction(
            flow="redirect",
            payment_method_id=self.payment_method_id.id,
            tokenize=True,
        )
        payment_data = {"ref": tx.reference, "paymentid": "pay_123"}

        with patch(
            "odoo.addons.payment_nets.services.nets_api.NetsAPI.get_payment",
            return_value={"raw": {"payment": {"summary": {"chargedAmount": 100}}}},
        ), patch(
            "odoo.addons.payment_nets_recurring.services.nets_recurring_api."
            "NetsRecurringAPI.create_recurring_agreement",
            return_value={"agreement_id": "agr_123"},
        ):
            tx._process("nets", payment_data)

        self.assertEqual(tx.state, "done")
        self.assertTrue(tx.token_id)
        self.assertEqual(tx.token_id.provider_ref, "agr_123")

    def test_recurring_charge_success(self):
        token = self._create_token(
            provider_id=self.provider.id,
            payment_method_id=self.payment_method_id.id,
            provider_ref="agr_456",
        )
        tx = self._create_transaction(
            flow="token",
            payment_method_id=self.payment_method_id.id,
            token_id=token.id,
            provider_id=self.provider.id,
        )

        with patch(
            "odoo.addons.payment_nets_recurring.services.nets_recurring_api."
            "NetsRecurringAPI.charge_recurring_agreement",
            return_value={"reference": tx.reference, "paymentid": "pay_456"},
        ), patch(
            "odoo.addons.payment_nets.services.nets_api.NetsAPI.get_payment",
            return_value={"raw": {"payment": {"summary": {"chargedAmount": 100}}}},
        ):
            tx._send_payment_request()

        self.assertEqual(tx.state, "done")

    def test_recurring_charge_failure(self):
        token = self._create_token(
            provider_id=self.provider.id,
            payment_method_id=self.payment_method_id.id,
            provider_ref="agr_789",
        )
        tx = self._create_transaction(
            flow="token",
            payment_method_id=self.payment_method_id.id,
            token_id=token.id,
            provider_id=self.provider.id,
        )

        with patch(
            "odoo.addons.payment_nets_recurring.services.nets_recurring_api."
            "NetsRecurringAPI.charge_recurring_agreement",
            side_effect=RuntimeError("charge failed"),
        ):
            tx._send_payment_request()

        self.assertEqual(tx.state, "error")
