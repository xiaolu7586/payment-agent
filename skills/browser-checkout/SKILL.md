---
name: browser-checkout
description: "Use this skill to execute the actual purchase after payment-guard has approved the transaction. Handles context gathering, product search, price comparison, and checkout form submission via cloud browser automation."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.6.0"
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
  → If shipping_country ≠ US: surface cross-border notice (see below)
  → Proceed

Case B — field is populated:
  → Ask: "Ship to: [name], [line1], [city] [state] [zip] — still correct?"
  → Confirmed → if shipping_country ≠ US: surface cross-border notice (see below)
  → Confirmed → proceed
  → New address given → update USER.md → if shipping_country ≠ US: surface notice → proceed
  → Never skip this re-confirmation for physical goods
```

**Cross-border notice (show when shipping_country ≠ US and merchant is US-based):**
```
"Your shipping address is in [country]. Ordering from a US merchant means:
 • International shipping will be added at checkout (typically $10–$40+ depending on item/weight)
 • Some items may be 'US only' — if so, I'll report it and stop
 • Customs duties or import taxes may be charged by your country on delivery
   (these are separate from the purchase and paid to your customs authority)
 The card will work fine. Just flagging so the final total won't surprise you."
```
Show this notice once per session, not on every step.


### 0b. Merchant Login / Browser Profile (skip for recurring subscription auto-renew)

> **Never surface "not logged in" as a blocker for the user to solve.**
> When no login profile exists, immediately run Case A below — open a browser
> session and give the user a share_url. This step must complete before Phase 2
> begins. If Phase 1 (search) was already run without a profile, trigger Case A
> inline before proceeding to checkout — do not list login as a user-facing problem.

**Check USER.md `merchant_profiles.<merchant>` field:**

**Case A — no profile saved (first login to this merchant):**

```python
from browser_use_sdk import BrowserUse
import os, json
from pathlib import Path

api_key = os.environ.get("BROWSER_USE_API_KEY") or \
    json.loads(Path(".secrets/env.json").read_text()).get("BROWSER_USE_API_KEY")
client = BrowserUse(api_key=api_key)

# 1. Create a named profile for this merchant
profile = client.profiles.create(name=f"{merchant}-profile")
profile_id = str(profile.id)

# 2. Open a live browser session so user can log in
#    Start at merchant home page — let the browser agent find the login button.
#    Do NOT hardcode /signin — login URLs differ per merchant.
login_session = client.sessions.create(
    profile_id=profile_id,
    start_url=f"https://{merchant_domain}",
    proxy_country_code="us",
    keep_alive=True
)
session_id = str(login_session.id)

# 3. Get a shareable URL the user can open without a browser-use account.
#    live_url on SessionItemView requires browser-use dashboard login — don't use it.
#    create_share() returns a public share_url accessible by anyone.
share = client.sessions.create_share(session_id)
```

Tell user:
> "I've opened a browser at [merchant_domain]. Please sign in at:
>  **[share.share_url]**
>  Once you've signed in, let me know and I'll continue."

Wait for user confirmation, then:

```python
# 4. Close the login session (cookies now saved to profile)
client.sessions.stop(session_id)
```

Save to USER.md:
```yaml
merchant_profiles:
  <merchant>: "<profile_id>"
```

**Case B — profile ID saved:**

Tell user: "Using your saved [merchant] session — no need to log in again."
The `profile_id` will be passed to the checkout session in Phase 1/2.

```
→ If session turns out expired mid-checkout (login redirect):
  → Do NOT surface as a user-facing error.
  → Automatically re-run Case A: open new session, give share_url, wait for login.
  → Delete old profile entry from USER.md, save new profile_id.
  → Resume checkout from where it was interrupted.
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

> **Session architecture:** Phases 1, 2a, and 2b all run inside a **single persistent
> browser session** (`keep_alive=True`). This preserves page state between steps —
> the cart filled in 2a is still there when 2b runs payment. Never use separate
> `client.run()` calls without a shared `session_id` for multi-step checkout.

```python
from browser_use_sdk import BrowserUse
import os, json, subprocess, re
from pathlib import Path

# Load API key
api_key = os.environ.get("BROWSER_USE_API_KEY") or \
    json.loads(Path(".secrets/env.json").read_text()).get("BROWSER_USE_API_KEY")
client = BrowserUse(api_key=api_key)

# Create a persistent browser session (shared across Phase 1, 2a, 2b)
# sessions.create() takes profile_id as a plain string — no camelCase alias needed
live_session = client.sessions.create(
    profile_id=merchant_profile_id,   # str UUID from USER.md, or None if no profile yet
    proxy_country_code="us",          # AgentCard is US-only; keep proxy in US
    keep_alive=True                   # preserve browser state between tasks
)
session_id = str(live_session.id)

try:
    # Phase 1: Search
    result = client.run(
        task=(
            f"Go to {merchant_url}. "
            f"Search for: {product_description}. "
            f"Find the best match under ${budget}. "
            f"Return: product name, exact current price, product URL, and availability. "
            f"Do not add to cart yet."
        ),
        llm="claude-sonnet-4-5",
        session_id=session_id    # runs inside the live session
    )
except Exception as e:
    client.sessions.stop(session_id)
    # Log failure and report to user
    raise
```

