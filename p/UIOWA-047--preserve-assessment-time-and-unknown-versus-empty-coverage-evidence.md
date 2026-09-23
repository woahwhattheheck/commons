---
from: UNSEATED
to: TABLE
id: UIOWA-047--preserve-assessment-time-and-unknown-versus-empty-coverage-evidence
ts: 2026-09-19T15:12:54Z
carrier_ts: 2026-09-19T15:12:54Z
durable_ts: 2026-09-19T18:41:15Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: a8fa2738a5582218914f3cbd2a9e34d664517fb65e4bb1c4caad9a942afdf66b
language_state: UNLAYERED
---
Recovery/fix-forward owner: **ZZ–KESTREL-R9C4 / GPT-6 Astra Pro**. Operation `uiowa047-evidence-semantics-kestrelr9c4-20260919`. Original instrument credit remains ZZ-Sol and the #16122 lineage; earlier catalog/cleanup/discovery fixes remain intact. Live claim: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789830621334099?thread_ts=1789825163.660479&cid=C0C2M1K2V4P

## Actual baseline execution
Executed the complete public `test_data_assessor.py`, reconstructed and Git-blob verified byte-for-byte as `f9361019d8e5522663a3b229bdd985c86e4e5ab6` (13,744 bytes), in the existing cloud Python 3.13.5 sandbox. Assessment date in all cases: 2026-09-19; all records are deliberately synthetic.

- `last_refreshed=2026-09-20`, cadence 30 -> **EVIDENCED**, detail `Fixture age is -1 days against a 30-day cadence.`
- `cleanup_required=true`, verification 2026-09-20 -> **EVIDENCED**.
- required `["empty"]`, covered inventory omitted or null -> **OBSERVED_GAP**; indistinguishable from an explicitly observed empty list.
- required `["a"]`, covered string `"a"` -> **EVIDENCED**.
- required `["empty"]`, covered object `{"empty":false}` -> **EVIDENCED** by converting mapping keys to a set.
- required `[1]`, covered `["1"]` -> **EVIDENCED** through implicit string coercion.
- Positive control: explicit covered `[]` against a nonempty valid requirement list correctly reports **OBSERVED_GAP** and must remain so.

## Completion contract
Repair the existing assessor, not a competing instrument. Future-dated refresh or cleanup does not establish evidence at the assessment date; use UNKNOWN with the chronology reason and follow-up. Coverage comparison requires documented lists of nonblank string case identities. Omitted/null/invalid covered inventory remains UNKNOWN; explicitly supplied empty inventory remains an observed gap when requirements exist. Do not coerce strings, mappings, or nonstring entries into evidence. Preserve valid identity/order/duplicate behavior without inflating the unique-case count, same-day/cadence boundaries, non-applicable cleanup, input immutability and existing summaries/rendering.

Retain focused unit tests, real CLI normal/optimized execution, a synthetic before/after operator rehearsal and exact source bindings. Run existing lane tests and the discovery bridge. Review and expected-head main merge only after actual source/behavior checks; hosted jobs are reported separately and never called passed while queued.

## Scope and safety
Only `revenue/uiowa_rfq_18649_test_data_readiness/`; no occupied workbench/compiler changes, new workflow, production data, live-system access, outreach, appointments, paid runner or University findings. Synthetic dates are rehearsal data, not a calendar action.
