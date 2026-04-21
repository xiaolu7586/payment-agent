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

**If exactly one active card exists → use it. Record `card_id` for all downstream steps.**

**If multiple active cards exist → ask user:**
> "You have [N] cards: [Card A: $X remaining] [Card B: $Y remaining]. Which would you like to use for this purchase?"
> Default suggestion: the card with the highest estimated balance.
> Save the selected `card_id` and pass it to browser-checkout.

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

**How to detect "Subscription (recurring, card saved)":**
Scan USER.md Purchase Log for `subscription` entries where `merchant` matches the current merchant
AND `card_id` matches the active card AND `status: success`. If found → classify as recurring auto-renew
(skip merchant login and shipping). If not found → classify as new subscription.

Pass the scenario type to browser-checkout so it knows which Phase 0 context checks to run.

---

## Layer 0: US Merchant Validation (Early Warning)

**AgentCard only works with US-based merchants.** This is a hard technical limitation —
the card will be declined at non-US checkout regardless of whitelist or budget settings.

> ⚠️ This check runs **before any browsing or searching begins** — never after cart fill.
> The moment a non-US merchant is detected, stop and surface the warning immediately.

### How to detect a non-US merchant

Flag the merchant as **likely non-US** if any of the following are true:

| Signal | Examples |
|--------|----------|
| Country-code TLD | `.ca`, `.co.uk`, `.de`, `.fr`, `.co.jp`, `.com.au`, `.in`, `.mx`, `.es`, `.it`, `.com.br`, `.nl`, `.se`, `.no`, `.dk`, `.fi`, `.pl`, `.be`, `.ch`, `.at`, `.pt` |
| Known regional Amazon domain | `amazon.ca`, `amazon.co.uk`, `amazon.de`, `amazon.co.jp`, `amazon.com.au`, `amazon.com.mx`, `amazon.com.br`, `amazon.in`, `amazon.fr`, `amazon.it`, `amazon.es` |
| Pricing currency other than USD | Site shows CAD, GBP, EUR, AUD, JPY, INR, etc. |
| Explicit region indicator in URL | `/ca/`, `/uk/`, `/gb/`, `/de/`, `/au/`, `/fr/`, `/jp/`, `/in/`, `/mx/`, `/es/`, `/it/`, `/nl/`, `/se/`, `/br/` as path segment |

### Decision

```
non-US signal detected?
  yes → EARLY WARNING (before any browsing). Respond:

    "[Merchant] looks like a [country] storefront. AgentCard is US-only —
     payment will likely be declined at checkout.

     Options:
     1. Switch to [US equivalent, e.g. amazon.com] — recommended, higher success rate
     2. Try [merchant] anyway — I'll proceed but payment may fail

     Which would you prefer?"

    → User picks US equivalent:
        Update merchant to US version → proceed to Layer 1 normally.

    → User confirms non-US ("try anyway" / "just go for it"):
        Acknowledge risk: "OK, I'll try — but be aware the card will likely be
        declined at payment. I'll stop and report clearly if that happens."
        Log: [ISO timestamp] | warning | [merchant] | — | [card_id] | non_us_override | user confirmed
        Proceed to Layer 1 with non-US merchant.

    → User doesn't confirm either way:
        Do not proceed. Wait for explicit choice.

  no → proceed to Layer 1
```

> Key principle: surface the limitation **as early as possible** so the user can decide
> before any browsing work is done. Never discover non-US merchant issues mid-checkout.

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

# User warned about non-US merchant but chose to proceed anyway
[ISO timestamp] | warning    | [merchant] | —         | [card_id] | non_us_override | user confirmed

# Blocked by US merchant check (user declined to proceed)
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
