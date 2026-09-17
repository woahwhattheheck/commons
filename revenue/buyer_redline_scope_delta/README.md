# Buyer Redline → Paid Scope Delta

Deterministic owner-review tooling for comparing a **structured, human-reviewed baseline offer/SOW** to a **structured counterdraft** without silently absorbing expanded work.

This is deliberately *not* a contract parser and not legal advice. It never signs, accepts, sends, changes a live price/payment rail, or recognizes revenue. Raw contract prose should first be extracted/reviewed by a human into the narrow JSON clause schema used here.

## Decisions

- `ACCEPTABLE_AS_WRITTEN` — structured clause facts are unchanged and exact baseline binding holds.
- `OWNER_REVIEW` — a material non-legal delta needs owner judgment.
- `REQUOTE_REQUIRED` — price/currency/payment timing or obvious cost/effort pressure changed.
- `LEGAL_REVIEW_REQUIRED` — IP, liability/warranty, or termination changed.
- `HOLD_CONTRADICTION` — source generation/binding or chronology conflicts; do not negotiate from this packet.

The counterdraft must name the exact `baseline_semantic_sha256`. Same-generation changed semantics and counterdraft chronology before the baseline fail closed.

## Clause identity

Each clause has an `id`, `category`, and `metric`. The **semantic identity is the triple `(id, category, metric)`**. Reusing an existing clause ID while changing category or metric is evaluated as removal of the old semantic clause plus addition of the new one. That prevents a counterdraft from relabeling an assumption/dependency as scope (or vice versa) to evade the applicable commercial rule.

## Hard gates

- duplicate JSON keys rejected;
- strict UTF-8, NFC strings, no surrogate text;
- floats/non-finite numbers rejected;
- money uses integer minor units and bool-as-int is rejected;
- `net_days` is a non-negative integer; `duration_days` is a positive integer;
- duplicate clause IDs and contradictory singleton commercial metrics rejected;
- raw and semantic SHA-256 identities retained;
- exact baseline semantic binding required;
- chronology compares parsed UTC instants rather than timestamp spellings;
- packet verification **recompiles from the exact baseline + counter source bytes** and requires exact packet equality;
- a caller cannot change status/deltas and regain validity by recomputing the packet's self-hash;
- all mutation/acceptance/legal/payment/revenue authority flags stay false.

The packet schema is `buyer-redline-scope-delta/v2`.

## CLI

```bash
python -m revenue.buyer_redline_scope_delta.cli compile baseline.json counter.json packet.json --markdown owner.md
python -m revenue.buyer_redline_scope_delta.cli verify baseline.json counter.json packet.json
```

CLI inputs must be bounded regular files (2 MiB max each). Outputs are create-exclusive: the CLI refuses to overwrite an existing packet or Markdown path.

## Verification boundary

The SHA-256 stored in the packet is a deterministic receipt, not an authentication signature. Trust comes from retaining the exact human-reviewed baseline/counter bytes and replaying the compiler against them. `verify` therefore requires both source files and refuses a packet that is merely internally self-consistent.

## Authority ceiling

This package only emits owner-review decision support. It does not parse raw contracts, provide legal advice, accept or sign terms, contact a buyer/prime, mutate price or payment rails, recognize revenue, or prove that any counterparty has accepted a commercial position.
