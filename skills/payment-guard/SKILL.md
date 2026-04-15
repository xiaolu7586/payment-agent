---
name: payment-guard
description: "Use this skill before every purchase attempt. Validates whether a transaction is permitted under the user's configured rules: merchant whitelist and amount threshold. Triggers automatically before any checkout — not called directly by the user."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.4.0"
---

# Payment Guard — Pre-Purchase Rule Engine

Enforces the user's authorization rules before any purchase is executed.
Must be called before every checkout attempt, without exception.

---

## Phase 0: Card Existence Check (ALWAYS FIRST)

Before any other check, read USER.md `cards` field.

**If `cards` is empty or all cards have `status: depleted`:**
→ **HARD STOP. Do not proceed. Do not search. Do not open any browser.**
→ Respond:
  "Before I can process purchases, you'll need a payment card first.
   It only takes a minute — shall we set one up now?"
→ Trigger agentcard skill setup flow.
→ Only after a card is successfully created and written to USER.md,
  offer to resume the original purchase request.

**If at least one active card exists → proceed to Pre-Guard.**

> Note: The soft reminder (no card, non-purchase context) is handled in SOUL.md.
> This skill only handles the hard block triggered by a purchase request.

---

## Pre-Guard: Scenario Classification

Identify the purchase type before running rules:

| Type | Examples | Needs Shipping? | Needs Merchant Login? |
|------|----------|-----------------|----------------------|
| Physical goods | Amazon, Nike, Target | Yes | Yes |
| Digital / SaaS credits | OpenAI, Vercel, Cursor | No | Yes |
| Subscription (new) | Spotify, Netflix | No | Yes |
| Subscription (recurring, card saved) | Auto-renew | No | No |
| Tickets | Ticketmaster | No | Yes |

Pass the scenario type to browser-checkout so it knows which Phase 0 context checks to run.

---

## Layer 0: US Merchant Validation (Hard System Constraint)

**AgentCard only works with US-based merchants.** This is a hard technical limitation — the card will be declined at non-US checkout regardless of whitelist or budget settings.

### How to detect a non-US merchant

Flag the merchant as **likely non-US** if any of the following are true:

| Signal | Examples |
|--------|----------|
| Country-code TLD | `.ca`, `.co.uk`, `.de`, `.fr`, `.co.jp`, `.com.au`, `.in`, `.mx`, `.es`, `.it` |
| Known regional Amazon domain | `amazon.ca`, `amazon.co.uk`, `amazon.de`, `amazon.co.jp`, `amazon.com.au`, `amazon.com.mx`, `amazon.com.br`, `amazon.in`, `amazon.fr`, `amazon.it`, `amazon.es` |
| Pricing currency other than USD | Site shows CAD, GBP, EUR, AUD, JPY, INR, etc. |
| Explicit region indicator in URL | `/ca/`, `/uk/`, `/de/`, `/au/` path prefix |

### Decision

```
non-US signal detected?
  yes → HARD STOP. Respond:
          "AgentCard only works with US merchants — [merchant] looks like a [country]
           storefront. A US purchase card won't be accepted there.
           If you meant the US version, I can switch to amazon.com instead.
           Otherwise you'd need a different payment method for this merchant."
        Offer to redirect to US equivalent if one exists (e.g. amazon.com).
        Do not proceed until user confirms a US merchant.

  no → proceed to Layer 1
```

> This check runs before both the whitelist and the threshold — there's no point validating rules for a merchant where payment is impossible.

---

## Layer 1: Merchant Whitelist

If `whitelist_enabled: true` in USER.md:
- Extract domain from target merchant URL.
- Check against `approved_merchants` list.
- **Not on list → STOP.** Tell user which merchant was blocked.
  Offer to add it: "Would you like to add [merchant] to your approved list?"
  If user confirms → update USER.md → re-run guard.
- **On list → proceed to Layer 2.**

If `whitelist_enabled: false` → skip to Layer 2.

---

## Layer 2: Amount Threshold

Read `approval_threshold` from USER.md.
If missing or not set → treat as 0 (all purchases require confirmation).

```
amount <= threshold  →  auto-approve  →  browser-checkout
amount >  threshold  →  pause, show details, wait for explicit confirmation
                          confirmed  →  browser-checkout
                          declined   →  cancel + log
```

When requesting confirmation always show:
- Item name, merchant, estimated price
- User's configured threshold
- Note that final price (with tax/shipping) will be confirmed again before payment

---

## Decision Flow

```
purchase requested
       │
  cards exist?
  no ──→ HARD STOP → guide card setup → resume after
  yes
       │
classify scenario
       │
  US merchant?
  no ──→ HARD STOP → warn user → offer US equivalent → wait for confirmation
  yes
       │
whitelist enabled?
  yes ──→ merchant on list? ──no──→ STOP (offer to add)
  │              │yes
  no             │
  └──────┬───────┘
         ▼
   check threshold
         │
  within threshold?
   yes ──→ auto-approve ──→ browser-checkout
   no  ──→ request confirmation
               │
          confirmed?
           yes ──→ browser-checkout
           no  ──→ cancel + log
```

---

## Logging

Append to USER.md Purchase Log after every guard decision (approved, blocked, or cancelled).
Use the unified format — **always include card_id** even if the card wasn't charged:

```
# Approved (handed off to browser-checkout — final result logged there)
[ISO timestamp] | purchase   | [merchant] | $[amount] | [card_id] | guard_approved | threshold=$[threshold]

# Blocked by whitelist
[ISO timestamp] | blocked    | [merchant] | $[amount] | [card_id] | guard_blocked  | not on whitelist

# Blocked by US merchant check
[ISO timestamp] | blocked    | [merchant] | $[amount] | [card_id] | guard_blocked  | non-US merchant

# User cancelled at threshold gate
[ISO timestamp] | cancelled  | [merchant] | $[amount] | [card_id] | user_cancelled | threshold=$[threshold]
```

> If no card is active yet (Phase 0 hard stop), omit card_id field (use `—`).

---

## Threshold & Whitelist Configuration

If user asks to change rules → update USER.md immediately → confirm back.
Example: "Done — purchases under $100 will now be approved automatically."

---

## Important

- This skill only decides. It does not execute any browser action or payment.
- Phase 0 (card check) runs before everything else, every time.
- The final price (post tax/shipping) gets a second gate inside browser-checkout Phase 2.
