"""Thin Nets Easy API client isolated from Odoo models."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib import request as urlrequest


class NetsAPI:
    """Client used by Odoo payment transactions to call Nets Easy endpoints."""

    _BASE_URLS = {
        "test": "https://test.api.dibspayment.eu/v1",
        "production": "https://api.dibspayment.eu/v1",
    }

    def __init__(self, api_key: str | None, secret_key: str | None, environment: str = "test"):
        self.api_key = api_key or ""
        self.secret_key = secret_key or ""
        self.environment = environment if environment in self._BASE_URLS else "test"
        self.base_url = self._BASE_URLS[self.environment]

    def create_payment(self, payload: dict) -> dict:
        """Create a Nets payment and return payment_id + checkout_url."""
        endpoint = "/payments"
        response = self._request("POST", endpoint, payload)
        checkout_url = (
            response.get("checkout", {}).get("url")
            or response.get("hostedPaymentPageUrl")
            or response.get("checkout_url")
        )
        payment_id = response.get("paymentId") or response.get("id") or payload.get("reference")
        return {
            "payment_id": payment_id,
            "checkout_url": checkout_url,
            "raw": response,
        }

    def get_payment(self, payment_id: str) -> dict:
        """Retrieve payment details from Nets."""
        endpoint = f"/payments/{payment_id}"
        response = self._request("GET", endpoint)
        status = (
            response.get("payment", {}).get("summary", {}).get("chargedAmount") and "charged"
        ) or response.get("status") or response.get("payment", {}).get("status") or "pending"
        return {
            "id": payment_id,
            "status": status,
            "raw": response,
        }

    def refund_payment(self, payment_id: str, amount: float | None = None) -> dict:
        """Create a refund request in Nets."""
        endpoint = f"/payments/{payment_id}/refunds"
        payload = {}
        if amount is not None:
            payload["amount"] = amount
        response = self._request("POST", endpoint, payload)
        return {"id": response.get("id") or payment_id, "raw": response}

    def _request(self, method: str, endpoint: str, payload: dict | None = None) -> dict:
        """Execute a JSON HTTP request to Nets.

        This implementation is intentionally lightweight and can be replaced with a richer client
        when final Nets endpoint contracts are locked.
        """
        url = f"{self.base_url}{endpoint}"
        body = None if payload is None else json.dumps(payload).encode()

        # Nets Easy expects the secret key directly in the Authorization header.
        # The checkout key can be passed separately to support broader endpoint compatibility.
        headers = {
            "Authorization": self.secret_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Checkout-Key"] = self.api_key

        req = urlrequest.Request(
            url=url,
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urlrequest.urlopen(req, timeout=30) as response:
                response_payload = response.read().decode() or "{}"
        except HTTPError as err:
            error_payload = err.read().decode() if err.fp else ""
            if error_payload:
                raise RuntimeError(
                    f"Nets API HTTP {err.code} {err.reason}: {error_payload}"
                ) from err
            raise RuntimeError(f"Nets API HTTP {err.code} {err.reason}") from err
        except URLError as err:
            raise RuntimeError(f"Nets API connection error: {err.reason}") from err

        parsed = json.loads(response_payload)
        return parsed if isinstance(parsed, dict) else {}
