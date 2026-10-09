from urllib.parse import urlsplit

from odoo import http
from odoo.http import request
from werkzeug.exceptions import BadRequest


class MailMailgun(http.Controller):
    @http.route("/mailgun/notify", auth="public", type="http", csrf=False)
    def mailgun_notify(self, **kw):
        message_url = kw.get("message-url")
        if not isinstance(message_url, str):
            raise BadRequest("Missing message-url")

        try:
            parsed_url = urlsplit(message_url)
            port = parsed_url.port
        except ValueError as error:
            raise BadRequest("Invalid message-url") from error

        hostname = parsed_url.hostname or ""
        if (
            parsed_url.scheme != "https"
            or hostname not in ("api.mailgun.net", "api.eu.mailgun.net")
            or parsed_url.username is not None
            or parsed_url.password is not None
            or port not in (None, 443)
        ):
            raise BadRequest("Invalid message-url")

        request.env["mail.thread"].sudo().mailgun_fetch_message(message_url)
        return "ok"
