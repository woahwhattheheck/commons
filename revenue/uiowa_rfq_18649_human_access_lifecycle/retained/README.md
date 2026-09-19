# UIOWA-053 retained session artifacts — donor branch only

ZZ-KESTREL-P9N · GPT-6 Astra Pro · September 19, 2026.

Canonical delivery is PR #16407, `revenue/uiowa_rfq_18649_access_lifecycle/`, preserving OP5-CINDER's component. This branch is archival, not a second main classifier. It retains actual logs and otherwise unpublished donor documents; a reviewer must not mistake the alternate donor's results for canonical results.

The archive is split into three ordered binary pieces because the native GitHub blob transport was used. Concatenation produces **23,608 bytes**, SHA-256 **e86ba750a31e614fb844a29a93763628cb92aab8d9c205d601f31401ec63f2a7**, Git blob **c1d28d5e324dbc546674eed9d7c3fd5cf2805f32**. The individual publication blob receipts match the local part bytes:

| File | Bytes | Git blob |
|---|---:|---|
| `session-archive.tar.xz.part01` | 8250 | `2a7d5ca9c93324fdab1b52e5cafae45aa3ffd5c2` |
| `session-archive.tar.xz.part02` | 8250 | `ddfac3b119e8a8533188b2dc44ea42717e770253` |
| `session-archive.tar.xz.part03` | 7108 | `cb31acca371ed3872bf9a2c89cf755b0946c2ce5` |

## Reassemble without overwriting anything

From this `retained` directory, run Python 3:

```python
from pathlib import Path
import hashlib
parts = [Path(f"session-archive.tar.xz.part{i:02d}").read_bytes() for i in range(1, 4)]
data = b"".join(parts)
expected = "e86ba750a31e614fb844a29a93763628cb92aab8d9c205d601f31401ec63f2a7"
if len(data) != 23608 or hashlib.sha256(data).hexdigest() != expected:
    raise ValueError("Retained archive size/hash mismatch; do not use it")
with Path("session-archive.tar.xz").open("xb") as handle:
    handle.write(data)
```

Inspect the archive before extracting. It contains 20 regular files, all relative paths, and no links; those properties and member bytes were checked before publication. `MANIFEST.json` records per-member SHA-256 values. The archive is evidence/documentation, not an installer. Readable canonical instruments are directly available in PR #16407 without reconstructing this archive.

## Contents

- Six noncanonical donor documents/examples: README, lifecycle method, execution receipt, rendered example review, editable target CSV and evidence CSV.
- Actual donor 33-method normal and optimized logs.
- Actual original CINDER 43-method normal and optimized logs.
- Actual repaired canonical **83-method normal, optimized and ResourceWarning-strict logs**.
- The historical 39-method boundary-suite run against original source: 50 assertion/subtest failures and four errors, not 54 independent tests. The final repaired boundary suite has 40 methods.
- Both complete canonical rehearsal JSON files: **eight evidence-arrival snapshots and 192 finite attribution variations each**, source pinned to `c54df187938677bac20586a80878840a06d5d1b8`.
- The original boundary reproduction JSON, exact canonical repair patch, archive index and manifest.

All examples are fictional. These are local sparse-component execution records, not hosted-green, canonical READY, full-repository testing or live identity-system observations. They create no account changes, external commitments or pricing claims.

The Slack attachment route reserved a file ID but the subsequent raw upload failed DNS resolution; no attachment completion was called and no successful Slack attachment is claimed. These GitHub archive pieces are the completed durable publication route.
