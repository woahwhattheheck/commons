# Synthetic acceptance plan

This plan is an internal delivery design for a possible specialist ERP workshare. It uses **synthetic or prime-authorized evidence only** until a separate data-access agreement authorizes anything else.

The plan deliberately avoids inventing 2026 RFP requirements. Buyer-specific rules are parameters that must come from the controlling packet and approved prime design.

## Evidence model

Every test receipt should bind:

- opportunity / implementation generation;
- source evidence generation;
- rule/configuration generation;
- fixture or authorized dataset identity;
- operation under test;
- expected result;
- observed result;
- exception code if any;
- verifier version;
- timestamp from execution environment;
- PASS / HOLD / FAIL;
- owner for any HOLD/FAIL.

A later rerun must not be able to overwrite the earlier receipt and pretend the earlier state never existed.

## Track A — conversion completeness and identity

Minimum synthetic cases:

| Case | Input condition | Binary target |
|---|---|---|
| A01 | one valid source row | exactly one target accounting entry |
| A02 | duplicate source transport row / same logical ID | no silent double migration |
| A03 | same ID with conflicting payload | HOLD conflict; never last-write-wins silently |
| A04 | unmapped required field | HOLD with exact field/reason |
| A05 | nullable/optional source field | follows explicit mapping rule only |
| A06 | overlong/truncated candidate value | FAIL/HOLD before silent truncation |
| A07 | invalid date/amount/type | rejected with reason |
| A08 | excluded record | explicit prime-owned exclusion rule + receipt |
| A09 | rerun same generation | idempotent accounting / no second logical record |
| A10 | interrupted batch / unknown outcome | reconcile before replay; no blind duplicate apply |
| A11 | source total vs migrated+excluded+held | exact equality |
| A12 | changed mapping generation | new receipt generation; old result remains reconstructable |

### Release invariant

For each in-scope source generation:

`source_count == migrated_unique + explicitly_excluded + held_unresolved`

and the three output sets are disjoint by logical record identity.

## Track B — approval and segregation of duties

The actual role/threshold matrix is **UNKNOWN until approved authority is retained**. Once supplied, instantiate synthetic actors and transactions.

Minimum cases:

| Case | Condition | Binary target |
|---|---|---|
| B01 | creator attempts self-approval | approved design outcome, explicitly traced |
| B02 | eligible distinct approver | approved design outcome, explicitly traced |
| B03 | ineligible role | deny |
| B04 | inactive user | deny |
| B05 | role removed after creation | current approved rule controls; trace generation |
| B06 | duplicate approval request | exactly-once state transition |
| B07 | cross-department actor | approved boundary enforced |
| B08 | amount just below threshold | exact threshold rule |
| B09 | amount exactly at threshold | exact threshold rule |
| B10 | amount just above threshold | exact threshold rule |
| B11 | permitted override/delegation | reason + authority + actor trace required |
| B12 | malformed/missing actor identity | deny / HOLD, never anonymous approve |
| B13 | audit event missing | FAIL even if business state appears correct |
| B14 | replay old authorization after role change | stale authorization rejected if design requires currentness |

Historical County findings motivate B01/B13 but do not define their 2026 expected outcome. The approved design does.

## Track C — integrations and external-state reliability

For each approved interface:

| Case | Condition | Binary target |
|---|---|---|
| C01 | normal event/file/API transaction | one reconciled target effect |
| C02 | duplicate delivery | no duplicate logical effect |
| C03 | timeout before response / unknown outcome | reconcile before retry |
| C04 | response lost after success | no blind second apply |
| C05 | target rejects invalid payload | explicit failure and no false success receipt |
| C06 | partial batch acceptance | accepted/rejected members separately accounted |
| C07 | out-of-order events | follows explicit ordering/version rule |
| C08 | stale generation | rejected or explicitly migrated per contract |
| C09 | credentials/authorization failure | no degraded unauthenticated path |
| C10 | retry budget exhausted | HOLD/FAIL with owner; no infinite retry |
| C11 | interface contract version drift | fail closed until mapped |
| C12 | reconciliation job sees mismatch | deployment/cutover gate remains HOLD |

## Track D — cutover, rollback and replay

Synthetic tabletop plus approved dry-run evidence:

1. Bind exact source freeze/extract and configuration generations.
2. Prove conversion reconciliation before dependent integrations open.
3. Prove checkpoint ownership and objective evidence.
4. Inject one migration exception, one integration unknown outcome, and one approval-control failure.
5. Verify each injected defect blocks the appropriate downstream readiness state.
6. Exercise rollback criteria and prove what state is reversible vs irreversible.
7. Exercise replay from a known checkpoint and prove idempotent accounting.
8. Run post-cutover reconciliation and preserve every unresolved exception.

### Hard stop conditions

Any of these keeps the specialist binder at HOLD/FAIL:

- unexplained source/target count delta;
- conflicting duplicate identity;
- silent truncation/coercion;
- unknown external-write outcome without reconciliation;
- missing actor/approval audit evidence;
- undocumented interface owner/contract;
- unbound configuration generation;
- missing rollback consequence for a failed checkpoint;
- customer-data use without explicit authorization;
- criterion marked PASS from assertion alone when objective evidence was required.

## Deliverable shape

For a contracted engagement, the acceptance pack should produce both:

- human-readable Markdown/CSV exception and acceptance matrices;
- machine-readable immutable-generation receipts suitable for independent verification.

No receipt is a County acceptance decision. It records TJLabs technical evidence only unless buyer-authoritative acceptance is separately attached by the prime.
