# TITAN V3 canonical-input archive closure — SOL-BOUNDARY

Operation: `TITAN-V3-CANONICAL-INPUT-ARCHIVE-CLOSURE-20260910-01`

## Disposition

**Evidence-only / HOLD_STALE_REPIN.** The source is reconstructed from authenticated
Slack packet `F0C0JPCAAQP`, 27,500 bytes, SHA-256
`f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`.
That packet is stale versus the advertised current re-pin, so this directory is an
isolated source/evidence handoff for the current one-tree publisher. It does not alter
the canonical V3 runtime, release archive, pointer, provider, Kaggle state, or submission.

## Closed boundary

The predecessor `package_files()` wrote each tar member to `work / member.name` before
establishing a canonical relative name. A synthetic regular member named
`../titan_v3_input_escape_witness.txt` escaped the temporary root, survived cleanup,
and returned a successful empty package. The outside bytes had SHA-256
`b38483d1bcc364216241e43521a606e3eb97a19294828bcc4b9fdcba8fdcc61a`.

The predecessor also checked only `base.sha256`, ignored `base.bytes` and `base.files`,
accepted ambiguous/duplicate/special members, and omitted the executing `build_v3.py`
from `source_shas()`.

The exact successor patch:

- authenticates compressed SHA-256, compressed byte count, and regular-file count;
- validates all tar members in memory before any filesystem write;
- permits only canonical relative POSIX names;
- rejects absolute, parent-escaping, backslash, drive-absolute, drive-relative,
  duplicate-normalized, special, sparse, oversized, and file-prefix-colliding members;
- caps member, per-file, and total uncompressed sizes;
- rejects overlay/source-check symlinks and receipt-key collisions; and
- binds `build_v3.py`, `apply_v3.py`, and source-only contracts into the manifest receipt.

## Exact validation

- Patch SHA-256: `fe6e9b53c5a1546394e591f9657ce555551c057eb7e9d38d667c82227dd7ef59`
- Normal Python: 8/8 PASS
- Optimized Python: 8/8 PASS
- Original packet under successor contracts: FAIL AS REQUIRED, rc=1, 18 errors
- Exact patch application to packet: PASS
- `py_compile`: PASS
- Source receipt: 10 entries, exact `V3-MANIFEST.json` overlay match
- `apply_v3.py` and `FILES.json`: byte unchanged

Run the repository evidence verifier from this directory:

```bash
python -B verify_evidence.py
python -B -O verify_evidence.py
python -m py_compile verify_evidence.py
```

The verifier checks all machine-readable receipts, exact content hashes, required patch
semantics, predecessor witness identity, and the ten-entry source receipt under both
interpreter modes. The full isolated executable carrier was retained separately because
this PR deliberately avoids copying stale V3 runtime bytes into the live tree.

## Ownership exclusions

- `--tree` target cleanliness and atomic publication remain SOL-CLEANROOM custody.
- The general syntactic-`assert` / `python -O` audit remains earlier SOL-ASTRA-AUTO
  custody. `ASTRA_HANDOFF.md` contains a supplementary exact predecessor only.
- Current/stale re-pin transport identity remains SOL-PRO custody.
- This evidence carrier makes no gameplay, score, release, or strength claim.

## Integration gate

The current one-tree publisher should reapply only
`evidence/canonical-input-closure.patch` to the corrected successor packet, regenerate
its source hashes, run the focused 8+8 source contracts from the full carrier, and then
run the full current package builder and release checks. Do not consume the stale packet
as canonical output.
