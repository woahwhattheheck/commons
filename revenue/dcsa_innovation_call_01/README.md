# DCSA Innovation Call #01 readiness carrier

Isolated, zero-dependency donor implementation for `DCSAInnovationCall01` / `HS0021-26-CSO-DCSA`.

This package is a **mechanical evidence/readiness compiler**, not a security-clearance authority, legal opinion, Government representation, submission agent, award record, or payment/revenue record. `DIRECT_READY` means only that the configured source, architecture, and evidence classes were locally byte-bound and current under the process-owned clock. An authorized owner must independently verify clearance truth, proposal authority, source generation, and all representations before submission.

## Why it exists

The opportunity has a short concept-paper window and a material direct-prime gate. The carrier is designed to prevent two expensive failure modes:

1. writing a full direct proposal when required security evidence is absent; and
2. letting an editable JSON timestamp / source checkbox / "we have clearance" boolean turn an ineligible packet green.

It yields exactly one operational state:

- `DIRECT_READY` — mechanical packet has current source bindings, required architecture domains, and byte-bound direct-readiness evidence classes;
- `TEAMING_REQUIRED` — source/architecture are mechanically usable but direct-readiness evidence is absent, so effort should shift to a cleared-prime workshare; or
- `HOLD` — deadline/source/evidence/architecture integrity is not safe enough to proceed.

## Security / authority properties

- Production time comes from the process; a caller-provided `trusted_now` is ignored.
- Source and eligibility evidence are local regular files read through one retained descriptor, bounded by size and SHA-256 checked; `O_NOFOLLOW` is used where the OS supports it.
- Files are `fstat()` checked before/after reading and fail closed on identity/size/mtime drift.
- Required source kinds are explicit; duplicate kinds hold.
- Source freshness and future timestamps hold.
- Optional `current_addendum_generation` requires that exact addendum generation to be byte-bound.
- Expired/future/non-evidenced eligibility records hold.
- Teaming ranking deliberately refuses to score a self-asserted facility-clearance signal; every candidate remains `OWNER_VERIFY` for FCL. A separate `incumbent_overlap_risk` signal penalizes technically strong incumbents whose scope may compete with, rather than complement, the proposed workshare.
- Output authority ceiling is explicit and all external-authority bits remain false.
- CLI writes outputs create-exclusive (`O_EXCL`) so a later run does not silently overwrite an earlier receipt.

## Required source kinds

- `innovation_call`
- `general_solicitation`
- `concept_paper_template`

Addenda may be represented as `addendum:<generation>` and bound through `current_addendum_generation`.

## Direct-readiness evidence classes

- `facility_clearance_top_secret`
- `personnel_us_citizenship`
- `personnel_interim_secret_or_higher`
- `privileged_user_t5_or_allowed_interim` when privileged users are in scope

The carrier checks that an evidence file exists, is stable while read, matches the declared digest, is not expired, and is marked `evidenced`. It does **not** authenticate the issuer or certify the security fact.

## Architecture domains

- unified access shell
- identity-provider adapter
- attribute-policy decision
- API/event integration
- legacy-continuity canary
- observability/rollback

The generated acceptance matrix covers foundation, integration, GAT/UAT/regression/integration/performance/accessibility/security validation, issue disposition, ATO evidence indexing, sustainment handoff, and production-readiness ROM.

## CLI

```bash
python revenue/dcsa_innovation_call_01/cli.py packet.json --out ./receipt-dir
```

Exit `0` for `DIRECT_READY` or `TEAMING_REQUIRED`; exit `2` for `HOLD` or malformed inputs. Outputs:

- `readiness_receipt.json`
- `concept_scaffold.md`

The scaffold is deliberately bounded: it explains the architecture and acceptance approach, lists holds, and never invents clearance, past performance, Government approval, contract, payment, or revenue.

## Tests

```bash
python -m unittest discover -s revenue/dcsa_innovation_call_01/tests -v
python -O -m unittest discover -s revenue/dcsa_innovation_call_01/tests -v
```

Hostiles cover deadline backdating, stale sources, missing architecture, hash drift, symlinks, expired evidence, missing addendum generation, deterministic receipts, false clearance ranking, incumbent-overlap commercial ranking, and authority-ceiling language.
