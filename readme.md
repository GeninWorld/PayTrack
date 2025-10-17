# 🚀 Paytrack — Effortless M-Pesa Integration for Developers

**Paytrack** makes M-Pesa integration fast, secure, and developer-friendly.  
Build and ship payments in minutes with clean APIs, signed webhooks, token-scoped keys, and a live wallet you can trust.

---

## ✨ Features

- 💳 **STK Push, C2B, B2C & B2B built-ins**  
  Collect and disburse funds easily through a unified API.

- 🔐 **Signed Webhooks, Idempotency & Replay Protection**  
  Reliable and tamper-proof callbacks with automatic retries.

- 🧾 **Wallet, Transactions & Auto-Payouts**  
  Manage your tenant wallet, view balances, and schedule payouts effortlessly.

- ⚡ **Blazing Fast & Reliable**  
  Low-latency callbacks and high-availability servers.

- 🛡️ **Secure by Design**  
  Token-scoped API keys, IP allow-listing, and full audit logs.

- 🧰 **SDKs & Tools**  
  Type-safe SDKs, Postman collections, and sandbox test mode.

## 💡 Example API Usage

### 🔸 Charge with STK Push

curl -X POST https://pay.geninworld.com/api/payment_request \
  -H "Authorization: Bearer sk_test_***" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "15.00",
    "currency": "KES",
    "request_ref": "unique_request_reference",
    "mpesa_number": "254700000000"
  }'
🔸 Disburse to B2B/B2C Account
bash
Copy code
curl -X POST https://pay.geninworld.com/api/disburse_request \
  -H "Authorization: Bearer sk_test_***" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "12",
    "request_ref": "abcdefesscndjkcd",
    "b2b_account": {
      "paybill_number": "1234",
      "account_number": "456"
    }
  }'
🔸 Query Payment Status
curl -X GET https://pay.geninworld.com/api/payment/<string:request_ref>/status \
  -H "Authorization: Bearer sk_test_***"
🔸 Query Disbursement Status
bash
curl -X GET https://pay.geninworld.com/api/disburse/<string:disbursement_identifier>/status \
  -H "Authorization: Bearer sk_test_***"
💰 Simple Pricing
Plan	Rate	Includes
Standard	1.5% per successful collection	Free test mode, no monthly fees
Settlements & Payouts	Instant	Normal M-Pesa B2C/B2B charges apply

✅ No monthly fees
✅ Free test mode
✅ Instant settlements & payouts

🧑‍💻 Get Started
👉 Start Building
👉 View API Docs

🧾 License
© 2025 Paytrack from Geninworld Limited
All rights reserved.

📞 Contact
For integrations, partnership, or support:
David Githehu
Website: https://rhtr3fc9-3000.uks1.devtunnels.ms/
Phone / WhatsApp: [+254 719 107332]

🌍 Build Africa’s next generation of fintech with Paytrack.