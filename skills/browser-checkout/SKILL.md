---
name: browser-checkout
description: "Use this skill to execute the actual purchase after payment-guard has approved the transaction. Handles context gathering, product search, price comparison, and checkout form submission via cloud browser automation."
license: MIT
metadata:
  author: xiaolu7586
  version: "0.2.0"
  homepage: "https://cloud.browser-use.com"
---

# Browser Checkout — Cloud Browser Execution Layer

Executes browser-based shopping workflows using browser-use.com cloud automation.

> Only call this skill AFTER payment-guard has confirmed the transaction is approved.

---

## Phase 0: Context Gathering (Before Every Purchase)

Context is collected lazily — only when the current purchase scenario requires it.
Once collected, context is saved to USER.md and re-confirmed on subsequent uses.

### 0a. Shipping Address (physical goods only)

Skip this step entirely for SaaS, subscriptions, credits, or digital purchases.

**Check USER.md `shipping_name` field:**

```
Case A — Field is empty:
  → "This order will be shipped to you. What name and address should I use?"
  → Collect: name, line1, line2 (optional), city, state, zip, country
  → Save all fields to USER.md shipping section
  → Proceed

Case B — Field is populated:
  → "Shipping to: [name], [line1], [city], [state] [zip] — is this correct?"
  → If confirmed → proceed
  → If user provides new address → update USER.md → proceed
  → Never skip this re-confirmation step for physical goods
```

### 0b. Merchant Account / Browser Profile

Required for any merchant that requires login (Amazon, Vercel, Notion, etc.).

**Check USER.md `merchant_profiles.<merchant>` field:**

```
Case A — No profile saved:
  → "To complete this purchase, I need to log in to [merchant] on your behalf."
  → "I will open a secure browser session. Please log in once, and I will save
     the session so you never need to do this again."
  → Create browser-use profile for this merchant
  → User completes login in the browser session
  → Save returned Profile ID to USER.md merchant_profiles.<merchant>
  → Proceed

Case B — Profile ID saved:
  → "I have a saved session for [merchant]. Shall I use it?"
  → If confirmed → load profile → proceed
  → If session turns out to be expired during checkout → notify user →
     return to Case A flow to re-authenticate
```

### 0c. AgentCard

**Check USER.md `cards` field:**

```
Case A — No cards:
  → Pause purchase
  → "You have no payment card set up. Would you like to set one up now?"
  → Trigger agentcard skill setup flow
  → Return here after card is ready

Case B — One or more cards:
  → Select card with sufficient balance
  → If no card has sufficient balance → notify user → suggest top-up
```

---

## Phase 1: Search & Compare

```python
session = client.sessions.create(
    task=f"Go to {merchant_url}. Search for: {product_description}. "
         f"Find the best match under ${budget}. "
         f"Return: product name, exact price, product URL, availability. "
         f"Do not add to cart yet.",
    model="claude-sonnet-4-6",
    profile_id=merchant_profile_id   # loaded from USER.md
)
result = session.run()
```

Present to user: product name, price, URL. Wait for explicit confirmation before proceeding.

---

## Phase 2: Checkout (after user confirms)

> Retrieve card credentials immediately before use — never cache between sessions.

```python
# Get card credentials (CLI call, parse output)
# agentcard details <card_id>
# Parse: PAN, CVV, expiry from stdout

session = client.sessions.create(
    task=f"""
Using the existing logged-in session, go to {product_url}.
Add the item to cart.
Proceed to checkout.
Fill in shipping details:
  Name: {shipping_name}
  Address: {shipping_line1}, {shipping_line2}
  City: {shipping_city}, {shipping_state} {shipping_zip}
  Country: {shipping_country}
STOP before submitting payment. Return the final total shown
(including tax and shipping) so it can be confirmed.
""",
    model="claude-sonnet-4-6",
    profile_id=merchant_profile_id
)
final_price = session.run()
```

**Final price confirmation (mandatory):**
```
→ "Final total including tax and shipping: $[final_price]
   This may differ from the listed price. Proceed?"
→ Re-run payment-guard threshold check against final_price
→ Only if user confirms → submit payment
```

```python
# Payment submission (separate step after final price confirmed)
session = client.sessions.create(
    task=f"""
Fill in payment details:
  Card number: {pan}
  Expiry: {expiry}
  CVV: {cvv}
Submit the order.
Return: order confirmation number and final amount charged.
""",
    model="claude-sonnet-4-6",
    profile_id=merchant_profile_id
)
order_result = session.run()

# Discard card values immediately
pan = cvv = expiry = None
```

---

## Phase 3: Post-Purchase

```bash
agentcard track-purchase \
  --merchant "<merchant>" \
  --amount "<final_amount>" \
  --status "success|failed" \
  --note "<order_id>"
```

- Append to USER.md Purchase Log
- Report to user: order confirmation, amount charged, remaining card balance
- **Balance warning check:** if remaining balance < (2 × approval_threshold) or < $20 (whichever is lower), notify: "Your card balance is running low ($X remaining). Consider topping up before your next purchase."

---

## Failure Handling

| Failure | Action |
|---------|--------|
| CAPTCHA encountered | Stop, report to user, run `agentcard support` — do NOT retry silently |
| Card declined | Check balance, report exact reason if available |
| Item out of stock | Report, offer to search alternatives |
| Price changed between search and checkout | Surface new price, re-run payment-guard check |
| Browser profile session expired | Notify user, re-run Phase 0b Case A to re-authenticate |
| Checkout timeout | Report, do NOT retry without explicit user instruction |
| Final price exceeds threshold | Pause, escalate to user — even if original price was within threshold |

---

## Security Rules

- Card credentials are fetched via CLI immediately before the payment step.
- Card values (PAN, CVV, expiry) are nulled out immediately after session completes.
- Never include card values in conversation messages or log entries.
- browser-use task strings containing card values must not be stored — use session-scoped variables only.