Present to user: product name, price, URL.
**Wait for explicit user confirmation before proceeding to Phase 2.**

---

## Phase 2: Checkout

> Both steps run in the **same `session_id`** created in Phase 1.
> The browser stays open between 2a and 2b — page state is preserved.

### Step 2a — Fill cart and get final price

```python
try:
    result_2a = client.run(
        task=(
            f"Go to {product_url}. "
            f"Add the item to cart and proceed to checkout. "
            f"Fill in shipping details: "
            f"Name: {shipping_name}, "
            f"Address: {shipping_line1} {shipping_line2}, "
            f"{shipping_city} {shipping_state} {shipping_zip}, {shipping_country}. "
            f"STOP before entering any payment information. "
            f"Return the final order total shown (including tax and shipping)."
        ),
        llm="claude-sonnet-4-5",
        session_id=session_id    # same live session — browser is still at checkout
    )
except Exception as e:
    client.sessions.stop(session_id)
    # Log failure (see Failure Logging section) and report to user
    raise
final_price = result_2a  # parse dollar amount from result string
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
# Actual output field names (verified):
#   Number:  <16-digit number>   → pan   (field label is "Number:", NOT "PAN:")
#   CVV:     <3-digit number>    → cvv
#   Expiry:  MM/YYYY             → e.g. "02/2033"  ← MM/YYYY format, NOT MM/YY
#
# Derive short expiry for forms that expect MM/YY:
#   expiry_short = MM/YY  (e.g. "02/33")
# Pass both — browser agent uses whichever the checkout form requires.
```

Pass credentials via `secrets=` — **never put card values in the task string**.
The browser agent references them as `{{pan}}`, `{{cvv}}`, `{{expiry}}`, `{{expiry_short}}` —
injected by the browser-use runtime and never appear in logs or task text.

```python
try:
    result_2b = client.run(
        task=(
            "The checkout page is already open. "
            "Enter payment details: card number {{pan}}, CVV {{cvv}}. "
            "For expiry: try {{expiry_short}} first (MM/YY format, e.g. 02/33). "
            "If the form rejects it or requires 4-digit year, use {{expiry}} (MM/YYYY, e.g. 02/2033). "
            "Submit the order. "
            "Return: order confirmation number and final amount charged."
        ),
        llm="claude-sonnet-4-5",
        session_id=session_id,   # same live session — browser is at payment step
        secrets={
            "pan": pan,
            "cvv": cvv,
            "expiry": expiry,              # MM/YYYY e.g. "02/2033"
            "expiry_short": expiry_short,  # MM/YY   e.g. "02/33"
        }
    )
    order_result = result_2b
finally:
    # Always clear card credentials and stop session — even if run() raises
    pan = cvv = expiry = expiry_short = ""
    client.sessions.stop(session_id)
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

**In all failure cases: call `client.sessions.stop(session_id)` before returning.**

| Failure | Action |
|---------|--------|
| CAPTCHA encountered | Stop session. Report to user. Run `agentcard support --message ... --card-id ...`. Log as `captcha`. |
| Card declined | Stop session. Run `agentcard balance`. Report to user. Log as `declined`. Trigger card rotation if balance is low. |
| Item out of stock | Stop session. Report. Offer alternatives (re-run Phase 1 with new session). Log as `out_of_stock`. |
| Price changed between Phase 1 and Phase 2 | Stop session. Surface new price. Re-run payment-guard check. Log as `price_changed`. |
| Final price exceeds threshold | Stop session. Pause and escalate. Log as `price_changed`. |
| Browser profile session expired | Stop session. Notify user. Re-run Phase 0b Case A to re-authenticate. Start fresh session after. Do NOT log as failure. |
| Checkout timeout | Stop session. Report. Do NOT retry without explicit instruction. Log as `timeout`. |
| Phase 2b fails after cart is filled | Stop session. Report. Warn user item may still be in cart at [merchant]. Log as `failed`. |

---

## Security Rules

- `agentcard details` is run via CLI immediately before Phase 2b — never cached between sessions.
- All four card variables (`pan`, `cvv`, `expiry`, `expiry_short`) are cleared immediately after `client.sessions.stop()`.
- Never include card values in conversation messages, logs, or USER.md.
- Card values are passed via `secrets=` dict — they are injected by the browser-use runtime and do not appear in task strings, API logs, or browser history.
- The live session (`session_id`) is stopped immediately after Phase 2b completes or fails.
