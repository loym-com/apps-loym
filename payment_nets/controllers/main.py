"""HTTP controllers for Nets payment notifications."""

from __future__ import annotations

import json
import logging

from werkzeug.wrappers import Response

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class NetsController(http.Controller):
    """Expose webhook endpoints for Nets callbacks."""

    _webhook_url = "/payment/nets/webhook"

    @staticmethod
    def _extract_notification_data(**post_data):
        """Build notification data from JSON body or form payload."""
        raw_body = request.httprequest.get_data(as_text=True)
        if raw_body:
            try:
                data = json.loads(raw_body)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                _logger.info("Nets webhook body is not JSON; falling back to form data")
        return dict(post_data)

    @http.route(_webhook_url, type="http", auth="public", methods=["POST"], csrf=False)
    def nets_webhook(self, **post_data):
        """Validate and process Nets webhook callbacks."""
        notification_data = self._extract_notification_data(**post_data)
        if not notification_data:
            return Response("Missing notification payload", status=400)

        if not (
            notification_data.get("payment_id")
            or notification_data.get("id")
            or notification_data.get("reference")
            or notification_data.get("merchant_reference")
        ):
            return Response("Missing transaction identifiers", status=400)

        try:
            request.env["payment.transaction"].sudo()._handle_notification_data("nets", notification_data)
        except ValidationError:
            # Acknowledge on validation issues to avoid provider retries flooding logs.
            _logger.exception("Nets: failed to process webhook notification")
        return Response("", status=200)
