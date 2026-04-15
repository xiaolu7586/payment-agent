# User Configuration

## Payment Rules

whitelist_enabled: false
approved_merchants: []

# Purchases above this amount (USD) require explicit user approval before checkout.
# Default: 0 — all purchases require confirmation until user sets a threshold.
approval_threshold: 0

## Card Registry

# Populated automatically after agentcard setup. Do not edit manually.
# Format: { id: "<card_id>", label: "<optional label>", created: "<date>" }
cards: []

## Shipping Address

# Collected on first physical-goods purchase. Re-confirmed on every subsequent use.
# Leave blank — agent will ask when needed.
shipping_name: ""
shipping_line1: ""
shipping_line2: ""
shipping_city: ""
shipping_state: ""
shipping_zip: ""
shipping_country: "US"

## Merchant Profiles

# Browser-use Profile IDs saved after first login to each merchant.
# Enables the agent to reuse authenticated sessions without re-entering credentials.
# Populated automatically. Do not edit manually.
# Re-confirmation prompt is shown to user before each use in case session has expired.
merchant_profiles:
  # amazon: "<browser-use-profile-id>"
  # vercel: "<browser-use-profile-id>"
  # notion: "<browser-use-profile-id>"

## Purchase Log

# Automatically appended after each transaction attempt (success, failure, blocked, refund).
# Format: [ISO timestamp] | [event] | [merchant] | $[amount] | [card_id] | [status] | [detail]
#
# event values : purchase | blocked | cancelled | failed | refund | subscription
# status values: success | declined | captcha | timeout | out_of_stock | price_changed | user_cancelled | guard_blocked | refunded
# detail       : order_id for purchases, reason for blocks/failures, refund amount for refunds
