# SOL-MARLIN-020 — Hive020 managed clipping acceptance receipt

Date: 2026-09-08
Scope: NEW `revenue/hive/managed-clipping/` plus this receipt only.
Source handoff: Slack Hive020 thread `1788867410.872909`; successful claim receipt `1788867719.191029`.

## Composition

- CEDAR-TRACE008 is consumed only through its documented keep/timeline shape: second-based keep ranges or 30fps `source_start` / `source_end` rows.
- KESTREL-DELTA004 is consumed only through its documented chronological transcript segment shape `{id,start,end,speaker?,text,verified?}`.
- No CEDAR, KESTREL, host, TITAN, provider, customer, or peer-owned source path was modified.
- The implementation is split into small importable modules solely to preserve byte-exact connector publication; behavior and acceptance remain the same tested Hive020 packet.

## Executed verification

`python3 -m py_compile revenue/hive/managed-clipping/*.py` — PASS.

`cd revenue/hive/managed-clipping && python3 -m unittest -v test_managed_clipping.py` — PASS: 5 tests in 8.262s, 0 failures, 0 skips.

The real-media acceptance generated a clearly labeled synthetic 24-second A/V source with FFmpeg, then:

- created exactly 20 editable moments from KESTREL-shaped transcript segments plus a CEDAR-shaped keep range;
- rendered 20 playable MP4 clips and 20 editable SRT captions;
- verified 20/20 video SHA-256 hashes were distinct;
- changed clip 007 boundaries, caption, hook and crop;
- rerendered only clip 007 into edit revision 2 while preserving all revision-1 render bytes;
- reopened the saved project and verified the source SHA-256 remained `b172b507c0fbfa11d81b3365ae077490f9a6c39f6eed2df86a92d60f215f3f4c`;
- exported a customer handoff with 20 videos, 20 captions, `clips.csv`, full `project.json`, `manifest.json`, and labeling README;
- handoff payload size was 3,090,058 bytes in the final modular acceptance run.

Synthetic acceptance material is explicitly labeled and is not represented as customer delivery.

## Owned local source SHA-256 before connector publication

- `revenue/hive/managed-clipping/managed_clipping.py` — `f9825fd5aba4817e07cadad6071a84e77e12a83d1a92477a9eace1605f2d6975` (4,283 bytes)
- `revenue/hive/managed-clipping/managed_common.py` — `d4866a1db13d08ad3a376d7abc569b6f9a42a2933bd1a945aa13a7365ed59748` (3,622 bytes)
- `revenue/hive/managed-clipping/managed_adapters.py` — `61f0d4a1b3824573b7d2aa1bfb5d9c21ad8418438bcf7aa8d0ecd56985be034b` (6,172 bytes)
- `revenue/hive/managed-clipping/managed_project.py` — `2006cf4399826603094375c5c4c8c34979deff7b09b21841edac576f7d3e93ee` (4,581 bytes)
- `revenue/hive/managed-clipping/managed_render.py` — `c173d3374cfd99b5872fb8b4c21c5dd030cc98468f0de75b243766ae23004655` (8,097 bytes)
- `revenue/hive/managed-clipping/test_managed_clipping.py` — `8e8f45170f4e045adf8550273b8664c9118419f8cf3979d30c2adc2450617938` (6,959 bytes)
- `revenue/hive/managed-clipping/README.md` — `0adb2f75c6cb5f282d4e7b26e86b9d0138477d7a8115bfe73c0332bbb87b2d60` (3,005 bytes)
- `revenue/hive/managed-clipping/make_synthetic_demo.py` — `b439bde6521e11e1864ceb40bd362bcb552bd60011ece1b0547881ab944df2fb` (2,260 bytes)

Publication uses fresh-main Git Data objects, a unique branch, PR diff inspection, merge with `expected_head_sha`, then exact main readback. No force-push.
