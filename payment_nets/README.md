# payment_nets

Odoo 19.0 Community addon implementing **Nets Easy** as a standard payment provider using the Odoo payment framework.

## Features

- Adds provider code `nets` to `payment.provider`
- Provider credentials and environment configuration:
  - `nets_api_key`
  - `nets_secret_key`
  - `nets_environment` (`test` / `production`)
- Redirect checkout flow through `_get_specific_rendering_values()`
- Webhook handling at `/payment/nets/webhook`
- Transaction lookup and state updates through the standard payment hooks:
  - `_get_tx_from_notification_data()`
  - `_process_notification_data()`
- API client isolated in `services/nets_api.py`

## Dependency

- `payment`

## Notes

- The API layer is structured for real Nets integration and currently uses endpoint placeholders.
- The module only handles payment processing (no subscriptions / recurring payments).

## Tests

Included tests cover:

- provider setup
- transaction rendering / payment request creation
- webhook processing with mocked Nets API responses
