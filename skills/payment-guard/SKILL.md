---
name: payment-guard
description: "Use this skill before every purchase attempt. Validates whether a transaction is permitted under the user's configured rules: merchant whitelist and amount threshold. Triggers automatically before any checkout — not called directly by the user."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.2.0"
---

# Payment Guard — Pre-Purchase Rule Engine

Enforces the user's authorization rules before any purchase is executed.
Must be called before every checkout attempt, without exception.

---

## Pre-Guard: Scenario Classification

Before running the two-layer check, identify the purchase type:

| Type | Examples | Needs Shipping? | Needs Merchant Login? |
|------|----------|-----------------|----------------------|
| Physical goods | Amazon, Nike, Target | Yes | Yes (account) |
| Digital / SaaS credits | OpenAI, Vercel, Cursor | No | Yes (account) |
| Subscription (new) | Spotify, Netflix | No | Yes (account) |
| Subscription (recurring, card already saved) | Auto-renew | No | No |
| Tickets | Ticketmaster | No | Yes (account) |

Pass the scenario type to browser-checkout so it knows which Phase 0 context checks to run.

---

## Layer 1: Merchant Whitelist

If `whitelist_enabled: true` in USER.md:
- Extract domain from target merchant URL
- Check against `approved_merchants` list in USER.md
- **Not on list → STOP.** Tell user which merchant was blocked.
  Offer to add it: "Would you like to add [merchant] to your approved list?"
  If user confirms → update USER.md → re-run guard.
- **On list → proceed to Layer 2.**

If `whitelist_enabled: false` → skip to Layer 2.

---

## Layer 2: Amount Threshold

Read `approval_threshold` from USER.md.

**If USER.md is missing or `approval_threshold` is not set → treat as 0.**
(All purchases require explicit confirmation until the user configures a threshold.)

```
amount <= threshold  →  auto-approve  →  browser-checkout
amount >  threshold  →  pause, present details, wait for user confirmation
                          → confirmed  →  browser-checkout
                          → declined   →  cancel + log
```

When requesting confirmation, always show:
- Item name and description
- Merchant
- Estimated price (pre-tax/shipping)
- User's configured threshold
- Note: "Final price including tax and shipping will be confirmed again before payment is submitted."

---

## Decision Flow

```
purchase requested
       │
classify scenario (physical / digital / subscription)
       │
whitelist enabled?
  yes ──→ merchant on list? ──no──→ STOP (offer to add)
  │              │
  no          yes
  └──────┬─────┘
         ▼
  check threshold
         │
  amount <= threshold?
    yes ──→ auto-approve ──→ browser-checkout (with scenario type)
    no  ──→ request user confirmation
               │
          confirmed?
            yes ──→ browser-checkout (with scenario type)
            no  ──→ cancel + log
```

---

## Logging

After every decision, append one line to USER.md Purchase Log:
```
[ISO timestamp] | [merchant] | $[amount] | [approved/blocked/cancelled/pending] | [reason]
```

---

## Threshold Configuration

If the user asks to change their threshold or whitelist:
- Update USER.md immediately
- Confirm the new setting back to the user
- Example: "Done — purchases under $100 will now be approved automatically."

---

## Important

- This skill only decides. It does not execute any browser action or payment.
- Always pass the scenario classification to browser-checkout after approval.
- The final price (post tax/shipping) is re-checked inside browser-checkout Phase 2 — this is a second gate, not a replacement for this guard.
