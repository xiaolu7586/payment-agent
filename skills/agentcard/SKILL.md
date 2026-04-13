---
name: agentcard
description: "Use this skill when the user wants to: set up a payment card, top up balance, check balance, view transaction history, request a refund, or when a checkout flow needs card credentials. Triggers: set up card, add funds, top up, how much is left on my card, card balance, refund, payment card setup, buy card, load card."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.1.0"
  homepage: "https://agentcard.ai"
---

# AgentCard — Prepaid Virtual Visa Card Management

Manages the full lifecycle of the user's AgentCard: setup, funding, balance checks, card credential retrieval for checkout, and refunds.

> AgentCard issues prepaid virtual Visa cards for AI agents. Cards work at US-based merchants only. Value range: $5–$200 in $5 increments.

## Pre-flight

Ensure `agentcard` CLI is installed: `npm install -g agentcard`

## Workflow

### 1. First-Time Setup

```bash
# Step 1: authenticate via magic link
agentcard signup --email <user_email>
# A magic link is sent to the user's email.
# Ask the user to click it, then confirm before proceeding.

# Step 2: create a prepaid card (returns a Stripe Checkout URL)
agentcard create --amount <amount>
# Valid amounts: 5, 10, 15, ... 200 (multiples of $5)
# Present the Stripe URL to the user — they must complete payment to activate the card.
# After user confirms payment, verify activation:
agentcard list
# Save the card ID to credentials for future use.
```

### 2. Top Up (New Card)

```bash
# Each top-up creates a new card
agentcard create --amount <amount>
# Present Stripe URL to user, wait for payment confirmation.
agentcard list
# Save new card ID to credentials.
```

### 3. Balance & History

```bash
agentcard balance <card_id>
# Returns: remaining balance + recent transaction history
# Note: balance refresh may take 2-3 minutes after a transaction.
```

### 4. Retrieve Card Credentials for Checkout

```bash
agentcard details <card_id>
# Returns: PAN, CVV, expiry date
# SECURITY: Use these values only to fill checkout forms via browser-checkout skill.
# Do NOT repeat card credentials in conversation. Do NOT log them.
```

### 5. Refund

```bash
agentcard refund <card_id> --amount <amount>
# Automated refunds: up to $5 or 25% of card value (whichever is greater).
# For larger refunds: inform user to contact support@agentcard.ai with card ID.
```

### 6. Report Issues

```bash
agentcard support --message "<description>"
# Use for: declined transactions, CAPTCHA blocks, payment failures.
```

## Rules

- Never expose PAN, CVV, or expiry in chat messages or logs.
- Always confirm card activation via `agentcard list` after a Stripe payment before storing the card ID.
- Always check balance before initiating a purchase — insufficient funds cause checkout failures.
- If the user has multiple cards, ask which one to use or use the one with sufficient balance.