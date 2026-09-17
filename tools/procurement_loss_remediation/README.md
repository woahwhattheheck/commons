# Procurement loss/debrief remediation loop

`tools.procurement_loss_remediation` is the second half of the procurement learning loop. It **composes** the already-landed `tools.procurement_win_loss` integrity receipt; it does not reread private mail, contact buyers, request debriefs, or infer a causal story from free text.

The trust split is deliberate:

- the upstream outcome receipt proves structural consistency, exact packet binding, chronology/currentness checks, outcome mapping, and all-false external authority for the caller-retained packet; it does **not** authenticate that caller-supplied source labels or SHA-256 values came from a buyer or provider;
- the remediation receipt projects those retained facts explicitly (`evidence_id`, kind, digest, observed-at, currentness, decision signal, mapped outcome) and binds the complete upstream receipt digest;
- `buyer_reason_mappings` are operator taxonomy classifications bound to an exact caller-retained rationale statement by evidence id + source digest. They are emitted only as `CALLER_RETAINED_STATED_SOURCE_BOUND_NOT_BUYER_AUTHENTICATED` diagnostics and never become buyer-authenticated facts in this product;
- a remediation gap whose basis type is `BUYER_REASON` is therefore fail-closed (`basis_valid=false`, `HOLD_CONTRADICTION`) until a separate authenticated retained/provider buyer-source authority exists. This repository currently supplies no such authority;
- `internal_hypotheses` are a physically separate namespace. Each evidence basis row must match the independently revalidated upstream packet's evidence id + digest + observed-at and must resolve to `CURRENT` terminal evidence. Stale, withdrawn, pending/unknown, reminted, or timestamp-shifted evidence cannot authorize an internal hypothesis gap;
- each versioned remediation gap names either a diagnostic buyer-reason id or a valid internal-hypothesis id. A gap cannot silently cross namespaces.

This allows retained outcome evidence to improve internal experiments without turning “we lost” or a caller-authored `BUYER_NOTICE` label into an invented claim about what a buyer said or why a buyer decided.

## States

The compiler emits exactly one conservative state:

- `ACTIONABLE_GAPS` — source is coherent and at least one versioned gap is supported by a valid **internal-hypothesis** basis. Caller-retained buyer-reason evidence alone cannot produce this state;
- `NO_ACTIONABLE_GAP` — source is coherent and no versioned remediation gap is supplied;
- `HOLD_SOURCE` — the underlying win/loss receipt is `UNKNOWN` or carries source-level chronology/conflict holds;
- `HOLD_CONTRADICTION` — a digest/evidence binding, hypothesis source/currentness binding, remediation basis, or unauthenticated `BUYER_REASON` authorization attempt fails closed;
- `HOLD_UNATTRIBUTED_REASON` — the retained outcome receipt contains one or more stated rationale statements that have not yet been explicitly taxonomy-bound.

`HOLD_UNATTRIBUTED_REASON` is intentional: the compiler will not silently classify a sentence because it happens to contain words such as “price,” “schedule,” or “experience.” Taxonomy binding still does not authenticate who authored that sentence.

## Buyer reason taxonomy

The current bounded taxonomy is:

`QUALIFICATION_EVIDENCE`, `SCOPE_TECHNICAL_FIT`, `PRICE_BASIS`, `PROCESS_COMPLIANCE`, `SCHEDULE_CAPACITY`, `PARTNER_WORKSHARE`, `OTHER_STATED`.

The retained statement is copied from the structurally verified upstream packet. The category is an **operator classification**, not a claim that the buyer used that label. Every emitted mapped reason carries `buyer_source_authenticated=false` until a separate authenticated source authority is deliberately introduced and reviewed.

## Internal hypotheses

Internal hypotheses require one or more `evidence_basis` rows containing the exact `evidence_id`, `source_digest_sha256`, and `observed_at` from the revalidated upstream receipt. The compiler resolves currentness and outcome from that receipt; callers do not self-declare them at this layer. A basis is valid only when every referenced fact is still `CURRENT` and maps to a terminal outcome. Hypotheses may capture ideas worth testing—such as whether short pursuit runway correlates with weak qualification evidence—but they remain `INTERNAL_HYPOTHESIS_NOT_BUYER_FACT` and never authorize a causal claim about a buyer decision.

## Remediation rails

Versioned gaps are routed to one existing internal seam: `SOLICITATION_EVIDENCE`, `RESPONSE_MODULE`, `OPPORTUNITY_QUALIFICATION`, `PARTNER_WORKSHARE`, `DELIVERY_PROCESS`, or `PRICING_BASIS`. Gap kinds are bounded to `CAPABILITY | EVIDENCE | PROCESS | PARTNER | SCHEDULE | PRICING | OTHER`.

## CLI

```bash
python3 -m tools.procurement_loss_remediation compile plan.json > receipt.json
python3 -m tools.procurement_loss_remediation verify plan.json receipt.json
```

Both commands use the strict JSON reader from the source win/loss product, including duplicate-key, non-finite-number, UTF-8, and size rejection, and both route compilation through the same truth-ceiling policy used by the semantic verifier.

## Privacy and authority

Repository fixtures are synthetic/reference-only. Hypothesis and remediation action text reject obvious email, URL, and phone-like strings, including common slash/colon phone separators. Retained rationale text inherits the upstream product's redaction/contact screening, but that screening is not buyer-authentication evidence.

Every remediation receipt hard-codes false authority for buyer contact, debrief request, outbound, provider mutation, contract, payment, cash, revenue, and buyer-causal inference. This tool produces an internal learning backlog only.

## Tests and CI

`test_procurement_loss_remediation.py` covers truth-narrowed caller-retained reason diagnostics, an explicit forged `BUYER_NOTICE` + arbitrary digest + `STATED` rationale predecessor, source identity/currentness projection, stale/pending/reminted hypothesis evidence, unknown-rationale hypotheses, source holds, missing taxonomy binding, namespace-crossing gaps, contact-shaped rejection, bool-as-int rejection, deterministic ordering, source-receipt tamper, and receipt tamper.

`test_procurement_loss_remediation_optimized.py` launches an actual `python -O` child without relying on stripped `assert` statements and repeats the forged buyer-source predecessor. The exact normal/optimized product proof is enrolled in the already-retained `.github/workflows/source-parses.yml` matrix for Python 3.11 and 3.13, avoiding a new active-workflow slot.

Run directly:

```bash
python3 -m unittest -v test_procurement_loss_remediation.py test_procurement_loss_remediation_optimized.py test_procurement_loss_remediation_generation_remint.py
python3 -O -m unittest -v test_procurement_loss_remediation.py test_procurement_loss_remediation_optimized.py test_procurement_loss_remediation_generation_remint.py
```
