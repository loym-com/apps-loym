# payment_nets_recurring

Odoo 19 addon extending `payment_nets` with recurring payments through Odoo's `payment.token`
framework.

## Scope

- No subscription model is added.
- Subscription billing logic remains in Odoo subscription/accounting models.
- Nets stores the recurring agreement/token and executes future charges.

## Features

- Enables Nets tokenization support (`support_tokenization`) for recurring usage.
- Adds `nets_support_recurring` provider metadata.
- Creates a recurring agreement during the first tokenized payment.
- Stores only Nets references (`provider_ref`) in `payment.token`.
- Supports token charging through recurring agreement API calls.

## Security

This module does not store PAN, CVV, or card expiry details.
