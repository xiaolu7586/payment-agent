---
name: agentcard
description: "Use this skill when the user wants to: set up a payment card, import an existing card, top up balance, check balance, view transaction history, request a refund, or when a checkout flow needs card credentials. Triggers: set up card, add funds, top up, how much is left on my card, card balance, refund, payment card setup, buy card, load card, I already have a card, import my card, connect my agentcard."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.5.0"
  homepage: "https://agentcard.ai"
---

# AgentCard — Prepaid Virtual Visa Card Management

Manages the full lifecycle of the user's AgentCard: setup, funding, balance checks,
card credential retrieval for checkout, refunds, and card rotation.

> AgentCard issues prepaid virtual Visa cards for AI agents.
> Cards work at **US-based merchants only**. Value range: **$5–$200** in $5 increments.

---

## Pre-flight

Ensure `agentcard` CLI is installed:
```bash
npm install -g agentcard
```

---

## 0. Entry Point — New or Returning User?

When a user asks to set up / connect a card, **always ask first — and only this one question**:

> "Do you already have an AgentCard account, or would you like to create one?"

- **"I already have one"** → go to **Workflow 0.5 (Import Existing Cards)**
- **"Create new" / first time** → go to **Workflow 1 (First-Time Setup)**

Never assume. Asking prevents creating a duplicate account and avoids charging the user for a card they already own.

> ⚠️ Ask only this one question in the first turn. Do NOT bundle email or amount
> questions here — those come after the user answers new-vs-returning.
> If the user has already volunteered an amount (e.g. "帮我开一张 $20 的卡"),
> note it silently and skip re-asking later.

---

## 0.5. Import Existing Cards (Returning User)

Use when the user says they already have an AgentCard account.

```bash
# Step 1: authenticate with existing account (same CLI, magic link)
agentcard signup --email <user_email>
```
> This command works for both new signups and returning logins — the CLI sends a magic link either way.

Ask user to click the link in their email, then wait for confirmation.

```bash
# Step 2: list all cards on this account
agentcard list
```

Parse the output and present the cards to the user in a readable table:

```
Here are the cards on your account:

  #  Card ID       Amount     Status    Purchased
  1  card_abc123   $45.00     active    2025-03-10
  2  card_def456   $50.00     active    2025-01-05

Which card(s) would you like to use with this agent?
You can import all of them, or just the ones with balance.
```

**After user selects:**

```bash
# Step 3: check balance for each selected card
agentcard balance <card_id>
```

Parse the output using the same dual-track logic as Workflow 3:
- If real-time balance is shown → use it as `loaded` in USER.md
- If "Real-time balance is not available" → use `Amount` from `agentcard list` as `loaded` (original denomination)

**Write each selected card to USER.md:**

> ⚠️ Date format: `agentcard list` shows dates as M/D/YYYY (e.g. "4/8/2026").
> Convert to ISO format YYYY-MM-DD (e.g. "2026-04-08") before writing to USER.md.

```yaml
cards:
  - id: "<card_id>"
    label: "<user label or 'Imported'>"
    created: "<YYYY-MM-DD converted from M/D/YYYY in list output>"
    loaded: "$<real-time balance if available, else original denomination>"
    status: "active"
```

Mark cards shown as $0 or expired in `agentcard list` as depleted:
```yaml
    status: "depleted"
    depleted_date: "<today>"
```

Confirm to user — if real-time balance available:
> "Done — I've linked your card (last 4: XXXX): $Y available."

If only denomination known:
> "Done — I've linked your $X card. If it's been used before, actual remaining balance may be lower — I'll track purchases from here on."

If all cards are depleted, offer to create a new one:
> "Your existing cards are all empty. Would you like to load a new one? ($5–$200)"

---

## 1. First-Time Setup

```bash
# Step 1: authenticate (one-time — magic link sent to user email)
agentcard signup --email <user_email>
```
Ask the user to click the link in their email, then wait for confirmation before proceeding.

```bash
# Step 2: create prepaid card — returns a Stripe Checkout URL
agentcard create --amount <amount>
# Valid: 5, 10, 15 ... 200
```

> If the user already stated an amount earlier in the conversation, use it directly.
> Do NOT ask again.

Present the Stripe URL to the user **immediately** — no text confirmation is required
before generating the link. The Stripe page is the natural confirmation gate.

> "Here's your payment link: [URL]
>  Once you've completed payment, let me know and I'll verify activation."

Wait for them to confirm payment is complete.

```bash
# Step 3: verify activation
agentcard list
# Capture the new card ID from output
```

**Write to USER.md immediately after activation:**
```yaml
cards:
  - id: "<card_id>"
    label: "<optional user label>"
    created: "<YYYY-MM-DD>"
    loaded: "$<amount>"
    status: "active"
```
Confirm to user: "Your $X card is ready. Card ID saved."

---

## 2. Top Up (New Card)

Same as steps 2–3 of setup. Each top-up creates a new card with a new card number.

After activation, append to USER.md `cards` list:
```yaml
  - id: "<new_card_id>"
    label: "Top-up <date>"
    created: "<YYYY-MM-DD>"
    loaded: "$<amount>"
    status: "active"
```

> ⚠️ New card = new card number. Any SaaS subscriptions on the old card
> will NOT transfer automatically. See Card Rotation section below.

---

## 3. Balance & Transaction History

```bash
agentcard balance <card_id>
```

**The API returns `availableBalanceCents` when supported by the card — use it if present.
Fall back to Purchase Log estimate if null.**

