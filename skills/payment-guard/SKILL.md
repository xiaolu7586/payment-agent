---
name: payment-guard
description: "Use this skill before every purchase attempt. Validates whether a transaction is permitted under the user's configured rules: merchant whitelist and amount threshold. Triggers automatically before any checkout — not called directly by the user."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.3.0"
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

After every decision, append to USER.md Purchase Log:
```
[ISO timestamp] | [merchant] | $[amount] | [approved/blocked/cancelled/pending] | [reason]
```

---

## Threshold & Whitelist Configuration

If user asks to change rules → update USER.md immediately → confirm back.
Example: "Done — purchases under $100 will now be approved automatically."

---

## Important

- This skill only decides. It does not execute any browser action or payment.
- Phase 0 (card check) runs before everything else, every time.
- The final price (post tax/shipping) gets a second gate inside browser-checkout Phase 2.
