# Tools

## Setup

Dependencies and credentials are handled automatically via `autorun.py` on first activation.
No manual installation required.

| Step | What happens |
|------|-------------|
| Agent installed | `autorun.py` runs automatically |
| Checks `agentcard` CLI | Installs via `npm install -g agentcard` if missing |
| Checks `browser-use-sdk` | Installs via `pip install browser-use-sdk` if missing |
| `BROWSER_USE_API_KEY` | Saved from formData to `.secrets/env.json` at install time |

---

## Runtime Dependencies

| Tool | Purpose | Installed by |
|------|---------|-------------|
| `agentcard` CLI | Virtual Visa card management | `autorun.py` |
| `browser-use-sdk` | Cloud browser automation for checkout | `autorun.py` |

---

## Credentials

| Credential | Where stored | How set |
|-----------|-------------|---------|
| `BROWSER_USE_API_KEY` | `.secrets/env.json` | Entered in formData at install time |
| `AGENTCARD_SESSION` | `~/.agentcard/` (auto) | Created after first `agentcard signup` |

When loading `BROWSER_USE_API_KEY` in skills:
1. Check `os.environ["BROWSER_USE_API_KEY"]` first
2. Fallback: read from `.secrets/env.json` → key `BROWSER_USE_API_KEY`

---

## External Services

| Service | Role | Docs |
|---------|------|------|
| agentcard.ai | Prepaid virtual Visa card issuance and management | https://agentcard.ai/skill |
| cloud.browser-use.com | Cloud browser execution for checkout flows | https://docs.browser-use.com/cloud/quickstart |

---

## Known Constraints

- AgentCard supports **US-based merchants only**
- AgentCard card value range: **$5–$200** (multiples of $5)
- Automated refunds capped at **$5 or 25% of card value** (whichever is greater)
- `agentcard signup` requires magic link click via email (one-time, at setup)
- Each top-up creates a new card with a new card number

---

## Pre-Purchase Checklist

Before any purchase attempt, the agent verifies:
1. `agentcard balance <id>` — sufficient funds
2. `payment-guard` whitelist check — merchant is approved
3. `payment-guard` threshold check — amount is within auto-approve limit
4. Shipping address collected (physical goods only)
5. Merchant browser profile loaded (login session ready)
