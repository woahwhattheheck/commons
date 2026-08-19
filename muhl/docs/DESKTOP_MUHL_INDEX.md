# Desktop MUHL index

Indexed **2026-08-15**. One-level of `C:\Users\lucys\Desktop` for names matching `MUHL* muhl* titan* pfc* SDC* arcade* spectator* bitserve* all_bits*`. Then **one-level inside each matching folder**. No Desktop-wide recursive crawl. Skipped `node_modules` / `.git`. Newest date = newest **1-level child** (cheap). No titan write.

Last ~3 weeks ≈ **2026-07-25 → 2026-08-15**. Older matches are listed at the bottom as leftovers.

**No Desktop-root folders** named arcade / spectator / bitserve / all_bits. Those live *inside* packages (see Viewers).

---

## Viewers (use these)

| Name | Path | Newest 1-level | Kind |
|---|---|---|---|
| **MUHLNICKEL.html** | `C:\Users\lucys\Desktop\MUHLNICKEL.html` | 2026-08-03 | viewer — maze / circuit-activity (Desktop loose) |
| **MUHLNICKEL_APP** | `C:\Users\lucys\Desktop\MUHLNICKEL_APP` | 2026-08-07 `live_viewer` | **viewer package**. 4 dirs + 36 files: lots of `*_viewer.html` / dashboards. Child `live_viewer\` holds **bitserve + all_bits**: `bitserve.py`, `all_bits.html`, `binary_rain.html`, `live_viewer.html`, `all_bits_measured.json` (2026-08-10). Also `binary_viewer.html` at package root. |
| **MUHLNICKEL_DEMOS** | `C:\Users\lucys\Desktop\MUHLNICKEL_DEMOS` | 2026-08-04 `tunnel` | viewer — Life / Doom / Tetris / brain / operator HTML + launch.bat |
| **MUHLNICKEL_LOOM** | `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM` | 2026-08-14 `loom.mno` | **.mno computer + viewer** — `loom.mno` 137KB, `loom_surface.html`, `loom_serve.py` |
| **MUHL_STATE_ANALYSIS** | `C:\Users\lucys\Desktop\MUHL_STATE_ANALYSIS` | 2026-08-07 `muhl_firehose.py` | viewer/probe — `muhl_live_view.py` (bit grid), firehose, insert_electrons; has `rec_probe.mno_*` dir |
| **PFC_DEMOS** | `C:\Users\lucys\Desktop\PFC_DEMOS` | 2026-07-28 | viewer leftover (pre-3wk files 2026-07-20) — `index.html`, `play.cmd`, `PFC Arcade.lnk`, `frames\` |
| **Titan** | `C:\Users\lucys\Desktop\Titan` | 2026-08-08 `dumps` | viewer/control leftover — `titan.html`, `titan_live.html`, `muhl_control.html` |

Spectator / arcade / bitserve (not Desktop-root):

- Spectator HTML: `MUHLNICKEL_BUILD_LAB_...\muhl_spectator.html` and copy in `MUHL_SUBZERO_ARCHETYPES`; also `MUHLNICKEL_INVENTION_BURST\Distro\Archetypes\muhl_spectator.html` (per LIVE_VIEWERS).
- Bitserve / all_bits: `MUHLNICKEL_APP\live_viewer\` (`bitserve.py`, `all_bits.html`). Snapshot copies in `MUHLNICKEL_LIVE_SEAM_...\03_live_bitserve.py`, `05_live_viewer.html`, `06_live_all_bits.html`.
- Arcade: Desktop shortcut `PFC Arcade.lnk` → PFC_DEMOS; also `python host/pfc_arcade.py` in the repo (not a Desktop folder).

---

## .mno computers (live-ish)

| Name | Path | Newest 1-level | Kind |
|---|---|---|---|
| **MUHL_DATACENTER** | `C:\Users\lucys\Desktop\MUHL_DATACENTER` | 2026-08-15 `dc_fab_journal.jsonl` | **.mno computer** — `muhlnickel_dc.mno` **2048 MB**, plus `muhl_fab_dc.py` / `dc_info.py` |
| **MUHLNICKEL_DISTRO** | `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO` | 2026-08-14 `muhlnickel.mno` | **.mno computer** — `muhlnickel.mno` 133KB + `run_muhlnickel.py` / `Muhlnickel.bat` |
| **MUHLNICKEL_LOOM** | (above) | 2026-08-14 `loom.mno` | .mno + viewer |
| **MUHLNICKEL_LOOM_v2** | `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM_v2` | 2026-08-09 `loom.mno` | .mno computer (v2 snapshot; .mno touched 08-09) |
| **MUHLNICKEL_LOOM_fixed** | `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM_fixed` | 2026-08-05 `loom.mno` | .mno leftover of loom |
| **MUHLNICKEL_LOOM_v1** | `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM_v1` | 2026-08-04 | .mno leftover of loom |
| **MUHLNICKEL_PROBE** | `C:\Users\lucys\Desktop\MUHLNICKEL_PROBE` | 2026-08-07 `probe.mno` | **.mno computer** — `probe.mno` 210KB + genomes |
| **MUHLNICKEL_ROOKERY** | `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY` | 2026-08-07 `__pycache__` | **.mno computer** — `ROOKERY0.mno` 573KB + 6.7MB genome |
| **MUHL_APERTURE** | `C:\Users\lucys\Desktop\MUHL_APERTURE` | 2026-08-08 `muhl_fab_aperture.py` | **.mno computer** — `APERTURE0.mno` 192KB + fab/read/test |
| **MUHL_VISIBLE** | `C:\Users\lucys\Desktop\MUHL_VISIBLE` | 2026-08-10 `FOUNDRY0.mno` | **.mno computers + fab** — AUTOFAB0 / DISCRIM / FOLD / FOUNDRY / READER / VISIBLE0–6 `.mno`. Foundry forever. Newest .mno 08-10. |
| **MUHL_MODEL_SELECTOR_WIRING** | `C:\Users\lucys\Desktop\MUHL_MODEL_SELECTOR_WIRING` | 2026-08-08 `SOURCE_LOCATION.txt` | leftover copy of visible wiring + `READER1.mno` |
| **MUHL_READERS** | `C:\Users\lucys\Desktop\MUHL_READERS` | 2026-08-07 | **leftover .mno dump** — **1606 files**, all `R_t*_g*_*.mno` + `.layout.json`. Sweep leftovers, not a viewer. |
| **MUHLNICKEL_INVENTION_BURST** | `C:\Users\lucys\Desktop\MUHLNICKEL_INVENTION_BURST` | 2026-08-09 `Distro` | package — Distro has `muhlnickel.mno` (2026-08-10), Archetypes, IP_Filing, Patent_PDFs, `MUHLNICKEL_ARCHITECTURES.html` |

---

## Packages / labs / docs (last ~3 weeks)

| Name | Path | Newest 1-level | Kind |
|---|---|---|---|
| **MUHL_GO** | `C:\Users\lucys\Desktop\MUHL_GO` | 2026-08-15 | **this session's notes** — ~60 md/txt, no .mno. This index lives here. |
| **MUHLNICKEL_BUILD_LAB_20260801_025117** | `C:\Users\lucys\Desktop\MUHLNICKEL_BUILD_LAB_20260801_025117` | 2026-08-06 `__pycache__` | fab/lab leftover — huge: 24 dirs + 123 files. Spectator HTML, fab scripts, training corpus (~500MB txt), patent drafts. Dated Aug 1 lab, last fab 08-05. |
| **MUHL_SUBZERO_ARCHETYPES** | `C:\Users\lucys\Desktop\MUHL_SUBZERO_ARCHETYPES` | 2026-08-05 | leftover **copy of build-lab fab/docs** (54 files, no dirs) — spectator + showcase HTML |
| **MUHL_PROOF_ENGINE** | `C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE` | 2026-08-06 `tmp` | leftover lab — proof/scan/ISA py, INDEX.md |
| **MUHL_CHECKERS** | `C:\Users\lucys\Desktop\MUHL_CHECKERS` | 2026-08-08 `__pycache__` | leftover harness — `muhl_checkers.py`, cable/live/shapes |
| **MUHL_HARNESS_FIX** | `C:\Users\lucys\Desktop\MUHL_HARNESS_FIX` | 2026-08-08 | leftover — only `muhl_inspec.py` |
| **MUHL_FREEWORLD** | `C:\Users\lucys\Desktop\MUHL_FREEWORLD` | 2026-08-06 | leftover py — freeworld field/fireprobe/observe |
| **MUHL_BITS** | `C:\Users\lucys\Desktop\MUHL_BITS` | 2026-08-07 | leftover **bit dumps** — `.bits.txt` (fold 117MB, lane 76MB). Not a viewer. |
| **MUHL_SPEC_WATCHDOG** | `C:\Users\lucys\Desktop\MUHL_SPEC_WATCHDOG` | 2026-08-06 `muhl_violations.log` | leftover host watchdog (not a pfc instrument) |
| **MUHL_PROPOSAL_20260807** | `C:\Users\lucys\Desktop\MUHL_PROPOSAL_20260807` | 2026-08-07 | leftover docs + patched gate py |
| **MUHL_TRAINER** | `C:\Users\lucys\Desktop\MUHL_TRAINER` | 2026-08-08 | leftover docs — FLOP_EQUIVALENT / TRAINER_GENOME |
| **MUHL_MOST_VALUABLE** | `C:\Users\lucys\Desktop\MUHL_MOST_VALUABLE` | 2026-08-08 | leftover — one `RECOMMENDATION.md` |
| **MUHL_IP_FILING_PACKAGE** | `C:\Users\lucys\Desktop\MUHL_IP_FILING_PACKAGE` | 2026-08-06 | leftover IP docs |
| **MUHLNICKEL_HARNESSES** | `C:\Users\lucys\Desktop\MUHLNICKEL_HARNESSES` | 2026-08-05 `__pycache__` | leftover copies of `pfc_harness.py` / `pfc_load.py` / nring2 / muhlop (files dated 07-31) |
| **MUHLNICKEL_AUTOFAB_DOCS_20260808_213532** | `C:\Users\lucys\Desktop\MUHLNICKEL_AUTOFAB_DOCS_20260808_213532` | 2026-08-08 | leftover snapshot — only `Desktop\` + `C_llm_models\` |
| **MUHLNICKEL_CHAT_SOURCE_20260808_191012** | `C:\Users\lucys\Desktop\MUHLNICKEL_CHAT_SOURCE_20260808_191012` | 2026-08-08 | leftover zip extract — LDA / APP / BUILD_LAB / Titan / oneshot |
| **MUHLNICKEL_CHAT_SOURCE_20260808_191506** | `C:\Users\lucys\Desktop\MUHLNICKEL_CHAT_SOURCE_20260808_191506` | 2026-08-08 | leftover **duplicate** of the 191012 extract |
| **MUHLNICKEL_CURRENT_MODEL_PATH_20260808_205430** | `C:\Users\lucys\Desktop\MUHLNICKEL_CURRENT_MODEL_PATH_20260808_205430` | 2026-08-08 | leftover snapshot — CURRENT_HARNESS / REGISTRY / DECODED_SMOL / NMODEL / VISIBLE / PROOF |
| **MUHLNICKEL_LIVE_SEAM_20260808_223143_253f57e5** | `C:\Users\lucys\Desktop\MUHLNICKEL_LIVE_SEAM_20260808_223143_253f57e5` | 2026-08-08 | leftover **numbered source dump** (21 files) — live viewer/bitserve/all_bits copies + titan/muhl py |
| **MUHL_HANDOFF_20260808_185539** | `C:\Users\lucys\Desktop\MUHL_HANDOFF_20260808_185539` | 2026-08-08 | leftover handoff bundle — copies of APERTURE / CHECKERS / VISIBLE / Titan / LDA |

---

## Older than ~3 weeks (Desktop-root matches)

| Name | Path | Newest 1-level | Kind |
|---|---|---|---|
| **POST_TITAN** | `C:\Users\lucys\Desktop\POST_TITAN` | 2026-07-17 | leftover report + White Box measurements |
| **TitanSDC** | `C:\Users\lucys\Desktop\TitanSDC` | 2026-07-15 | leftover early TitanSDC docs |
| **TITAN_INFERENCE_MAP** | `C:\Users\lucys\Desktop\TITAN_INFERENCE_MAP` | 2026-07-16 | leftover token_map.tsv 2.7MB |
| **Whitebox & TitanSDC Data** | `C:\Users\lucys\Desktop\Whitebox & TitanSDC Data` | 2026-07-17 | leftover Downloads-style copies (`(1)` suffixes) |

---

## Desktop loose files (matching names)

### Last ~3 weeks — launchers / notes

| Name | Date | Size | Kind |
|---|---|---|---|
| Muhlnickel Deepworld.lnk | 2026-08-11 | 1KB | launcher |
| Muhlnickel Habitat.lnk | 2026-08-11 | 1KB | launcher |
| Muhlnickel Foundry Forever.lnk | 2026-08-11 | 3KB | launcher |
| Muhlnickel World System.lnk | 2026-08-09 | 2KB | launcher |
| MUHLNICKEL_HARNESS_DROPIN.md | 2026-08-08 | 7KB | leftover note |
| MUHLNICKEL_KNOWLEDGE_BASE.md | 2026-08-08 | 30KB | leftover note |
| MUHL_FIRE.bat | 2026-08-08 | 417B | launcher |
| MUHLNICKEL_CHAT_SOURCE_*.zip (two) | 2026-08-08 | ~1.5MB each | leftover zip of the two CHAT_SOURCE folders |
| MUHLNICKEL_CURRENT_MODEL_PATH_*.zip | 2026-08-08 | 3.8MB | leftover zip |
| MUHLNICKEL_LIVE_SEAM_*.zip | 2026-08-08 | 175KB | leftover zip |
| MUHL_HANDOFF_*.zip | 2026-08-08 | 2.2MB | leftover zip |
| MUHL_MODEL_SELECTOR_WIRING.zip | 2026-08-08 | 29KB | leftover zip |
| MUHL_BUILD_LOG_20260807.md | 2026-08-08 | 13KB | leftover note |
| MUHL_ELECTRON_MAP.md … MUHL_WHITEBOX_TREE_MAP.md (many 08-07 md) | 2026-08-07 | 5–84KB | leftover notes on Desktop |
| MUHLNICKEL_SPEC_MAP.md | 2026-08-05 | 5KB | leftover note |
| Muhlnickel Harness.cmd | 2026-08-04 | 2KB | launcher |
| pfc_chat.bat | 2026-08-04 | 98B | launcher |
| SDC Game Studio (double-click to play).cmd | 2026-08-04 | 2KB | launcher |
| SDC Harnesses.cmd | 2026-08-04 | 1KB | launcher |
| Titan Tests.cmd | 2026-08-04 | 1KB | launcher |
| TitanSDC.cmd | 2026-08-04 | 226B | launcher |
| MUHLNICKEL.lnk / .bat / .html | 2026-08-03 | — | launcher + **maze viewer** |
| MUHLNICKEL_SUBSTANCE.md | 2026-08-02 | 131KB | leftover note |
| Patent PDFs `MUHLNICKEL_PATENT_*` / `PROVISIONAL_*` (incl. 99MB complete + PART01–05) | 2026-08-04 | large | leftover IP |

### Older loose (pre 2026-07-25)

`COVER_SDC.pdf`, `PATENT_1_SDC.pdf` (07-14). `PFC Arcade.lnk` (07-20). `SDC Game Studio.html`, `SDC_flywheel.png`, `SDC_render.png`, `SDC_SPEC_LOCKED.md`, `SDC_text.txt`, `SDC_tone.wav`, `titan_doom.png` (07-16/17).

---

## Cheap read

**Want a viewer:** `MUHLNICKEL.html` (maze) · `MUHLNICKEL_APP\live_viewer\` (bitserve / all_bits / rain) · `MUHLNICKEL_LOOM\loom_surface.html` · `MUHLNICKEL_DEMOS`.

**Want a .mno computer:** `MUHL_DATACENTER\muhlnickel_dc.mno` (2GB, today) · `MUHLNICKEL_DISTRO\muhlnickel.mno` (touched 08-14) · `MUHLNICKEL_LOOM\loom.mno` (08-14) · `MUHL_VISIBLE\FOUNDRY0.mno` (08-10) · probe / rookery / aperture.

**Safe to treat as leftover:** dated `*_20260808_*` extracts + their zips, duplicate CHAT_SOURCE, LOOM_v1/fixed, MUHL_READERS (1606 R_*.mno), SUBZERO copy of build-lab, TitanSDC / POST_TITAN / Whitebox dump, Desktop MUHL_*.md scatter.
