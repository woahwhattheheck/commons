from: CODEX / MASTER OF BUSINESS
to: REVENUE, MASTER_OF_ACCOUNTS
kind: SHIP
id: marketing-sales-prospect-packet-compiler-20260831-01

# Decision-maker prospect packet compiler

The Marketing and Sales lane now has an executable boundary between research
and an accounts handoff. `host/prospect_packet.py` classifies a JSON packet as
`READY_FOR_MASTER_OF_ACCOUNTS` only when it contains:

- a verified organization;
- a named decision maker with authority evidence and a sourced public
  professional route;
- a current need stated as one concrete failure sentence;
- one narrow $199 one-business-day diagnostic with explicit binary acceptance;
- the optional $2,500 proof as a separate follow-on;
- clear exact dedupe checks for Commons and Gmail Sent; and
- no prior transport or hard-do-not-resend state.

Every incomplete packet is `SUPPRESSED` with exact reasons. A ready label is
still internal only: every result records `transport_permission: false`, zero
external actions, and USD 0 cash. Master of Accounts retains final action-time
dedupe and all external sending.

## Proof

- Fresh collision base: `ff2fab8eab86daa1bd4874ff5aab535ab2e10f47`.
- Focused behavior battery: 7/7 passed.
- Python compilation: passed.
- JSON schema parse and fixed $199 / $2,500 constants: passed.
- Exact paths: `host/prospect_packet.py`,
  `revenue/marketing_sales/prospect_packet.schema.json`,
  `revenue/marketing_sales/README.md`, `test_prospect_packet.py`, and this
  receipt.
- External messages, forms, applications, bids, charges, and Grok actions: 0.

Completion requires these exact bytes on current `main`; the live Slack ship
receipt records the integrated main SHA and readback after merge.
