---
name: browser-checkout
description: "Use this skill to execute the actual purchase after payment-guard has approved the transaction. Handles product search, price comparison, and checkout form submission via cloud browser automation. Triggers: after guard approval, execute purchase, complete checkout, search and buy, find best price."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.1.0"
  homepage: "https://cloud.browser-use.com"
---

# Browser Checkout — Cloud Browser Execution Layer

Executes browser-based shopping workflows using browser-use.com cloud automation. Handles search, price comparison, add-to-cart, and checkout form submission.

> Only call this skill AFTER payment-guard has confirmed the transaction is approved.

## Pre-flight

- `BROWSER_USE_API_KEY` must be set in environment.
- Card credentials (PAN, CVV, expiry) must be retrieved from agentcard skill immediately before checkout — do not cache or store them.
- Sufficient card balance must be confirmed via `agentcard balance` before proceeding.

## SDK Setup

```python
from browser_use_sdk import BrowserUseClient

client = BrowserUseClient(api_key=os.environ["BROWSER_USE_API_KEY"])
```

## Workflow

### Step 1: Search & Compare

```python
session = client.sessions.create(
    task=f"Go to {merchant_url}. Search for: {product_description}. "
         f"Find the best match under ${budget}. Return: product name, price, "
         f"product URL, and availability. Do not add to cart yet.",
    model="claude-sonnet-4-6"
)
result = session.run()
```

Present results to user for confirmation before proceeding to checkout.

### Step 2: Checkout (after user confirms)

```python
# Retrieve card credentials immediately before use
card = agentcard.details(card_id)  # PAN, CVV, expiry

session = client.sessions.create(
    task=f"""
Go to {product_url}.
Add the item to cart.
Proceed to checkout.
Fill in shipping details:
  Name: {shipping_name}
  Address: {shipping_address}
Fill in payment details:
  Card number: {card.pan}
  Expiry: {card.expiry}
  CVV: {card.cvv}
Submit the order.
Return: order confirmation number and final amount charged.
""",
    model="claude-sonnet-4-6"
)
result = session.run()

# Immediately discard card credentials after session completes
del card
```

### Step 3: Post-Purchase

```bash
# Log the transaction
agentcard track-purchase \
  --merchant <merchant> \
  --amount <amount> \
  --status <success|failed> \
  --order-id <order_id>
```

Report to user: order confirmation number, amount charged, remaining card balance.

## Failure Handling

| Failure | Action |
|---------|--------|
| CAPTCHA encountered | Report to user, run `agentcard support`, do NOT retry silently |
| Card declined | Check balance via `agentcard balance`, report to user |
| Item out of stock | Report to user, offer to search for alternatives |
| Price changed since search | Report new price, re-run payment-guard threshold check |
| Checkout timeout | Report to user, do NOT retry without explicit instruction |

## Security Rules

- Card credentials (PAN, CVV, expiry) must be fetched fresh for each transaction.
- Never store card credentials in session state, logs, or conversation history.
- Never surface card credentials in any user-facing message.
- Use `del card` / variable cleanup immediately after the browser session completes.