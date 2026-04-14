---
name: agentcard
description: "Use this skill when the user wants to: set up a payment card, import an existing card, top up balance, check balance, view transaction history, request a refund, or when a checkout flow needs card credentials. Triggers: set up card, add funds, top up, how much is left on my card, card balance, refund, payment card setup, buy card, load card, I already have a card, import my card, connect my agentcard."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.3.0"
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

When a user asks to set up / connect a card, **always ask first**:

> "Do you already have an AgentCard account, or would you like to create one?"

- **"I already have one"** → go to **Workflow 0.5 (Import Existing Cards)**
- **"Create new" / first time** → go to **Workflow 1 (First-Time Setup)**

Never assume. Asking prevents creating a duplicate account and avoids charging the user for a card they already own.

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

  #  Card ID       Balance    Created
  1  card_abc123   $45.00     2025-03-10
  2  card_def456   $0.00      2025-01-05

Which card(s) would you like to use with this agent?
You can import all of them, or just the ones with balance.
```

**After user selects:**

```bash
# Step 3: confirm balance for each selected card
agentcard balance <card_id>
```

**Write each selected card to USER.md:**
```yaml
cards:
  - id: "<card_id>"
    label: "<user label or 'Imported'>"
    created: "<original creation date from list output>"
    loaded: "<balance at import>"
    status: "active"
```

Mark any $0 cards as depleted:
```yaml
    status: "depleted"
    depleted_date: "<today>"
```

Confirm to user:
> "Done — I've linked X card(s) to your agent. [Card label]: $Y remaining."

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
Present the Stripe URL to the user. Wait for them to confirm payment is complete.

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
```

> ⚠️ New card = new card number. Any SaaS subscriptions on the old card
> will NOT transfer automatically. See Card Rotation section below.

---

## 3. Balance & Transaction History

```bash
agentcard balance <card_id>
# Returns: remaining balance + recent transaction list
# Note: may take 2–3 minutes to reflect the latest transaction
```

**After every balance check, run the low-balance warning:**

```
remaining_balance = <parsed from output>
monthly_cost_estimate = sum of known recurring subscriptions on this card (from USER.md Purchase Log)

if remaining_balance < max($20, 2 × approval_threshold):
  → Warn: "Card balance is running low: $X remaining.
           Consider topping up — a new $Y card takes only a minute to set up."
  → If user has active subscriptions on this card:
    → "Note: your [Spotify / X / Y] subscriptions use this card.
       When it runs out, those will stop. Would you like to set up a new card and update them now?"
```

---

## 4. Retrieve Card Credentials for Checkout

```bash
agentcard details <card_id>
# Returns: PAN, CVV, expiry
```

**SECURITY:**
- Invoke this command only inside the browser-checkout skill, immediately before form submission.
- Parse PAN, CVV, expiry from stdout — treat as ephemeral variables.
- Do NOT echo or log these values anywhere.
- Do NOT pass them between skills as named parameters in conversation.

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
For each affected subscription, trigger browser-checkout with task type `subscription-card-update`:
```bash
# browser-use task:
# "Go to [platform] billing settings.
#  Replace the saved card with: [new card details].
#  Confirm the update was saved."
```
Log result per platform. If a platform update fails, report specifically which one and why.

**Step 4 — Update USER.md:**
Mark old card as depleted:
```yaml
cards:
  - id: "<old_card_id>"
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
- Log refund attempt in USER.md Purchase Log.

---

## 7. Report Issues

```bash
agentcard support --message "<description>"
```
Use for: declined transactions, CAPTCHA blocks, unexpected charges, payment failures.

---

## Rules

- Card IDs are always written to USER.md `cards` field immediately after activation.
- Never expose PAN, CVV, or expiry in conversation or logs.
- If the user has multiple active cards, prefer the one with sufficient balance;
  if multiple qualify, ask the user which to use.
- Always verify activation via `agentcard list` before writing card ID to USER.md.
