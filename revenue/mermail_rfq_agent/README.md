# Mermail RFQ Agent — evidence-bound vendor quote workflow

A companion skill for the Superteam **Build and Demo a Mermail Agent Skill** bounty. It turns Mermail into a procurement/RFQ control plane without giving the agent purchasing or payment authority.

## Why this use case

Procurement is fundamentally an email-identity and thread-integrity problem: multiple vendors reply with changing prices, lead times, MOQs, shipping/tax caveats, and amendments. A useful agent must keep those facts attached to the right sender and thread and must not turn “cheapest” into “authorized to buy.”

This package combines:

- a Mermail companion skill that routes to the platform's existing inbox/composition tools;
- a deterministic, network-free quote ledger with append-only amendment handling;
- hostile tests for spoofed sender, thread drift, quote-id collisions, version regression, missing price, expiry, MOQ mismatch, and cross-currency ranking;
- a synthetic demo that performs no live email, wallet, purchase, or payment action.

## Run it

Requires Node.js 22+.

```bash
npm test
npm run demo
```

## Demo story

1. Buyer freezes an RFQ for 1,000 FKM-75 precision gaskets.
2. The skill sends isolated solicitations only after exact preview and fresh approval.
3. Mermail replies are read through bounded inbox/thread tools and treated as untrusted evidence.
4. The ledger binds each quote to the allowlisted sender + original thread, preserves quote versions, and reports missing terms.
5. Same-currency explicit unit prices can be ranked for review, but output always states `awardAuthorized: false` and `paymentAuthorized: false`.

The checked-in demo starts at step 4 with synthetic Mermail identities, so validation never creates external side effects.

## Layout

- `skill/SKILL.md` — agent workflow and authority boundary
- `skill/agents/openai.yaml` — OpenAI/Codex skill metadata + Mermail MCP dependency
- `skill/references/` — tool routing and security contracts
- `src/quote-ledger.mjs` — deterministic commercial evidence ledger
- `test/quote-ledger.test.mjs` — hostile regression suite
- `demo/` — synthetic end-to-end comparison fixture

## Submission notes

This is intentionally a **community companion** rather than a new official tool-owning domain: it recombines the official Mermail inbox and composition capabilities while respecting their existing ownership and approval rules. A separate upstream proposal can be used if Mermail maintainers want to graduate the workflow into the official skill catalog.
