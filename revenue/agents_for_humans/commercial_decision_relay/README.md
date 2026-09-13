# Commercial Decision Relay

**A Strands-powered professional agent that does the repetitive commercial evidence work and interrupts a human only when there is a real decision.**

Built for the AWS **Agents for Humans** hackathon, Professional Agents track.

## The problem

Commercial teams repeatedly check offers, replies, amendments, expiries, and terms. That work is repetitive; the final decision is not. An LLM should not convert fuzzy language into "closed" status.

Commercial Decision Relay separates the two:

- **Strands orchestrates work** through explicit custom tools and lifecycle hooks.
- A **deterministic evidence engine** decides whether normalized, human-reviewed evidence actually matches the current offer.
- Routine `AWAITING_RESPONSE` and `DECLINED` states stay quiet.
- Exact acceptance, counteroffer, clarification, expiry, late response, and evidence conflict become human decision cards.
- The project has **zero signer/legal, contract execution, invoice/checkout, payment, fulfillment, or revenue authority**.

## Architecture

See [docs/architecture.md](docs/architecture.md). The repository includes:

- `src/decision_relay/core.py` — deterministic evidence/receipt engine
- `src/decision_relay/strands_app.py` — Strands agent, five custom tools, hash-only audit hooks
- `src/decision_relay/web_demo.py` — zero-dependency local decision board
- `fixtures/demo-batch.json` — synthetic judge fixture
- `tests/` — hostile custody, replay, time, identity, authority, and verification cases
- `docs/demo-script.md` — <=5 minute demo plan
- `docs/submission-draft.md` — submission narrative + prior-work disclosure

## Quick start: deterministic path

The custody engine and product board do not require a model credential.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v

# Build a deterministic receipt.
decision-relay reconcile \
  --batch fixtures/demo-batch.json \
  --output /tmp/decision-relay-receipt.json

# Copy receipt_sha256 from the receipt and verify it as an independent caller commitment.
decision-relay verify \
  --receipt /tmp/decision-relay-receipt.json \
  --batch fixtures/demo-batch.json \
  --expected-receipt-sha256 <SHA256>

python -m decision_relay.web_demo --batch fixtures/demo-batch.json
# open http://127.0.0.1:8080
```

> `pip install -e .` installs Strands because the hackathon project requires it. For core-only development in a constrained environment, set `PYTHONPATH=src` and run the unit tests directly; `core.py` and `web_demo.py` use only the Python standard library.

## Run the Strands agent

### Amazon Bedrock (default Strands provider)

Configure AWS credentials using the standard Strands/AWS setup, then:

```bash
decision-relay agent --provider bedrock \
  "Process the normalized evidence and show me only decisions that need a human."
```

### OpenAI provider

```bash
pip install -e '.[openai]'
export OPENAI_API_KEY='...'
export DECISION_RELAY_MODEL_ID='gpt-4o-mini'  # optional
decision-relay agent --provider openai
```

Strands supports multiple providers; the provider choice does not change the deterministic receipt semantics.

## Strands implementation

The agent has exactly five business tools:

1. `ingest_batch` — normalize/dedupe evidence; no external side effects.
2. `reconcile_evidence` — create the deterministic decision receipt.
3. `decision_queue` — return only human-interruption states.
4. `explain_blocker` — explain one deterministic series status.
5. `verify_current_receipt` — bind the receipt to independently supplied SHA-256 plus trusted source.

`AuditHooks` subscribes to Strands `BeforeToolCallEvent` and `AfterToolCallEvent`, allowlists those tools, and writes hash-only audit records rather than raw commercial evidence.

## Evidence contract

Input is **normalized evidence**, not raw email prose. A response is commercially exact only if the current offer version, counterparty, thread, currency, amount, terms digest, timing, source digest, and human-review attestation satisfy the contract. Future evidence is quarantined. Exact replay collapses. Conflicting IDs/offer versions fail closed.

A receipt has a deterministic SHA-256, but that self-digest is only integrity. Verification also requires an **out-of-band expected digest and the trusted source batch** and recomputes the receipt.

## Authority contract

The project deliberately has no tools for:

- signer or legal authority
- contract creation/execution
- invoice or checkout creation
- payment or charging
- fulfillment start
- recognized revenue

`HUMAN_CLOSING_READY` means: *reviewed response exactly matches the current offer and a human now has a closing decision.* It does **not** mean the agent closed a deal.

## Hackathon submission checklist

- [x] New Strands-based project created during the submission period
- [x] Public-repo-ready MIT license
- [x] README and install instructions
- [x] Architecture diagram (Mermaid)
- [x] Synthetic free judge fixture
- [x] Demo script <=5 minutes
- [x] Prior-work/open-source disclosure draft
- [ ] Public repository URL
- [ ] AWS Builder ID entered on Devpost
- [ ] Public YouTube/Vimeo demo video
- [ ] Optional live demo deployment
- [ ] Devpost submission before Sep. 14, 2026 5:00pm PDT

No AWS spend is required by this repository itself. If you choose paid AWS services, monitor cost separately.