```
Parse agentcard balance output:

Case A — "Available balance: $X" is printed:
  → Use this as the authoritative real-time balance.
  → Also display transaction list if shown.

Case B — "Real-time balance is not available for this card." is printed:
  → availableBalanceCents is null for this card type.
  → Estimate from Purchase Log:
      estimated_balance = card.loaded (USER.md) − sum of approved purchases logged for this card_id
  → Tell user:
     "Estimated balance: ~$X (real-time balance not available for this card —
      calculated from purchases tracked in this agent)"
  → If the card was used outside this agent, the estimate may be inaccurate.
```

**Low-balance warning (run after every purchase regardless of which case):**

```
effective_balance = real-time balance (Case A) OR estimated balance (Case B)

if effective_balance < max($20, 2 × approval_threshold):
  → Warn: "Your card balance is running low (~$X remaining).
           Consider topping up — a new card takes only a minute to set up."
  → If user has active subscriptions on this card:
    → "Note: your [Spotify / Notion] subscriptions use this card.
       When it runs out, those will fail. Set up a new card and update them now?"
```

---

## 4. Retrieve Card Credentials for Checkout

```bash
agentcard details <card_id>
# Actual output (verified):
#   Number:  <16-digit number>    → pan          (field label is "Number:", NOT "PAN:")
#   CVV:     <3-digit number>     → cvv
#   Expiry:  MM/YYYY              → e.g. "02/2033"  (MM/YYYY, NOT MM/YY)
#   Amount:  $XX.00               → denomination (ignore for credential use)
#
# Also derive: expiry_short = MM/YY (e.g. "02/33") for forms that expect short format
```

**SECURITY:**
- Invoke this command only inside the browser-checkout skill, immediately before Phase 2b.
- Parse Number/CVV/Expiry from stdout — store as ephemeral local variables only.
- Pass to browser-use via `secrets=` dict, NOT in the task string.
- Clear all four variables (`pan`, `cvv`, `expiry`, `expiry_short`) immediately after `client.sessions.stop()`.
- Do NOT echo or log these values anywhere.

---

## 5. Card Rotation (when a card is depleted)

When `agentcard balance` shows $0 (or near-zero) and the user wants to continue:

**Step 1 — Create new card** (see Top Up section above).

**Step 2 — Identify affected subscriptions:**
```
Scan USER.md Purchase Log for recurring entries using the depleted card ID.
Present list to user:
  "These subscriptions were using your old card and will now fail:
   - Spotify ($X/month)
   - Notion ($Y/month)
   Would you like me to update the payment method on each of them?"
```

**Step 3 — Update payment method per platform (if user confirms):**

For each affected subscription, retrieve new card credentials (agentcard Workflow 4) and
run a browser-use task to update billing settings.

Do NOT hardcode billing URLs — they change and vary by merchant.
Let the browser agent navigate from the merchant home page:

```python
from browser_use_sdk import BrowserUse
# (client already initialised with api_key)

# Get new card credentials via CLI immediately before this call
# (agentcard details <new_card_id> → pan, cvv, expiry, expiry_short)

update_session = client.sessions.create(
    profile_id=merchant_profile_id,   # existing login profile for this merchant
    start_url=f"https://{merchant_domain}",   # navigate from home, not hardcoded billing path
    proxy_country_code="us",
    keep_alive=True
)
result = client.run(
    task=(
        f"You are logged in to {merchant_domain}. "
        f"Navigate to the billing or subscription settings page. "
        f"Find the saved payment method and update it to a new card: "
        f"card number {{{{pan}}}}, "
        f"expiry {{{{expiry_short}}}} (try MM/YY first, use {{{{expiry}}}} if rejected), "
        f"CVV {{{{cvv}}}}. "
        f"Confirm the update was saved. "
        f"Return: success confirmation or error message."
    ),
    llm="claude-sonnet-4-5",
    session_id=str(update_session.id),
    secrets={"pan": pan, "cvv": cvv, "expiry": expiry, "expiry_short": expiry_short}
)
client.sessions.stop(str(update_session.id))
pan = cvv = expiry = expiry_short = ""
```

Log result per platform. If a platform update fails, report specifically which one and why.

**Step 4 — Update USER.md:**
Mark old card as depleted (preserve all other fields):
```yaml
cards:
  - id: "<old_card_id>"
    label: "<original label>"
    created: "<original date>"
    loaded: "<original amount>"
    status: "depleted"
    depleted_date: "<YYYY-MM-DD>"
```

---

## 6. Refund

```bash
agentcard refund <card_id> --amount <amount>
```

- Automated refunds: up to **$5 or 25% of card value** (whichever is greater).
- For larger amounts: tell user to email support@agentcard.ai with the card ID.

**Append to USER.md Purchase Log after every refund attempt:**
```
# Success
[ISO timestamp] | refund | [merchant] | $[refund_amount] | [card_id] | refunded | original order: [order_id]

# Failed / over limit (manual email required)
[ISO timestamp] | refund | [merchant] | $[requested_amount] | [card_id] | failed | exceeds auto-refund limit — manual email sent
```

---

## 7. Report Issues

```bash
agentcard support \
  --message "<description>" \
  --card-id "<card_id>" \    # include when issue is card-related
  --url "<url>" \            # optional — URL where issue occurred
  --error "<error>"          # optional — error message or code
```
Use for: declined transactions, CAPTCHA blocks, unexpected charges, payment failures.
`--card-id` is available and should be included whenever a specific card is involved.

---

## Rules

- Card IDs are always written to USER.md `cards` field immediately after activation.
- Never expose PAN, CVV, or expiry in conversation or logs.
- If the user has multiple active cards, prefer the one with sufficient balance;
  if multiple qualify, ask the user which to use.
- Always verify activation via `agentcard list` before writing card ID to USER.md.
