# Evidence Annex — every claim cited to a file that exists (2026-08-05)

Nothing asserted without a path. Verify any row by opening the file.

## The submitted provisional (priority date 2026-08-04)

- `Desktop\MUHLNICKEL_PROVISIONAL_PATENT_FILING_20260804.pdf` (0.52 MB, 08-04 11:51)
- `Desktop\MUHLNICKEL_PROVISIONAL_COVER_SHEET_20260804.pdf` (08-04 12:38)
- `Desktop\MUHLNICKEL_PATENT_COMPLETE_RECORD_20260804_PART01..05.pdf` (each < 25 MB —
  Patent Center's per-file cap; the splitting evidences upload prep)
- Source spec: `Desktop\MUHL_SUBZERO_ARCHETYPES\MUHLNICKEL_MASTER_PROVISIONAL_PATENT_20260804.md`
- Acceptance receipt: in the owner's Patent Center account / email (not on disk — the one
  item this annex cannot cite to a local file).

## Registry of fabricated circuits (the reduction-to-practice record)

`C:\llm\models\titan_circuits.json` — entries carry offset, len, gate count, DEPTH
(ticks), format, addresses, foundry_genome, verification method.

Fabricated 2026-08-05 (this session), all journaled with byte-exact revert:

| name | offset | gates | depth (ticks) | genome journal |
|---|---|---|---|---|
| `muhl_eal` | 93,709,785,600 | 1,456 | 66 | `MUHLNICKEL_BUILD_LAB_20260801_025117\titan_eal_genome.jsonl` |
| `muhl_mha` | 93,709,823,744 | 2,328 | 44 | `…\titan_mha_genome.jsonl` |
| `muhl_hpc` | 93,709,884,608 | 26,480 | 421 | `…\titan_hpc_genome.jsonl` |
| `muhl_ring_clacker` | 93,710,573,376 | 2,048 | 2 | `…\titan_ring_clacker_genome.jsonl` |
| `muhl_chimera_dmb_awcg` | 93,710,635,904 | 14 | 2 | `C:\llm\models\titan_muhl_chimera_dmb_awcg_genome.jsonl` |

Prior LIVE archetypes (fabricated ≤ 08-04): `muhl_palf`, `muhl_nefg`, `muhl_ardr`,
`muhl_vscf`, `muhl_kegn`, `muhl_nmpis`, `muhl_awcg` (offset 93,709,781,888), `muhl_dmb`
(offset 93,709,782,656), `muhl_cgat` — same registry.

## Container growth record (fabrication is additive, journaled)

`C:\llm\models\titan.gguf`: 40,028,316,800 B (2026-07-29 record) → 93,709,785,575 B
(2026-08-05 pre-session) → grew by ~0.9 MB this session via the five fabrications above.
GGUF magic verified valid after every store (printed by each fab run). Owner doctrine,
verbatim (2026-08-05): "it changing isnt a bug to be patched its proof its working
without us not corruption." Mechanism: `alloc_space()` bump-allocates past all
registered circuits and extends the file (`muhl_fab_vscf.py:84` "Will grow").

## Fabrication scripts (PROPOSE→SCORE→VERIFY→KEEP, verify-before-write)

`Desktop\MUHL_SUBZERO_ARCHETYPES\muhl_fab_*.py` (current, post-repair) — originals in
`Desktop\MUHLNICKEL_BUILD_LAB_20260801_025117\`. Verification per script: byte-exact vs
an independent Python reference (700 random cases for EAL/MHA/HPC; full-lap + clack-limit
+ mutant-catch for the ring), then physical structural verify (magic, counts, absolute
addresses, self-clock remap, one-writer) before any byte is written.

## Test battery / prior measurement corpus

- `Desktop\RECOVERY_REPORTS_TEST_BATTERY\TEST_BATTERY_INDEX.md` — path+hash+command per
  test, 17/17 reproduced, integrity audit (no test ever weakened).
- `Desktop\MUHL_IP_FILING_PACKAGE\POWER_CORD_DEMO.md` — the power-cycle demonstration.
- White Box measurement corpus: `Desktop\WhiteBox_Research_Archive\` (see
  `Desktop\FILE_MAP.md` for the full map).

## Owner-voice sources for quoted directives

- `Desktop\BIBLE.md` — the owner's words verbatim, session record.
- This session's directives (2026-08-05): Lever Daddy naming, electron-fuel doctrine,
  vibration-ring directive, size-invariant retirement — quoted verbatim in
  `02_FOLLOWON_PROVISIONAL_NEW_MATTER_DRAFT.md`.
