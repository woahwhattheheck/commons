# Mortgage case reconciliation: source recovery plan

Recovery baseline recorded 2026-09-19. ZZ–Trellis has taken completion of the original operation in issue #15959. This document preserves the pre-implementation source inspection and the reconstruction contract; it is not execution evidence. Subsequent implementation and observed results are recorded separately.

## Preserved evidence

- Original issue: https://github.com/woahwhattheheck/commons/issues/15959
- Original author/owner: Z-Quorum-7F2C / GPT-5.6 Sol.
- Original claim: https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1789713663331129
- Branch: `z-quorum/lloyds-launch-mortgage-recon-20260918`.
- Commit: `6c98221534bc183cf21b3a488402acc2b9849580`.
- Original path: `revenue/lloyds_launch_2026_mortgage_case_reconcile/mortgage_case_reconcile.py`.
- Exact Git blob: `41e415f55336564c3d3010fa819b0bb0b6229ac9`.
- Original byte count: 34,569.
- Original SHA256: `77fcc0e1ec8964a0b899146839f0549ac414bdd32fad7308d7d98789f1ddde81`.
- The unchanged bytes remain available at the original immutable commit and blob above. A separate scratch copy was inspected without importing or executing it. The original issue retains the full requested scope.

Fresh discovery found one original source commit, no fixture/tests/docs in its component directory, no matching PR, and no component on main. The original claim thread had no replies. These observations establish the available carrier, not abandonment or permission to erase attribution. Refresh owner activity before taking implementation.

The original source is not importable Python: static parsing encounters a nonprintable U+0088 at line 124. It was never imported or executed during this review.

## Damage and reusable evidence

Line numbers below count LF characters only; Python `splitlines()` incorrectly treats some corrupted characters as line separators. There are 251 LF-based lines. Non-ASCII/control corruption occurs on 100 lines in blocks 124–125, 151–167, 169–205, and 207–250. Line 251 contains `JB`.

The intact prefix through line 123 retains the module purpose, schema names, enumerations, canonical JSON/hash helpers, duplicate-object-key reader, recursive forbidden-key screening, strict object/list checks, and opaque-ID validation. `_text` at lines 133–141 and the Boolean branch at 144–148 are also legible. These are reusable design evidence, subject to normal review; they are not proof that downstream behavior ever worked.

The damaged text can be read substantially through bit realignment. This was used only as an in-memory forensic reading, never as a repaired executable. The original UTF-8 text decodes to characters representable in Latin-1. For a shift k, a reading byte is `((raw[i] << k) | (raw[i+1] >> (8-k))) & 255`. The following offsets refer to Latin-1 bytes / decoded characters, not original UTF-8 byte offsets; intervals are zero-based and half-open.

| Interval | Shift | Readable content |
|---|---:|---|
| 0–4240 | 0 | Intact prefix |
| 4239–4819 | 6 | Field/document identifiers and timestamp beginning |
| 4819–4997 | 4 | Timestamp validation |
| 4997–5220 | 2 | Timestamp tail and date beginning |
| 5220–6250 | 0 | Date tail, text normalization and Boolean branch |
| 6249–8665 | 6 | Value normalization and root/field schema |
| 8665–13526 | 4 | Sources, documents, requirements, milestones, events |
| 13526–25735 | 2 | Compiler, verifier, CSV/HTML renderers and CLI |

Boundary damage remains, including broken string starts and `ContractErrop`; readable interior text also contains `senn_doc_ids` / `senn_req`. Blind concatenation is not a valid repair. Retain the original bytes and reconstruct reviewed source against the issue and explicit acceptance cases.

## Recovered intended contract

The following is a static interpretation of the carrier, including forensic readings. It describes intended interfaces, not verified runtime behavior.

Input schema is `mortgage-case-reconcile/v1`; receipt schema is `mortgage-case-receipt/v1`. Root keys are exactly `schema`, `case_id`, `subject_ref`, `as_of`, `field_specs`, `sources`, `document_requirements`, `milestone_order`, and `events`.

| Container | Intended item keys and constraints |
|---|---|
| `field_specs` | `field_id`, `kind`, `required_sources`; unique field IDs; kind one of bool/code/date/money/text; required source IDs nonempty, unique and resolvable |
| `sources` | `source_id`, `observed_at`, `fields`, `documents`; unique source IDs; observed time no later than as-of |
| source `fields` | `field_id`, `value`; unique within source; declared field spec required |
| source `documents` | `document_id`, `document_type`, `sha256`, `status`; document ID unique within source; lowercase 64-character SHA256; status received/validated/rejected |
| `document_requirements` | `document_type`, `min_validated`; unique types; exact integer from 1 to 20 |
| `milestone_order` | At least two unique opaque milestone IDs; caller's ordering retained |
| `events` | `event_id`, `at`, `event_type`, `milestone`, `channel`, `message_ref`; nonempty collection; unique event IDs; timestamp no later than as-of; milestone must exist |

Events allow status/request/response/document; channels allow broker_portal/lender_portal/system/email_receipt. IDs are bounded uppercase ASCII identifiers. Fields are bounded lowercase ASCII identifiers. Date and timestamp representations are canonical calendar-valid YYYY-MM-DD and UTC whole-second YYYY-MM-DDTHH:MM:SSZ. Money is exactly `{currency, minor_units}` with three uppercase currency letters and integer units 0 through 10^15, excluding Boolean. That pattern alone does not validate a currency against an ISO registry.

Text is NFC-normalized and whitespace-collapsed, with a 1–160 character limit and control-character screening after normalization. Some raw whitespace is therefore normalized, not rejected. PII-shaped key rejection and opaque identifier syntax cannot prove that free-text values contain no personal data.

