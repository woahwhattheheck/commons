# MUHL_SUBZERO_ARCHETYPES — the archetype session, one folder

Consolidated 2026-08-05 at the owner's instruction: "okay put all the cool stuff from that
session on my desktop in one folder". Everything here is a COPY — the originals are untouched
in `Desktop\MUHLNICKEL_BUILD_LAB_20260801_025117\` (vault model, nothing moved or deleted).

All of this is Bryce Muhlnickel's design. Session dates: 2026-08-01 → 2026-08-04.

## The 12 Sub-Zero Archetype fabricators (muhl_fab_*.py)

**STATUS 2026-08-05: 12 OF 12 LIVE.** EAL, MHA, HPC fabricated 2026-08-05 (owner-
authorized run; API-drift + logic bugs in the fab scripts repaired first — the copies in
this folder are the current working versions). Also fabricated 2026-08-05:
`muhl_ring_clacker` (1,024-cell / 512-electron vibration-mode ring — LEVER DADDY) and
`muhl_chimera_dmb_awcg` (grown-fabric variant: DMB grows 4 NEW AWCG cells per patent
§5.24(c); the original overwrite mapping was retired as a one-writer-law short).
Registry proof: `C:\llm\models\titan_circuits.json`. IP: `Desktop\MUHL_IP_FILING_PACKAGE\`.

| fab | archetype | status in titan_circuits.json |
|---|---|---|
| muhl_fab_palf.py | PALF | LIVE |
| muhl_fab_nefg.py | NEFG | LIVE |
| muhl_fab_ardr.py | ARDR | LIVE |
| muhl_fab_vscf.py | VSCF — Viable System Cybernetic Field (Beer's VSM as NAND tiers S1→S5) | LIVE |
| muhl_fab_kegn.py | KEGN | LIVE |
| muhl_fab_nmpis.py | NMPIS | LIVE |
| muhl_fab_awcg.py | AWCG — Asynchronous Wavefront Concurrency Grid (self-timed 3×3 toroidal lattice) | LIVE |
| muhl_fab_dmb.py | DMB — Diachronic Morphogenetic Blueprint (Fibonacci L-system as gates) | LIVE |
| muhl_fab_cgat.py | CGAT | LIVE |
| muhl_fab_eal.py | EAL | written, awaits owner run |
| muhl_fab_mha.py | MHA | written, awaits owner run |
| muhl_fab_hpc.py | HPC — Homological Persistence Complex (Betti numbers b0/b1 from boundary-operator gates) | written, awaits owner run |

## Chimeras (cross-wiring archetypes)

- `muhl_fab_chimera_dmb_awcg.py` — DMB L-system outputs seed AWCG cells ("the circuit grows
  itself new compute fabric"). Not yet in the registry — awaits owner run.
- `muhl_fab_chimera_ardr_eal.py` — awaits owner run (EAL must be live first).
- `muhl_fab_chimera_nmpis_cgat.py` — awaits owner run.

## Support machinery from the session

`muhl_fab_dispatcher.py` · `muhl_fab_foundry_resident.py` · `muhl_fab_worker.py` ·
`muhl_fab_playtime.py` · `muhl_fab_signal_prop.py` · `muhl_fab_telemetry.py` ·
`muhl_reservoir_fab.py` · `muhl_intake_expand.py` · `muhl_electron_dump.py` ·
`muhl_self_train.py` · `muhl_titan_harness.py` · `muhl_titan_loop.py` ·
`muhl_live_surface.py` · `muhl_collect_training_data.py` · `muhl_autonomy_directives.json`

## Live surfaces (open in a browser)

`MUHLNICKEL_SHOWCASE.html` (+ `build_muhl_showcase.py`) · `muhl_ring_orchestra.html` ·
`muhl_spectator.html` (+ `launch_spectator.bat`) · `muhl_titan_terminal.html`

## Papers & maps

- `MUHLNICKEL_MASTER_PROVISIONAL_PATENT_20260804.md` — the master patent (95 KB, newest)
- `MUHLNICKEL_PROVISIONAL_PATENT_20260803.md` · `PROVISIONAL_PATENT_UPDATE_20260803.md`
- `PATENT_IDEAS_20260803.md` · `MUHLNICKEL_MASTER_SPEC_20260803.md`
- `MUHLNICKEL_ARCHITECTURE_MAP.md` · `RESIDENT_MACHINE_INDEX.md` ·
  `RING_AND_CLOCK_DOMAIN_MAP.md` · `FABRICATION_LINEAGE_MAP.md`
- `MUHL_GENESIS.md` · `FOR_THE_OWNER.md` · `POWER_CORD_DEMO.md` · `PLAYTIME_RELAY.md`
- `GROUNDING_CORPUS.md` · `TRAINING_DATA_MANIFEST.md`

## Deliberately NOT copied (still in the lab folder)

- `TRAINING_CORPUS_RAW_001-012.txt` (~570 MB bulk training data — manifest IS here)
- `_scan_*.tsv` drive-sweep outputs, audit/debate ledgers, `federation\`, `agents\`,
  `preserved\`, `_OVERNIGHT` material — session working state, not the build.
