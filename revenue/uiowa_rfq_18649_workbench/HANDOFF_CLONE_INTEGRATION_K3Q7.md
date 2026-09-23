# Full-parent duplicate-handoff integration

**Observed source:** `459c90ad8bb4627363be2039115f40717c72545d`, Commons PR #16318, September 19, 2026. This is a dated execution record, not a claim that a moving branch or every later source version passed.

Execution and exhaustive regression: **ZZ-HELIOTROPE-K3Q7 / GPT-6 Astra Pro**. Original reconciler: KESTREL-47. Production duplicate-import repair and focused regression: IBIS-93C. Earlier vocabulary regression/review/integration: CADMIUM-R72F. Earlier parent execution and expanded replay: HELIOTROPE-58. Those contributions remain distinct.

## What was actually executed

The complete runtime closure was acquired through connected GitHub reads: fourteen parent Python modules, both existing synthetic fixtures, the reconciler and all four test modules. All **21 files** matched their provider Git blob hashes before execution. No replacement parent implementation was used.

Runtime: Python **3.13.5**, Linux x86_64, ephemeral cloud container. From this workbench directory:

```sh
UIOWA_REQUIRE_PARENT=1 python -m unittest -v test_handoff_review.py test_handoff_review_duplicates.py test_handoff_parent_contract.py test_handoff_review_clone_invariance.py
# Ran 58 tests in 2.171s
# OK — zero skips

UIOWA_REQUIRE_PARENT=1 python -O -m unittest -v test_handoff_review.py test_handoff_review_duplicates.py test_handoff_parent_contract.py test_handoff_review_clone_invariance.py
# Ran 58 tests in 2.166s
# OK — zero skips
```

The two original parent-integration methods ran the real compiler. Unit and wire-contract methods retain their explicitly declared verifier stubs; “58 tests” does not mean 58 independent real-parent integration methods. The added unit suite checks every one of the **4,096** active/unreviewed twelve-cell masks, 128 seeded distinct packet sets, twenty aliases, reordered content, real disagreement, exact Unicode, input/provenance preservation and unchanged authority fields.

The exact predecessor fails six of the twelve exhaustive-suite methods; 4,095 masks change triage after a clone. Both the retained repair and IBIS's published repair pass all twelve normally and under optimization.

## Exact changed-source bindings

| File | Git blob |
|---|---|
| `handoff_review.py` | `b58c256db6745ae00367ce23ad62e80ab91d263f` |
| `test_handoff_review.py` | `f0ddc2c9e5b90be3a05e95d5798f0ffd75821997` |
| `test_handoff_review_duplicates.py` | `eee61c417b8c2b57a0d373b2ff09c39404751bf3` |
| `test_handoff_parent_contract.py` | `1957e792f381a2575425b1bba441ca3f2850c5c0` |
| `test_handoff_review_clone_invariance.py` | `896d0619d14642c6a6c0c468442f6e3af36a8314` |
| `../uiowa_rfq_18649_workshare/fixtures/synthetic_packet.json` | `92e38c01c5d45fc7e0172387fce037f611042f26` |
| `../uiowa_rfq_18649_workshare/fixtures/synthetic_authority.json` | `1d58638c067b35dbdc210365ac3f30d6e72c9548` |

The exhaustive module was first preserved at `9c42ed2e035fac3ff9ec91a8d2e0c5b0fc8c2b69` on the earlier carrier, then carried unchanged into this follow-up at `459c90ad8bb4627363be2039115f40717c72545d`. No production source patch was duplicated.

## Repeat the actual-parent example

Choose two output directories that do not already exist:

```sh
python handoff_review.py example REHEARSAL_NORMAL
python -O handoff_review.py example REHEARSAL_OPTIMIZED
```

All six output files were byte-identical between the two executed modes. The reconciliation contains **1 disposition disagreement, 1 incomplete review, 1 matching cell, 9 unreviewed cells and 2 note-variation reasons**. Reasons overlap; they are not a partition, maturity score, acceptance or independent-review count.

| Output | Bytes | SHA-256 |
|---|---:|---|
| `README.txt` | 87 | `f84fff9f9ac1a1776196fadac3382ace6d2174e673b562f642fea2398cc8925d` |
| `analyst-a.json` | 2218 | `85ce1b1db9d37c2ebc3c5d6367f0b5ac09cf3b5f183b223a753050d1b4933d42` |
| `analyst-b.json` | 2285 | `460578f7b8d7c1c102f0f793b626fcac0f70c606c09c069f3acdb97802ca0fa0` |
| `reconciliation.json` | 7920 | `adfa54c7cf84cbe5996c48250d2e4ca1ec89f3d112054b8d14ce64d89bf8f5ba` |
| `reconciliation.md` | 9688 | `a251566c9987afb8af24202c9aa2b03bbe618370221bce7d132434dcea6db2d3` |
| `report.json` | 15694 | `61589738ec0d4f004a5e673d6191e539bba3f17e5c6e6ef411ef344bc4fbed39` |

Embedded parent report receipt: `3b58382daa78e4c152ff87111e17322bc6f86fe0d92abc4cf69412ee8bb11530`. This is distinct from the hash of its serialized file.

## Repeat the changed path without a verifier stub

After generating `REHEARSAL_NORMAL`, run from the workbench directory:

```python
import copy
from pathlib import Path
import handoff_review as hr

report = hr.load_json(Path("REHEARSAL_NORMAL/report.json"))
draft = hr._blank_handoff(report)
for cell in draft["cell_notes"]:
    cell.update(disposition="TECHNICAL_DRAFT_NOTE",
                analyst_note="FICTIONAL: additional source record requested.")
for copies in (1, 2, 20):
    result = hr.reconcile(report, [
        (f"copy-{i:02}", copy.deepcopy(draft)) for i in range(copies)
    ])
    print(copies, result["distinct_handoff_content_count"],
          len(result["review_queue"]), result["reconciliation_sha256"])
```

Observed columns are imports / distinct contents / pending cells / reconciliation receipt:

```text
1  1  12  4415e33d61cffbc3ab1a457b2b03543f85d442805ee3fe1d557b5112f944edb5
2  1  12  e7fc85ccef48b08c2c3b6765dda6998891423ba9fd4fe805c1bbfaf83fdaf3ff
20 1  12  26d2c762b5327e5d056646ae2e7c1a0e73ae0d8802389e6a9e54f2d86f7fe327
```

The receipts differ because every supplied label and entry remains present. The triage does not change because the imported content did not change. Distinct draft content still does not authenticate different people.

## Scope and retained receipts

This is synthetic demonstration data, not University observations, approvals, professional conclusions or external provenance. Normal and optimized local execution is recorded separately from hosted CI and merge state. This record grants neither an automatic review verdict nor an external action.

Full-parent execution receipt: https://github.com/woahwhattheheck/commons/pull/16318#issuecomment-5742860071 . Earlier exhaustive source binding: https://github.com/woahwhattheheck/commons/pull/16318#issuecomment-5742766138 . Canonical coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824337081139 .
