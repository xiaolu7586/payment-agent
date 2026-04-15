---
name: browser-checkout
description: "Use this skill to execute the actual purchase after payment-guard has approved the transaction. Handles context gathering, product search, price comparison, and checkout form submission via cloud browser automation."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.4.0"
  homepage: "https://cloud.browser-use.com"
---

# Browser Checkout — Cloud Browser Execution Layer

Executes browser-based shopping workflows using browser-use.com cloud automation.

> Only call this skill AFTER payment-guard has confirmed the transaction is approved.
> By the time this skill runs, card existence is already guaranteed by payment-guard Phase 0.

---

## Phase 0: Context Gathering

Context is collected lazily — only when the current purchase scenario requires it.
Once collected, saved to USER.md and re-confirmed on subsequent uses.

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

### 0b. Merchant Login / Browser Profile (skip for recurring subscription auto-renew)

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

### 0c. Card Balance Check (always)

> Card existence is already confirmed by payment-guard. This step only verifies
> the selected card has sufficient balance for this specific purchase.

```bash
agentcard balance <card_id>
```

Determine effective balance using dual-track logic:
- **"Available balance: $X" shown** → use that figure (real-time)
- **"Real-time balance is not available"** → estimate:
  `effective_balance = card.loaded (USER.md) − sum of Purchase Log entries for this card`

```
If effective_balance >= estimated purchase amount → proceed
If effective_balance < estimated purchase amount:
  → "Your card has ~$X remaining, which may not cover this purchase (~$Y).
     Would you like to top up before continuing?"
  → If user tops up → add new card → proceed
  → If user declines → cancel and report
```

> If checkout fails with a card decline despite sufficient estimated balance,
> treat it as a balance discrepancy (card may have been used outside this agent)
> and trigger card rotation (agentcard Workflow 5).

---

## Phase 1: Search & Compare

```python
from browser_use_sdk import BrowserUseClient
import os, json
from pathlib import Path

# Load API key: env var first, fallback to .secrets/env.json
api_key = os.environ.get("BROWSER_USE_API_KEY")
if not api_key:
    secrets = Path(".secrets/env.json")
    if secrets.exists():
        api_key = json.loads(secrets.read_text()).get("BROWSER_USE_API_KEY")

client = BrowserUseClient(api_key=api_key)

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

## Phase 3: Post-Purchase (Success)

**Step 1 — Report to AgentCard's tracking server:**
```bash
agentcard track-purchase \
  --name "<item name>" \
  --amount "<final_amount_in_dollars>" \
  --store "<merchant domain>" \
  --card-id "<card_id>" \
  --intent "<what the user asked for>"
```
> CLI args: `--name`, `--amount`, `--store`, `--card-id`, `--intent`, `--incomplete` (flag for failures).
> Do NOT use `--merchant` or `--status` — those don't exist.

**Step 2 — Append to USER.md Purchase Log:**
```
[ISO timestamp] | purchase | [merchant] | $[final_amount] | [card_id] | success | [order_id]
```

For subscription purchases, use event type `subscription` and add recurrence info in detail:
```
[ISO timestamp] | subscription | [merchant] | $[amount]/month | [card_id] | success | [order_id] plan=[plan_name]
```

**Step 3 — Report to user:**
- Order confirmation number
- Final amount charged
- Estimated card balance remaining

**Step 4 — Balance warning:**
```
effective_balance = (real-time from agentcard balance) OR (card.loaded − sum of Purchase Log for card_id)

If effective_balance < max($20, 2 × approval_threshold):
  → "Card balance is ~$X. Consider topping up before your next purchase."
  → Scan Purchase Log for subscription entries on this card:
    → "Your [Spotify / Notion] subscriptions use this card and will fail when it runs out."
```

---

## Failure Logging

**Every failure must be logged to USER.md Purchase Log** — failures are just as important as
successes for balance estimation and debugging.

```
# Card declined
[ISO timestamp] | failed | [merchant] | $[amount] | [card_id] | declined | possible balance issue

# CAPTCHA / bot detection
[ISO timestamp] | failed | [merchant] | $[amount] | [card_id] | captcha | reported to agentcard support

# Checkout timeout
[ISO timestamp] | failed | [merchant] | $[amount] | [card_id] | timeout | cart may still be filled

# Out of stock (item not available at checkout)
[ISO timestamp] | failed | [merchant] | $[amount] | [card_id] | out_of_stock | [item name]

# Price changed above threshold
[ISO timestamp] | failed | [merchant] | $[new_amount] | [card_id] | price_changed | was $[original], exceeded threshold
```

Also call `agentcard track-purchase` with `--incomplete` flag for all failures:
```bash
agentcard track-purchase \
  --name "<item>" \
  --amount "<amount>" \
  --store "<merchant>" \
  --card-id "<card_id>" \
  --incomplete \
  --intent "<what user asked for>"
```

## Failure Actions

| Failure | Action |
|---------|--------|
| CAPTCHA encountered | Stop. Report to user. Run `agentcard support --message ... --card-id ...`. Log as `captcha`. |
| Card declined | Run `agentcard balance`. Report to user. Log as `declined`. Trigger card rotation if balance is low. |
| Item out of stock | Report. Offer alternatives (re-run Phase 1). Log as `out_of_stock`. |
| Price changed between Phase 1 and Phase 2 | Surface new price. Re-run payment-guard threshold check. Log as `price_changed`. |
| Final price exceeds threshold | Pause and escalate. Log as `price_changed`. |
| Browser profile session expired | Notify user. Re-run Phase 0b Case A. Do NOT log as failure — resume after re-auth. |
| Checkout timeout | Report. Do NOT retry without explicit instruction. Log as `timeout`. |
| Phase 2b fails after cart is filled | Report. Warn user item may still be in cart. Log as `failed`. |

---

## Security Rules

- `agentcard details` is run via CLI immediately before Phase 2b — never cached between sessions.
- PAN, CVV, expiry are cleared (`= ""`) immediately after the browser session completes.
- Never include card values in conversation messages, logs, or USER.md.
- browser-use task strings containing card values are session-scoped and not persisted.
