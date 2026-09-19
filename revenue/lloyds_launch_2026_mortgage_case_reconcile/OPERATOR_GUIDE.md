# Mortgage case reconciliation operator guide

This demonstration compares supplied records and preserves their disagreements. Its two committed cases are strictly fictional. A result of `NO_DECLARED_BLOCKERS` means the configured reconciliation checks found no blockers in that supplied snapshot. It does not establish eligibility, affordability, underwriting approval, document authenticity or permission to lend.

The original concept and carrier belong to **Z-Quorum-7F2C / GPT-5.6 Sol**, [Commons issue 15959](https://github.com/woahwhattheheck/commons/issues/15959), commit `6c98221534bc183cf21b3a488402acc2b9849580`. This is a reconstruction of a damaged, non-importable source carrier; it is not an exact restoration of proven original behaviour. The unchanged original Git blob is `41e415f55336564c3d3010fa819b0bb0b6229ac9`.

## Run the complete fictional journey

Use Python 3 from this component directory. The output directory must be new.

```sh
python -B rehearse_mortgage.py --output-dir /tmp/mortgage-rehearsal-normal
python -B -O rehearse_mortgage.py --output-dir /tmp/mortgage-rehearsal-optimized
```

The rehearsal invokes the actual command line interface. It creates separate `baseline/` and `revised/` packets, verifies each using its copied verifier, runs the original compile/verify interface, checks that an edited receipt is rejected, and checks that an existing packet is preserved when an overwrite is rejected. Optimized mode propagates to each child process. Each command has its literal argument list, working directory, stdout, stderr and exit code retained under `commands/`.

Read `READOUT.md` for the comparison and `rehearsal.json` for the complete execution record. The latter is written only when every expected result has been observed. A failed run can retain partial files and command logs; it is not a completed rehearsal. Choose another new directory after inspecting a failure. No browser execution is part of this script.

## What the supplied snapshots say

Both fixtures use `CASE-7001` and `SUBJECT-7001`; those labels do not identify real people. All source, document, event and message references are fictional opaque identifiers. The `case_note` value demonstrates supported Unicode without containing personal data.

| Supplied evidence | Baseline `sample_case.json` | Revision `revised_case.json` |
|---|---|---|
| Requested amount | Broker: GBP 25,000,000 minor units; lender: GBP 24,500,000 minor units | Both records explicitly supply GBP 25,000,000 minor units |
| Identity document hash | Broker declares validated; lender declares rejected for the same hash | Both explicitly declare validated |
| Income document | No observation supplied | Both supply the same declared validated hash |
| Status history | `DOCUMENTS` and `REVIEW` both at 10:00 UTC | Revised record supplies `REVIEW` at 11:00 UTC |
| Later informational event | A request at 12:00 names `INTAKE` | The same request remains in the history |
| Observation cutoff | 18 September 2026, 14:00 UTC | 19 September 2026, 14:00 UTC |

The monetary values are supplied fixture facts, not quotes, recommended amounts or a lending decision. Document hashes are declared placeholder values derived from fictional labels; the package contains no identity or income documents and does not authenticate their contents.

The baseline should retain five issues: one `FIELD_CONFLICT`, one `DOCUMENT_STATUS_CONFLICT`, two `DOCUMENT_REQUIREMENT_UNMET` issues, and one `MILESTONE_AMBIGUOUS`. The disputed identity hash does not satisfy the identity requirement, so a document contradiction and unmet requirement both remain visible. Two copies of one validated hash count once. The simultaneous status claims leave the current milestone ambiguous. A later request naming an earlier milestone is informational and does not establish a transition.

The revised fixture explicitly supplies the corrections. The software neither chooses an amount nor decides which party was right. Its expected result is `NO_DECLARED_BLOCKERS`, current milestone `REVIEW`, and no issues. The original packet is retained alongside it. Issue IDs are deterministic within each receipt; the worked comparison uses issue code plus subject and shows each receipt's own IDs rather than treating those IDs as stable across changed issue sets.

## Create and inspect a packet directly

```sh
python -B mortgage_case_reconcile.py bundle sample_case.json --output-dir /tmp/mortgage-baseline
python -B mortgage_case_reconcile.py verify-bundle /tmp/mortgage-baseline
```

The packet contains:

| File | Purpose |
|---|---|
| `case.json` | Exact supplied input bytes |
| `normalized-case.json` | Strict, normalized case contract |
| `receipt.json` | Recompiled observations, issues, actions and timeline |
| `exceptions.csv` | Spreadsheet-facing exception queue |
| `summary.html` | Escaped, offline human-readable summary |
| `README.md` | Packet instructions and scope |
| `mortgage_core.py`, `mortgage_case_reconcile.py` | Copied implementation used for reproduction |
| `bundle-manifest.json` | File identities for the completed packet |

Open `summary.html` from the packet in a browser. It provides the observations behind each finding and links each issue to its own next action. A browser visual inspection is a separate activity from the script's execution proof.

After moving the packet to another directory, use the copied verifier:

```sh
cd /tmp/mortgage-baseline
python -B mortgage_case_reconcile.py verify-bundle .
```

Verification establishes consistency between the supplied input, the retained implementation and the generated outputs. Hashes do not prove that a broker or lender authored the input, that a document is genuine, or that the supplied observations are complete. Preserve the packet's original bytes when sharing it.

The original interfaces remain available. All output paths must be new:

```sh
python -B mortgage_case_reconcile.py compile sample_case.json --json-out /tmp/mortgage-receipt.json --csv-out /tmp/mortgage-exceptions.csv --html-out /tmp/mortgage-summary.html
python -B mortgage_case_reconcile.py verify sample_case.json /tmp/mortgage-receipt.json
```

## Interpret and act on the queue

Take the explicit issue/action pair back to the relevant record owner outside this demo. Retain every supplied observation. Supply a separate corrected snapshot only when the correction is known; retain the earlier packet for comparison. The tool performs no contact, collection, alerts, submission or record update in another system.

`source_digest` identifies normalized case content, while `semantic_digest` identifies the complete semantic receipt before its digest is added. Exact original input bytes are separately retained in `case.json`. Text normalization and deterministic collection ordering can make different original byte strings represent the same normalized content.

PII-shaped key rejection and opaque identifiers are input restrictions, not a guarantee that free text contains no personal information. Continue to use the supplied fictional fixtures for this public demonstration. Full programme fit and still-unknown owner inputs are recorded in [PROGRAMME_RESEARCH.md](PROGRAMME_RESEARCH.md).
