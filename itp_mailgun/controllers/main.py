
import hashlib
import hmac
import time

from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotAcceptable, ServiceUnavailable


# Sikkerhetsmerknad: Denne versjonen validerer signaturen og tidsstempelet, men implementerer ikke lagring av brukte token-verdier. For full beskyttelse mot replay-angrep bør modulen også lagre hver aksepterte token med en unik databasebegrensning. Det bør gjøres før du eksponerer endepunktet som en ferdig produksjonsløsning.


class MailMailgun(http.Controller):

    @http.route(
        "/mailgun/notify.mime",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
    )
    def mailgun_notify(self, **kw):
        form = request.httprequest.form

        timestamp = form.get("timestamp", "")
        token = form.get("token", "")
        signature = form.get("signature", "")
        mime_message = form.get("body-mime")

        if not timestamp or not token or not signature:
            raise NotAcceptable("Missing Mailgun signature fields")

        if not mime_message:
            raise NotAcceptable("Missing MIME message")

        try:
            timestamp_int = int(timestamp)
        except ValueError as error:
            raise NotAcceptable("Invalid timestamp") from error

        # Allow Mailgun's documented retry period of up to 8 hours.
        now = time.time()
        if timestamp_int > now + 300 or now - timestamp_int > 9 * 3600:
            raise NotAcceptable("Expired webhook")

        params = request.env["ir.config_parameter"].sudo()
        signing_key = params.get_param(
            "itp_mailgun.webhook_signing_key"
        )

        if not signing_key:
            raise ServiceUnavailable(
                "Mailgun webhook signing key is not configured"
            )

        digest = hmac.new(
            signing_key.encode("utf-8"),
            (timestamp + token).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(digest, signature):
            raise NotAcceptable("Invalid Mailgun signature")

        request.env["mail.thread"].sudo().message_process(
            False,
            mime_message,
        )

        return "ok"
