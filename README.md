# Payment Assistant

An autonomous payment agent that searches, compares, and completes purchases on your behalf — within the merchants and budget rules you define.

Powered by [AgentCard](https://agentcard.ai) virtual Visa and [browser-use](https://cloud.browser-use.com) cloud browser automation.

---

## What It Does

- **Set up your payment card** — create and fund a prepaid virtual Visa card through conversation, no external dashboard needed
- **Shop within your rules** — define which merchants you trust and set a spending threshold; the agent checks both before every purchase
- **Search and compare** — finds the best match for what you want before asking you to confirm
- **Checkout automatically** — fills shipping, payment, and submits the order once you approve
- **Track your spending** — logs every transaction and shows your remaining card balance after each purchase
- **Top up when needed** — request a new card top-up anytime; the agent guides you through in under a minute

---

## Supported Scenarios

### Online Shopping
Purchase physical products from major retailers. The agent handles search, price comparison, shipping details, and checkout.

### SaaS Credits & Top-ups
One-click top-ups for AI tools and developer platforms — API credits, usage quota, and pay-as-you-go services.

> Examples: OpenAI, Anthropic, Vercel, Cursor, GitHub Copilot

### Subscriptions
Set up new subscriptions or annual plan payments. The agent handles the checkout and saves your session for future use.

> Examples: Notion, Linear, Spotify, Netflix, Google Workspace

### Event Tickets
Purchase tickets from major ticketing platforms — the agent searches by event, selects your preferred seats, and completes checkout.

---

## How Payment Works

Payment is handled through **AgentCard** — a prepaid virtual Visa card created specifically for agent use:

- You fund the card in any amount ($5–$200) via a secure Stripe checkout link
- The agent uses the card to pay at checkout — you never need to share your real credit card
- Spending limits are set at the card level; the agent adds a second layer of rules on top
- Card credentials are never stored or repeated in conversation — retrieved only at the moment of form submission

---

## Budget Controls

| Control | How to set it |
|--------|--------------|
| **Merchant whitelist** | Tell the agent which sites you approve; only those can be used |
| **Approval threshold** | Set a dollar amount — purchases below it are auto-approved, above it require your confirmation |
| **Card balance** | Fund exactly what you want to spend; the card cannot be overdrafted |

Every purchase goes through a pre-flight check before any browser action is taken. If anything is outside your rules, the agent stops and explains.

---

## Your First Purchase

```
You:   Set up my payment card
Agent: What email should I use for your AgentCard account?
You:   your@email.com
Agent: Check your email and click the link, then let me know.
       How much would you like to load? ($5–$200)
You:   $100
Agent: Here is your payment link: [Stripe URL]
       Let me know once you have completed it.
You:   Done
Agent: Your $100 card is ready. What would you like to buy?
```

---

## Skills

| Skill | Role |
|-------|------|
| `agentcard` | Card lifecycle — setup, balance, credentials, refunds, card rotation |
| `payment-guard` | Pre-purchase rule enforcement — whitelist, threshold, scenario classification |
| `browser-checkout` | Execution — search, compare, checkout, post-purchase logging |

---

## Requirements

- `agentcard` CLI — `npm install -g agentcard`
- `browser-use-sdk` — `pip install browser-use-sdk`
- `BROWSER_USE_API_KEY` — from [cloud.browser-use.com](https://cloud.browser-use.com/settings)

---

## License

MIT
