# User Configuration

## Payment Rules

whitelist_enabled: false
approved_merchants: []

# Purchases above this amount (USD) require explicit user approval before checkout.
approval_threshold: 50

## Card Registry

# Card IDs are stored here after setup. Do not edit manually.
cards: []

## Purchase Log

# Automatically appended by payment-guard and browser-checkout after each transaction.
# Format: [timestamp] merchant | amount | status | note