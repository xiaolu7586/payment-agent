---
name: browser-checkout
description: "Use this skill to execute the actual purchase after payment-guard has approved the transaction. Handles context gathering, product search, price comparison, and checkout form submission via cloud browser automation."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.3.0"
  homepage: "https://cloud.browser-use.com"
---

# Browser Checkout — Cloud Browser Execution Layer

Executes browser-based shopping workflows using browser-use.com cloud automation.

> Only call this skill AFTER payment-guard has confirmed the transaction is approved.

---

## Phase 0: Context Gathering (Before Every Purchase)

Context is collected lazily — only when the current purchase scenario requires it.
Once collected, context is saved to USER.md and re-confirmed on subsequent uses.

### 0a. Shipping Address (physical goods only — skip for SaaS, subscriptions, tickets, digital)

**Check USER.md `shipping_name` field:**

```
Case A — field is empty:
  → Ask: "This order will be shipped to you. What name and address should I use?"
  → Collect: name, line1, line2 (optional), city, state, zip, country
  → Save all fields to USER.md shipping section
  → Proceed

Case B — field is populated:
  → Ask: "Ship to: [name], [line1], [city] [state] [zip] — still correct?"
  → Confirmed → proceed
  → New address given → update USER.md → proceed
  → Never skip this re-confirmation for physical goods
```

### 0b. Merchant Account / Browser Profile (skip for recurring subscription auto-renew)

**Check USER.md `merchant_profiles.<merchant>` field:**

```
Case A — no profile saved:
  → Tell user: "I need to log in to [merchant] once on your behalf.
     I will open a browser session — please complete the login.
     Your session will be saved so this is a one-time step."
  → Create browser-use profile for this merchant
  → User completes login
  → Save returned Profile ID to USER.md: merchant_profiles.<merchant>
  → Proceed

Case B — profile ID saved:
  → Tell user: "Using your saved [merchant] session."
  → Load profile → proceed
  → If session turns out expired mid-checkout → notify user →
     return to Case A to re-authenticate
```

### 0c. AgentCard (always)

**Check USER.md `cards` field:**

```
Case A — no cards:
  → Pause purchase
  → "You have no payment card set up. Set one up now?" 
  → Trigger agentcard skill setup flow → return here when ready

Case B — cards present:
  → Run: agentcard balance <card_id>
  → If balance >= purchase amount → proceed
  → If balance < purchase amount → notify user, suggest top-up
```

---

## Phase 1: Search & Compare

```python
from browser_use_sdk import BrowserUseClient
import os

client = BrowserUseClient(api_key=os.environ["BROWSER_USE_API_KEY"])

session = client.sessions.create(
    task=(
        f"Go to {merchant_url}. "
        f"Search for: {product_description}. "
        f"Find the best match under ${budget}. "
        f"Return: product name, exact current price, product URL, and availability. "
        f"Do not add to cart yet."
    ),
    model="claude-sonnet-4-6",
    profile_id=merchant_profile_id   # from USER.md merchant_profiles
)
result = session.run()
```

Present to user: product name, price, URL.
**Wait for explicit user confirmation before proceeding to Phase 2.**

---

## Phase 2: Checkout

### Step 2a — Fill cart and get final price

```python
session = client.sessions.create(
    task=(
        f"Using the current session, go to {product_url}. "
        f"Add the item to cart and proceed to checkout. "
        f"Fill in shipping details: "
        f"Name: {shipping_name}, "
        f"Address: {shipping_line1} {shipping_line2}, "
        f"{shipping_city} {shipping_state} {shipping_zip}, {shipping_country}. "
        f"STOP before entering payment. "
        f"Return the final order total shown (including tax and shipping)."
    ),
    model="claude-sonnet-4-6",
    profile_id=merchant_profile_id
)
final_price = session.run()
```

**Mandatory final price confirmation:**
```
→ "Final total (including tax and shipping): $[final_price]
   This may differ from the listed price of $[search_price].
   Proceed with payment?"
→ Re-run payment-guard threshold check against final_price
→ Only proceed if user explicitly confirms
```

### Step 2b — Submit payment

Retrieve card credentials immediately before this step via CLI:

```bash
# Run in shell, capture stdout
agentcard details <card_id>
# Parse output lines to extract:
#   PAN:    <16-digit number>
#   Expiry: MM/YY
#   CVV:    <3-digit number>
# Store as short-lived local variables — not in conversation, not in logs
```

```python
session = client.sessions.create(
    task=(
        f"Fill in payment details: "
        f"Card number: {pan}, Expiry: {expiry}, CVV: {cvv}. "
        f"Submit the order. "
        f"Return: order confirmation number and final amount charged."
    ),
    model="claude-sonnet-4-6",
    profile_id=merchant_profile_id
)
order_result = session.run()

# Immediately clear card values from scope
pan = cvv = expiry = ""
```

---

## Phase 3: Post-Purchase

```bash
agentcard track-purchase \
  --merchant "<merchant>" \
  --amount "<final_amount>" \
  --status "success"
```

Append to USER.md Purchase Log:
```
[ISO timestamp] | [merchant] | $[amount] | success | [order_id]
```

Report to user:
- Order confirmation number
- Final amount charged
- Remaining card balance (run `agentcard balance <card_id>`)

**Balance warning** (run after every purchase):
```
If remaining_balance < max($20, 2 × approval_threshold):
  → "Card balance is $X. Consider topping up before your next purchase."
  → If recurring subscriptions detected on this card:
    → "Your [service] subscription will stop working when this card runs out."
```

---

## Failure Handling

| Failure | Action |
|---------|--------|
| CAPTCHA encountered | Stop. Report to user. Run `agentcard support`. Do NOT retry silently. |
| Card declined | Run `agentcard balance`. Report reason. Do not retry without instruction. |
| Item out of stock | Report. Offer to search for alternatives (re-run Phase 1). |
| Price changed between Phase 1 and Phase 2 | Surface new price. Re-run payment-guard threshold check. |
| Final price exceeds threshold | Pause and escalate — even if Phase 1 price was within threshold. |
| Browser profile session expired | Notify user. Re-run Phase 0b Case A to re-authenticate. |
| Checkout timeout | Report. Do NOT retry without explicit user instruction. |
| Phase 2b fails after cart is filled | Report. Advise user to check their [merchant] cart — item may still be there. |

---

## Security Rules

- `agentcard details` is run via CLI shell call immediately before Phase 2b — not cached between sessions.
- PAN, CVV, expiry are cleared (`= ""`) immediately after the browser session completes.
- Never include card values in conversation messages, logs, or USER.md.
- browser-use task strings containing card values are session-scoped and not stored by this agent.
