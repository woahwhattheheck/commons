# Human-reply → paid-workshare kit

Buyer/partner interest is not acceptance, and a warm reply is not revenue. This package turns a genuine human routing/interest event into a **bounded fixed-fee workshare proposal** while keeping those states separate.

It ships three reusable one-page commercial carriers:

1. **Data Migration + Integration Acceptance** — source→target reconciliation, interface replay/idempotency, UAT/cutover evidence.
2. **Responsible-AI / LLM Evaluation + Governance Evidence** — role/scenario evaluation, deterministic replay, governance evidence mapping.
3. **Operational / Financial Evidence Reconciliation** — read-only closed-period reconciliation, deterministic exception ledger, owner-review pack.

Each pack states a fee band, delivery band, deliverables, acceptance conditions, exclusions, milestones, intake/security gates, and the authority that remains with the buyer/prime.

## Hard commercial boundaries

The compiler accepts only `commercial_state = PROPOSED_NOT_ACCEPTED`. It also requires every evidence flag to remain false:

- buyer accepted
- customer relationship
- signed contract
- invoice issued
- payment settled
- booked revenue
- recognized revenue

If any flag is true, the compiler refuses the record and tells the caller to use a separate evidence-backed workflow.

Every caller-controlled string that is rendered into the buyer-facing proposal is passed through the same commercial-truth boundary, including counterparty/opportunity labels, the one-line scope, and every input-bound row. Rendered text is NFKC-normalized, Unicode control/format/line-separator characters are rejected, and the commercial-claim scanner runs over a punctuation-folded semantic skeleton. This prevents width-compatibility forms or Markdown/punctuation insertion from turning an all-false evidence record into visible unsupported statements such as “buyer accepted,” “award secured,” “payment received,” “invoice issued,” “signed contract,” “booked revenue,” or guaranteed outcomes.

The generated one-pager explicitly says that routing, interest, and silence are not commitments. Any change to scope, price, deadline, currency, source, or acceptance requires a new offer revision rather than silently rolling forward an old price.

## Compile

```bash
python -m revenue.human_reply_workshare_kit revenue/human_reply_workshare_kit/example.synthetic.json
```

Deterministic receipt:

```bash
python -m revenue.human_reply_workshare_kit \
  revenue/human_reply_workshare_kit/example.synthetic.json \
  --format receipt
```

The receipt binds the normalized offer. Receipt rendering revalidates the normalized record, regenerates the buyer-facing Markdown, and recomputes the normalized SHA-256; a caller cannot mint a receipt by constructing a `CompiledOffer` with a forged hash or modified Markdown.

## Test

Focused suite:

```bash
python -m unittest revenue.human_reply_workshare_kit.test_core -v
python -O -m unittest revenue.human_reply_workshare_kit.test_core -v
```

Retained Commons battery bridge:

```bash
python test_human_reply_workshare_kit.py -v
python -O test_human_reply_workshare_kit.py -v
```

The focused suite covers all three packs, price/duration bounds, strict JSON (including duplicate keys and floats), positive commercial-state claim rejection, caller-text claim smuggling on every rendered surface, NFKC/Markdown/control-character predecessors, deterministic receipts, forged compiled-state rejection, milestone ordering, and stale-term warning presence. The root bridge runs the focused suite in both normal and optimized Python so the product is included in the retained root test discovery surface.

## Source packs

- [`packs/data_migration_acceptance.md`](packs/data_migration_acceptance.md)
- [`packs/responsible_ai_evaluation.md`](packs/responsible_ai_evaluation.md)
- [`packs/financial_evidence_reconciliation.md`](packs/financial_evidence_reconciliation.md)

These are buyer-neutral templates. They are not claims about a named customer, award, acceptance, payment, or realized outcome.
