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

## Pre-Purchase Checklist (in execution order)

Before any purchase, the following checks run in this exact sequence:

1. **Card exists** — `payment-guard` Phase 0: `cards` field in USER.md must be non-empty
2. **Whitelist** — `payment-guard` Layer 1: merchant must be on approved list (if enabled)
3. **Threshold** — `payment-guard` Layer 2: amount vs approval threshold
4. **Shipping address** — `browser-checkout` Phase 0a: collected if physical goods
5. **Merchant login** — `browser-checkout` Phase 0b: browser-use profile loaded or created
6. **Card balance** — `browser-checkout` Phase 0c: sufficient funds confirmed via `agentcard balance`