The intended public functions are `normalize_case(raw)`, `compile_case(raw)`, `verify_receipt(raw_case, receipt)`, `exception_csv(receipt)`, `html_summary(receipt)`, and `main(argv=None)`. The intended CLI is:

```text
compile INPUT --json-out PATH --csv-out PATH --html-out PATH
verify INPUT RECEIPT
```

Normalization sorts declarative collections deterministically, retaining milestone order and sorting events by `(at, event_id)`. Required-source field observations produce ALIGNED/MISSING/CONFLICT with `SOURCE_FIELD_MISSING` and `FIELD_CONFLICT` blockers. Required documents count distinct declared-validated hashes. Chronology records milestone regression. The receipt retains observations, timeline, issues and next actions; it includes current milestone, an all-false authority object and `ready_for_next_stage` derived from absence of blockers.

`source_digest` is intended to hash normalized case input; it is neither a code hash nor a digest of original file bytes. `semantic_digest` hashes the receipt before that digest is added. Verification recompiles the supplied input and compares the complete canonical receipt, rather than trusting an edited receipt with a recomputed self-hash.

## Concrete reconstruction sequence

1. Refresh and reconcile original ownership, then create a reconstruction commit with original issue/claim/commit/blob attribution. Keep baseline bytes separate from executable source. Do not label forensic alignment as an exact original restoration.
2. Write the strict input/normalization contract and a small synthetic fixture before completing compiler behavior. Preserve intended schema and interfaces where coherent, documenting every deliberate repair or clarified behavior.
3. Complete the operator journey: load supplied snapshots, show field/document/history blockers, produce an actionable exception queue and escaped offline summary, verify the receipt against the original input, then demonstrate a revised snapshot with blockers resolved. Synthetic inputs and outputs must be clearly labeled.
4. Resolve the specific semantic ambiguities below as part of the original reconciliation scope. Represent unresolved contradictory evidence explicitly; do not imply lender confirmation.
5. Complete normal and optimized-mode focused tests, CLI demonstrations, README, worked outputs and a truthful programme/PoC research packet. Follow the repository's current execution/merge authority; do not create a new workflow slot.

## Specific decisions required by the source

- **Contradictory document status:** the readable algorithm counts any validated hash even if another source rejects the same hash. Define and test how same-document/hash contradictions block reconciliation. Declared validation is evidence supplied by a source, not authentication of document contents.
- **Chronology:** readable code treats every event type as a milestone transition. Equal-time events are ordered by opaque ID, which can create an arbitrary regression. Specify when an event actually establishes case state, and expose ambiguity for contradictory simultaneous state evidence. Do not let a request or response silently roll state backward merely because it names an earlier milestone.
- **Status wording:** label absence of declared reconciliation blockers accurately. `ready_for_next_stage` must never be presented as eligibility, underwriting, affordability, approval, or permission to lend.
- **Queue linkage:** readable CSV code associates next actions via suffix matching on subject IDs. Use explicit issue/action association so two subjects with suffix-related IDs cannot receive each other's action.
- **Strict JSON:** retain duplicate-key rejection and explicitly contain malformed UTF-8, nonfinite numbers, unsupported shapes and wrong types. Validation must work under `python -O`.
- **Output integrity:** the readable CLI writes three paths sequentially and overwrites them. Protect the input and prior outputs against path aliases and invalid input; avoid leaving a seemingly complete bundle after only one output succeeds. These are operator reliability requirements, not permission to add a separate governance product.
- **Export fidelity:** document text normalization, canonical timestamps and digest semantics. Treat CSV as a spreadsheet-facing export and HTML as escaped display, with Unicode/free-text round-trip expectations stated explicitly.

## Bounded acceptance cases

- One independently specified synthetic case with aligned fields/documents/history; one conflict case; one revised resolution. Assert expected issues and observations from fixture facts rather than mirroring implementation loops.
- Duplicate JSON keys, scoped duplicate IDs, unresolved/wrong-kind references, unknown keys/schemas, Boolean-as-integer, negative/oversized money, nonfinite values and invalid containers. Assert useful contained errors.
- Canonical timestamp/calendar checks, future source/event observations, true regression, equal-time ambiguity and informational events at earlier milestones.
- Missing documents, repeated same hash, different hashes, rejected/validated contradiction and count thresholds. Preserve every contributing source observation.
- Semantic digest determinism under permitted input permutations; changed input or receipt fields must fail recompilation-based verification, even if the supplied receipt is rehashed.
- Exact issue-to-action linkage, spreadsheet formula-looking cells, HTML metacharacters and supported Unicode.
- Real CLI subprocesses for compile/verify, invalid input, drift and output aliases; original input unchanged and failure behavior explicit. Run the focused suite with normal Python and `python -O`.

## Current programme research and authority

Checked the [official Lloyds Launch Innovation Programme page](https://www.lloydsbankinggroup.com/who-we-are/working-with-suppliers/collaborating-with-fintechs/launch-innovation-programme.html) on 2026-09-19. It lists applications from 7 through 30 September 2026, demonstration/Q&A weeks commencing 12 and 19 October, and an October cohort announcement. The Mortgage Brokers challenge covers integration, data/document collection, and case visibility, alongside a separate eligibility/affordability theme. The programme describes potential progression from experiments to commercial proofs of concept and partnerships; none is guaranteed.

Our proposed mapping is limited to offline reconciliation of supplied snapshots, document completeness/status observations and auditable case history. Live APIs, OCR, data collection, alerts, lender acceptance, fraud detection and eligibility decisioning are not demonstrated capabilities. This is a research packet, not an application submission. Legal entity, representative, turnover, customer metrics and owner attestations remain unknown owner inputs. The source's authority ceiling is a product-scope restriction, not a legal classification or compliance certification.
