# Procurement loss/debrief remediation loop

`tools.procurement_loss_remediation` is the second half of the procurement learning loop. It **composes** the already-landed `tools.procurement_win_loss` source-bound outcome receipt; it does not reread private mail, contact buyers, request debriefs, or infer a causal story from free text.

The trust split is deliberate:

- the source outcome receipt proves `WON | LOST | NO_DECISION | UNKNOWN`, its exact redacted rationale statements, evidence identities/digests, chronology, currentness state, and all-false external authority;
- the remediation receipt projects those source facts explicitly (`evidence_id`, kind, digest, observed-at, currentness, decision signal, mapped outcome) and also binds the complete upstream receipt digest;
- `buyer_reason_mappings` are operator taxonomy classifications bound to an **exact source-attributed rationale statement** by evidence id + source digest;
- `internal_hypotheses` are a physically separate namespace. Each evidence basis row must match an independently verified source evidence id + digest + observed-at and must resolve to `CURRENT` terminal evidence; stale, withdrawn, pending/unknown, reminted, or timestamp-shifted evidence cannot authorize an actionable hypothesis gap;
- each versioned remediation gap names either a buyer-reason id or a valid internal-hypothesis id. A gap cannot silently cross namespaces.

This is how a real `NOT_SELECTED` response can improve targeting without turning “we lost” into an invented explanation for why.

## States

The compiler emits exactly one conservative state:

- `ACTIONABLE_GAPS` — source is coherent, every source-stated rationale statement is taxonomy-bound, every hypothesis has a current terminal source-bound evidence basis, every gap has a valid basis, and at least one remediation gap exists;
- `NO_ACTIONABLE_GAP` — source is coherent and no versioned remediation gap is supplied;
- `HOLD_SOURCE` — the underlying win/loss receipt is `UNKNOWN` or carries source-level chronology/conflict holds;
- `HOLD_CONTRADICTION` — a buyer-reason digest/evidence binding, hypothesis source/currentness binding, or remediation basis contradicts the verified source packet;
- `HOLD_UNATTRIBUTED_REASON` — the verified outcome receipt contains one or more buyer-stated rationale statements that have not yet been explicitly taxonomy-bound.

`HOLD_UNATTRIBUTED_REASON` is intentional: the compiler will not silently classify a sentence because it happens to contain words such as “price,” “schedule,” or “experience.”

## Buyer reason taxonomy

The current bounded taxonomy is:

`QUALIFICATION_EVIDENCE`, `SCOPE_TECHNICAL_FIT`, `PRICE_BASIS`, `PROCESS_COMPLIANCE`, `SCHEDULE_CAPACITY`, `PARTNER_WORKSHARE`, `OTHER_STATED`.

The source statement remains verbatim redacted evidence from the verified win/loss receipt. The category is an **operator classification**, not a claim that the buyer used that label.

## Internal hypotheses

Internal hypotheses require one or more `evidence_basis` rows containing the exact `evidence_id`, `source_digest_sha256`, and `observed_at` from the verified source receipt. The compiler then resolves currentness and outcome from that trusted receipt; callers do not self-declare them. A basis is valid only when every referenced fact is still `CURRENT` and maps to a terminal outcome. Hypotheses may capture ideas worth testing—such as whether short pursuit runway correlates with weak qualification evidence—but they never promote into buyer-stated rationale and never authorize a causal claim about a buyer decision.

## Remediation rails

Versioned gaps are routed to one existing internal seam: `SOLICITATION_EVIDENCE`, `RESPONSE_MODULE`, `OPPORTUNITY_QUALIFICATION`, `PARTNER_WORKSHARE`, `DELIVERY_PROCESS`, or `PRICING_BASIS`. Gap kinds are bounded to `CAPABILITY | EVIDENCE | PROCESS | PARTNER | SCHEDULE | PRICING | OTHER`.

## CLI

```bash
python3 -m tools.procurement_loss_remediation compile plan.json > receipt.json
python3 -m tools.procurement_loss_remediation verify plan.json receipt.json
```

Both commands use the strict JSON reader from the source win/loss product, including duplicate-key, non-finite-number, UTF-8, and size rejection.

## Privacy and authority

Repository fixtures are synthetic/reference-only. Hypothesis and remediation action text reject obvious email, URL, and phone-like strings, including common slash/colon phone separators. Buyer rationale inherits the win/loss product's redaction/contact screening.

Every remediation receipt hard-codes false authority for buyer contact, debrief request, outbound, provider mutation, contract, payment, cash, revenue, and buyer-causal inference. This tool produces an internal learning backlog only.

## Tests and CI

`test_procurement_loss_remediation.py` covers source-bound buyer reasons, explicit source identity/currentness projection, stale/pending/reminted hypothesis evidence, unknown-rationale hypotheses, source holds, missing taxonomy binding, namespace-crossing gaps, contact-shaped rejection, bool-as-int rejection, deterministic ordering, source-receipt tamper, and receipt tamper.

`test_procurement_loss_remediation_optimized.py` launches an actual `python -O` child without relying on stripped `assert` statements. The dedicated `.github/workflows/procurement-loss-remediation.yml` is path-scoped to this product and both root test bridges, uses concurrency cancellation, and runs the suite under Python 3.11 and 3.13 in both normal and optimized interpreters.

Run directly:

```bash
python3 -m unittest -v test_procurement_loss_remediation.py test_procurement_loss_remediation_optimized.py
python3 -O -m unittest -v test_procurement_loss_remediation.py test_procurement_loss_remediation_optimized.py
```
