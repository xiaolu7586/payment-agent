---
name: payment-guard
description: "Use this skill before every purchase attempt. Validates whether a transaction is permitted under the user's configured rules: merchant whitelist and amount threshold. Triggers automatically before any checkout — not called directly by the user."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.1.0"
---

# Payment Guard — Pre-Purchase Rule Engine

Enforces the user's authorization rules before any purchase is executed. Must be called before every checkout attempt, without exception.

## Two-Layer Check

### Layer 1: Merchant Whitelist

If the user has whitelist mode enabled:
- Extract the domain from the target merchant URL.
- Check against the user's approved merchant list stored in USER.md.
- If the merchant is NOT on the whitelist → **STOP. Do not proceed.**
  - Tell the user: which merchant was blocked and why.
  - Offer to add the merchant to the whitelist if the user confirms.
- If the merchant IS on the whitelist → proceed to Layer 2.

If whitelist mode is disabled → skip to Layer 2.

### Layer 2: Amount Threshold

- Compare the purchase amount against the user's configured approval threshold.
- If amount <= threshold → **auto-approve**, proceed to checkout.
- If amount > threshold → **pause, request explicit user approval**.
  - Present: item name, merchant, exact price, threshold limit.
  - Wait for user confirmation before proceeding.
  - If user declines → cancel and log the attempt.

## Decision Flow

```
purchase requested
       |
  whitelist ON?
   yes       no
    |         |
check       skip
whitelist    |
    |        |
 blocked?   check threshold
  yes  no    |
  |    |   over limit?
STOP  check   yes      no
      threshold |       |
           request   auto-approve
           approval  → browser-checkout
               |
          approved?
          yes     no
           |       |
      browser-  cancel
      checkout   + log
```

## Logging

After every decision, append to the audit log (USER.md > Purchase Log):
- Timestamp, merchant, amount, decision (approved / blocked / pending approval / cancelled), reason.

## USER.md Schema

The user's rules are stored in USER.md with this structure:

```
## Payment Rules

whitelist_enabled: true|false
approved_merchants:
  - amazon.com
  - ...

approval_threshold: 50   # USD — purchases above this require explicit user confirmation
```

## Important

- This skill does not execute any payment. It only decides whether to allow or block.
- A missing or unconfigured USER.md should be treated as: whitelist disabled, threshold = $0 (all purchases require approval).
- If the user asks to update their rules (add merchant, change threshold), update USER.md accordingly and confirm.