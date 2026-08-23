"""Nets recurring API client isolated from Odoo models."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib import request as urlrequest


class NetsRecurringAPI:
    """Client wrapper for Nets recurring agreement endpoints."""

    _BASE_URLS = {
        "test": "https://test.api.dibspayment.eu/v1",
        "production": "https://api.dibspayment.eu/v1",
    }

    def __init__(self, api_key: str | None, secret_key: str | None, environment: str = "test"):
        self.api_key = api_key or ""
        self.secret_key = secret_key or ""
        self.environment = environment if environment in self._BASE_URLS else "test"
        self.base_url = self._BASE_URLS[self.environment]

    def create_recurring_agreement(self, payload: dict) -> dict:
        """Create recurring agreement and return agreement id."""
        # Endpoint is placeholder-compatible and can be replaced with final Nets contract.
        response = self._request("POST", "/recurring/agreements", payload)
        agreement_id = (
            response.get("agreementId")
            or response.get("id")
            or response.get("agreement_id")
        )
        return {"agreement_id": agreement_id, "raw": response}

    def charge_recurring_agreement(self, agreement_id: str, payload: dict) -> dict:
        """Charge a recurring agreement and return payment metadata."""
        response = self._request(
            "POST", f"/recurring/agreements/{agreement_id}/charges", payload
        )
        return {
            "id": response.get("id") or response.get("paymentId"),
            "paymentid": response.get("paymentId") or response.get("id"),
            "status": response.get("status"),
            "raw": response,
        }

    def cancel_recurring_agreement(self, agreement_id: str) -> dict:
        """Cancel a recurring agreement."""
        response = self._request("POST", f"/recurring/agreements/{agreement_id}/cancel", {})
        return {"id": agreement_id, "raw": response}

    def _request(self, method: str, endpoint: str, payload: dict | None = None) -> dict:
        """Execute HTTP request against Nets recurring endpoints."""
        url = f"{self.base_url}{endpoint}"
        body = None if payload is None else json.dumps(payload).encode()
        headers = {
            "Authorization": self.secret_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Checkout-Key"] = self.api_key

        req = urlrequest.Request(url=url, data=body, method=method, headers=headers)
        try:
            with urlrequest.urlopen(req, timeout=30) as response:
                response_payload = response.read().decode() or "{}"
        except HTTPError as err:
            error_payload = err.read().decode() if err.fp else ""
            if error_payload:
                raise RuntimeError(
                    f"Nets recurring API HTTP {err.code} {err.reason}: {error_payload}"
                ) from err
            raise RuntimeError(f"Nets recurring API HTTP {err.code} {err.reason}") from err
        except URLError as err:
            raise RuntimeError(f"Nets recurring API connection error: {err.reason}") from err

        parsed = json.loads(response_payload)
        return parsed if isinstance(parsed, dict) else {}
