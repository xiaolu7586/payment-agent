# Tools

## Runtime Dependencies

| Tool | Purpose | Install |
|------|---------|---------|
| `agentcard` | Virtual Visa card management | `npm install -g agentcard` |
| `browser-use-sdk` | Cloud browser automation for checkout | `pip install browser-use-sdk` |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BROWSER_USE_API_KEY` | Yes | API key from cloud.browser-use.com/settings |
| `AGENTCARD_SESSION` | Auto | Persisted after first `agentcard signup` |

## External Services

| Service | Role | Docs |
|---------|------|------|
| agentcard.ai | Prepaid virtual Visa card issuance and management | https://agentcard.ai/skill |
| cloud.browser-use.com | Cloud browser execution for checkout flows | https://docs.browser-use.com/cloud/quickstart |

## Known Constraints

- AgentCard supports **US-based merchants only**
- AgentCard card value range: **$5–$200** (multiples of $5)
- Automated refunds capped at: **$5 or 25% of card value** (whichever is greater)
- `agentcard signup` requires magic link click via email (one-time, at setup)
- Each top-up generates a new card and a Stripe Checkout URL for the user to complete payment

## Pre-flight Check

Before any purchase attempt, verify:
1. `agentcard balance <id>` — sufficient funds
2. `payment-guard` whitelist check — merchant is approved
3. `payment-guard` threshold check — amount is within auto-approve limit
4. User has confirmed the specific item, price, and merchant