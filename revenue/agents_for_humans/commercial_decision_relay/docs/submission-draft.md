# Devpost submission draft

## Commercial Decision Relay

Commercial teams lose time repeatedly checking offer threads, matching versions, identifying exact acceptances, and separating routine outcomes from decisions that actually need a human. A naive AI assistant can make this worse by confidently turning ambiguous language into "closed" status.

Commercial Decision Relay is a Strands Agents SDK professional agent that handles that repetitive evidence loop end to end. Strands orchestrates custom evidence tools and lifecycle audit hooks. A deterministic engine binds responses to the current offer version, counterparty, thread, terms, amount, time window, human review attestation, and source digest. The agent stays quiet for routine waiting/decline states and surfaces only exact-acceptance-ready, counteroffer, clarification, expiry, late-response, or evidence-conflict decision cards.

The central design choice is a hard authority boundary: `HUMAN_CLOSING_READY` is not signer or legal authority. The project contains no capability to sign, execute contracts, create checkout/invoices, charge, begin fulfillment, or recognize revenue. Receipt verification requires both trusted source evidence and an independently supplied digest; a self-digest is never treated as authenticity.

### Built with
- Strands Agents SDK (Python)
- Custom Strands tools
- Strands Before/AfterToolCall lifecycle hooks
- Optional Amazon Bedrock default provider or OpenAI provider
- Standard-library deterministic evidence engine and local decision dashboard

### What judges can reproduce free
1. Install dependencies.
2. Run the deterministic fixture/tests.
3. Open the local decision dashboard.
4. Configure a supported model provider to exercise the Strands orchestration path.

### Prior work/open-source disclosure
This project was created during the Aug. 10–Sep. 14, 2026 submission period. Commercial-evidence patterns were informed by contemporaneous work in the `woahwhattheheck/commons` repository, including a commercial acceptance evidence bridge created during the same period. If any source is incorporated verbatim, the exact source commit/file will be disclosed in the final submission. The Strands-native orchestration, tool layer, audit hooks, product dashboard, fixtures, documentation, and hackathon packaging are new work for this project.
