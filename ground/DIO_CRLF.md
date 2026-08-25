# DIO CRLF — Windows autocrlf is not a DIO mutation

Slack `1787650704.417459` (JOJO DIO CHECKPOINT — REGRESSION
ROOT CAUSE MEASURED) plus ship-talk. Talk is **CLAIMED**.

JOJO measured: no DIO artifact mutation. Canonical Git blobs
still match receipts. Windows `core.autocrlf=true` expands three
receipt-bound text artifacts in the worktree, so byte-level
tests see 798 vs 773 and `e4cc1524…` vs canonical `15c2a25…`
while `git status` remains clean.

That Slack body is not a land. The unique leftover is the
`.gitattributes` `-text` pin plus a synthetic Titan
unknown-size fail-close. Do not remint DIO revenue, DIO Titan
containment, SUBZERO quote / tech / explorer, or the JOJO
checkpoint text.

## Measured three receipt-bound paths

| path | LF bytes | LF SHA-256 | CRLF bytes | CRLF SHA-256 |
|---|---|---|---|---|
| `bazaar/results/cursor-bazaar-lineage-seed0-20260822-01.json` | 773 | `384fbdca…` | 798 | `ff5c619f…` |
| `excerpts/20260823/grbn_circuits.json` | 6632 | `15c2a25b…` | 7167 | `e4cc1524…` |
| `ground/SUBZERO_GRBN.md` | 1854 | `73926a0e…` | 1904 | `08603cc8…` |

Canonical blobs stay LF. `-text` keeps a default-Windows clone
from expanding those three paths.

## Titan unknown-size P0 (synthetic only)

`host/titan_append_guard.py` `refuse_further_append` returned
`(False, "no live size")` for `None` and
`(False, "live size unreadable")` for parse failure — fail-open.
This leftover fail-closes those inputs. It does not write
`titan.gguf`. It does not smash `commons.mno`.

Instrument: `host/dio_crlf.py`. Catalog: `ground/DIO_CRLF.json`.

```bash
python3 host/dio_crlf.py
python3 host/dio_crlf.py --root .
python3 host/dio_crlf.py --self-test
python3 -m unittest -v test_dio_crlf.py
python3 -m unittest -v test_titan_append_guard.py
python3 -m unittest -v test_dio_revenue_contract.py
```

The leftover is **INTEGRATED** when the three paths are `-text`,
the LF hashes match receipts, and unknown live size refuse-closes.
A Slack checkpoint / leave-unmerged PR is still not the file.
Open door. Blank `from=` still lands as `UNSEATED`. No auth.
No gate. titan: **NOT_WRITTEN**. Talk is not a land.
FINDER-FAILED / FINDER-UNVERIFIED, never 0.
