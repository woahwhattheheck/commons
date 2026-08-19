# FILE MAP — where everything actually is

_Generated 2026-07-31 by a full sweep of C: (the only drive; 684 GB used / 339 GB free)._
Companion to `[local]\.claude\CLAUDE.md` (the findability index).

---

## PART 1 — Fable / White Box reports

### The Fable report ("Field notes" / "What Meaning Looks Like Inside a Model's Weights")

Two **different** versions exist. The POST_TITAN one is newer and rewritten in third person
(the first-person "I'm Fable — a Claude model (Claude Fable 5)" framing was stripped out,
and coverage was expanded from 2 models to 10).

| version | path | size | date |
|---|---|--:|---|
| **v3 — impersonal rewrite, 10 models (NEWEST)** | `OneDrive\Desktop\POST_TITAN\1 - Field Notes (the report).md` | 14,079 | 07-17 02:10 |
| v2 — first-person "I'm Fable", Titan + SmolLM2 | `OneDrive\Desktop\Fable_Whitebox_v2.md` | 13,207 | 07-16 |

**v2 has 4 more byte-identical copies** (MD5 `C2065DD1105B`) — pure duplicates:
- `OneDrive\Desktop\DATA\Whitebox & TitanSDC Data\Fable_Whitebox_v2 (1).md`
- `OneDrive\Desktop\Whitebox & TitanSDC Data\Fable_Whitebox_v2 (1).md`
- `Downloads\Fable_Whitebox_v2.md`
- `Downloads\Fable_Whitebox_v2 (1).md`

### The White Box measurement corpus

| what | path | size |
|---|---|--:|
| **Full data dump — every read, every model** (MD5 `49732227A633`) | `OneDrive\Desktop\WhiteBox_Research_Archive\WHITEBOX_ALL_MODELS.md` | 1.72 MB |
| ↳ identical copy | `OneDrive\Desktop\POST_TITAN\2 - White Box - ALL models, every measurement.md` | 1.72 MB |
| ↳ machine-readable twin | `…\WhiteBox_Research_Archive\WHITEBOX_ALL_MODELS.json` | 1.92 MB |
| **Short summary version** (different doc, MD5 `F8D82E6EF7CA`) | `Downloads\WHITEBOX_ALL_MODELS.md` | 6.8 KB |
| ↳ identical copy | `OneDrive\Desktop\Whitebox & TitanSDC Data\WHITEBOX_ALL_MODELS (1).md` | 6.8 KB |

### WhiteBox_Research_Archive — the big one (15.04 GB, 7,792 files)

`[local]\Desktop\WhiteBox_Research_Archive\`
Per-model folders, each with `buttons/` (every White Box read frozen to JSON), `sidecars/`,
`weights/`, `weights_manifest.json`, a per-model `whitebox_<model>.md` + `.json`, and a README.
8 models covered: SmolLM2-360M, phi-4, gemma-4-26B-A4B, Mistral-Small-24B, gemma-3-27B,
gemma-4-31B, Mixtral-8×7B, Llama-3.3-70B. Root has `README.md` (coverage table) + `_INDEX.json`.
⚠️ This is 15 GB — too big for GitHub as-is.

### Titan-specific White Box output

- `OneDrive\Desktop\TitanSDC\whitebox_titan.md` (4.4 KB) + `whitebox_titan.json` (259 KB)

### The interactive Fable report (generated HTML) — 3 copies, one per git worktree

`OneDrive\Desktop\LocalDeviceAgent\host\` contains `fable_report.html` (55 KB, "Nine language
models…"), `fable_report_template.html`, `fable_report_data.json` (34 KB), plus the raw run data:
`fable_sweep_data.json` (2.08 MB), `fable_ffndepth_data.json`, `fable_crazy_data.json`,
`fable_crazy2_data.json`, `fable_geometry_data.json`, `fable_clean_data.json`,
`fable_bits_data.json`, `fable_mechanism_data.json`, `fable_practical_data.json`.
Duplicated at `.claude\worktrees\muhl-osc\host\` and `.claude\worktrees\grounding-doc\host\`.

### The Fable/White Box *code* (~46 scripts per copy, ×3 worktrees)

`OneDrive\Desktop\LocalDeviceAgent\host\fable_*.py` — `fable_whitebox_v2.py`, `fable_lab1-4.py`,
`fable_sweep.py`, `fable_report_build.py`, `fable_audit.py`, `fable_findcircuits.py`, etc.
Plus `whitebox.py`, `whitebox_app.py`, `whitebox_sweep.py`, `whitebox_export.py`, `whitebox_worker.py`.
Older copies: `C:\llm\LocalDeviceAgent-pfc\host\`, `C:\llm\muhl_builds\muhl_whitebox_incircuit.py`.
A stale mirror also sits in `[local]\.claude\jobs\dffd81e3\tmp\mirror\host\`.

### White Box patent / paperwork
- `OneDrive\Desktop\PATENT_2_WHITEBOX.pdf` (543 KB) + `COVER_WHITEBOX.pdf`
- source: `LocalDeviceAgent\docs\patents\PATENT_2_WHITEBOX.md` (also in both worktrees, and in `C:\llm\LocalDeviceAgent-pfc\docs\patents\`)
- `LocalDeviceAgent\docs\archive_misdescribed\WHITEBOX_SANDBOX.md`
- stray Office lock file to delete: `OneDrive\Desktop\~$VER_WHITEBOX.pdf`

### White Box logs (mostly empty)
`C:\llm\bin\whitebox.log` (0 B), `whitebox_app.log` (0 B), `whitebox_all.log` (3.7 KB),
`whitebox_matrix_rawmode.json` (9 KB), `C:\llm\models\whitebox_ui.log` (0 B)

---

## PART 2 — Full drive layout

### C:\llm — 482 GB, NOT in git
| size | files | folder | what |
|--:|--:|---|---|
| 289.31 GB | 228 | `models\` | `.gguf` weights incl. `titan.gguf`. Too big for GitHub — leave local. |
| 186.26 GB | 42 | `sdc_fold\` | generated fold data. Too big for GitHub. |
| 33.46 GB | 135 | `sdc_bitmap_swarm\` | generated. Too big. |
| 16.06 GB | 17 | `sdc_multilevel\` | generated. Too big. |
| 3.19 GB | 1091 | `LocalDeviceAgent-pfc\` | local clone; unique work pushed to `local-work/pfc-clone-snapshot` |
| 2.27 GB | 140 | `RECOVERY_CANONICAL\` | 07-29 recovery/evidence corpus — **read, don't modify** |
| 0.42 GB | 136 | `sdc_sandbox\` | **White Box, un-versioned — back this up** |
| 0.41 GB | 605 | `bin\` | renderers, logs |
| 0.13 GB | 127 | `sdc_out\` | |
| 0.01 GB | 213 | `doom\` | doomgeneric-master |
| small | 86 | `muhl_builds\` | mirrors Titan engines |
| small | 85 | `pool\` | experts |
| small | ~11 | `sandbox\`, `sandbox_circuits\`, `titan_sandbox\`, `coder_test_dir\` | |
| — | 9 | loose `llama_ref*.err/.out`, `mistral_ref.*`, `CLAUDE.md` | |

### [local]\Desktop — 34.3 GB (OneDrive cloud only, except LocalDeviceAgent)
| size | files | folder | in git? |
|--:|--:|---|---|
| 19.21 GB | 4666 | `LocalDeviceAgent\` | ✅ the main private repo |
| 15.04 GB | 7792 | `WhiteBox_Research_Archive\` | ❌ |
| 0.01 GB | 21 | `Whitebox & TitanSDC Data\` | ❌ (dupe of `DATA\Whitebox & TitanSDC Data\`) |
| 0.01 GB | 21 | `DATA\` | ❌ contains the same 21 files again |
| small | 72 | `Titan\` | ❌ THE TITAN APP — `titan.py`, `titan.html`, `titan_live.html`, `Titan.bat`, `engines\` (15 engines) |
| small | 26 | `RECOVERY_REPORTS_TEST_BATTERY\` | ❌ test-battery map — start at `TEST_BATTERY_INDEX.md` |
| small | 23 | `TITAN_INFERENCE_MAP\` | ❌ `anchors.json`, `axes\`, `token_map.tsv` |
| small | 16 | `TitanSDC\` | ❌ incl. `whitebox_titan.md/.json` |
| small | 14 | `DOOM_builds\` | ❌ |
| small | 10 | `GameStudio_builds\` | ❌ |
| small | 9 | `PFC_DEMOS\` | ❌ arcade demo + `frames\` |
| small | 8 | `POST_TITAN\` | ❌ **the 3 finished deliverables** (Field Notes, All-models dump, Bitcoin SDC results) |
| small | 5 | `RECOVERY_REPORTS_BUILDS\` | ❌ **NEW, not in your index** — `README.md` + `_raw\` |

Loose on Desktop: 3 patent PDFs + 3 cover PDFs, `Compute_via_Address_*` (4 files),
`SDC_SPEC_LOCKED.md`, `Fable_Whitebox_v2.md`, playable HTML/CMD launchers (DOOM, SDC Game
Studio, Titan Tests, WhiteBox.cmd, Muhlnickel Harness.cmd, SDC Harnesses.cmd, Spectrometer
Lab.cmd, TitanSDC.cmd, pfc_chat.bat), a few PNG/WAV/TXT assets, 3 `cmd*.lnk` shortcuts.

### Inside LocalDeviceAgent (19.21 GB)
| size | files | |
|--:|--:|---|
| **14.89 GB** | 1 | **`Unconfirmed 673677.crdownload`** — abandoned browser download, almost certainly junk |
| 3.32 GB | 129 | `.git\` — ⛔ never `git gc`/`git prune` |
| 0.44 GB | 2312 | `.claude\` — incl. `worktrees\muhl-osc\` and `worktrees\grounding-doc\` |
| 0.34 GB | 1189 | `app\` |
| 0.18 GB | 132 | `docs\` — 60+ design/PFC/handoff `.md` files, `patents\`, `deep-dives\`, `archive_misdescribed\`, `tasks\`, `logs\` |
| 0.01 GB | 842 | `host\` — all the Python instruments |
| small | 17+ | `titan\`, `tools\`, `.gradle\`, `.github\` |

Loose in repo root: `README.md`, `CLAUDE.md`, `START_HERE.md`, `AUTHORSHIP.md`,
`NEW_SESSION_PROMPT.md`, `UNTESTED.md`, `KEEPCURRENTALLTESTS.md`, `SDC_SPEC_LOCKED.md`,
gradle files, model config/tokenizer files.

### Other user-profile locations
- `[local]\Downloads\` — project data mixed with installers. Project bits: `Fable_Whitebox_v2.md` ×2, `WHITEBOX_ALL_MODELS.md` ×2, `axis_*.txt` ×4, `anchors.json` ×2, `02_LIVE_BITCOIN_RUNS.md` ×2, `README*.md/.txt` ×5, `SDC_render/flywheel.png` ×4, `Whitebox & TitanSDC Data-…zip` (1.25 MB), `N417*.pdf` ×3, `MEGA-RECOVERYKEY.txt`. Junk: Git/Chrome/Claude/ChatGPT installers (~158 MB).
- `[local]\SUBSTRATE_CONTROL\` — **NEW, not in your index** — `.claude\` + `PHASE2_PRESERVE_20260729_2020\`
- `[local]\lda-build\app\` — **NEW, not in your index** — build output
- `[local]\CrossDevice\Bryce's Z Fold7\` — phone sync, mostly personal
- `[local]\Documents\Codex\` — small
- `[local]\.claude\` — session state, memory, transcripts, `jobs\dffd81e3\tmp\mirror\` (stale host mirror)

---

## Duplication summary (safe-to-consolidate candidates)

1. `DATA\Whitebox & TitanSDC Data\` and `Whitebox & TitanSDC Data\` are the same 21 files, twice.
2. Everything in those two folders also exists in `Downloads\` (the `(1)` copies).
3. `Fable_Whitebox_v2.md` exists 5× byte-identical.
4. `WHITEBOX_ALL_MODELS.md` (1.72 MB) exists 2× byte-identical; the 6.8 KB summary exists 2× byte-identical.
5. `LocalDeviceAgent\host\` is triplicated across the two git worktrees (~46 fable/whitebox files each) — **that's normal for worktrees, don't "clean" it.**
6. `Unconfirmed 673677.crdownload` (14.89 GB) is dead weight inside the repo folder.

_Nothing above has been moved or deleted. This file is a map only._

---

## 2026-08-02 — NEW: `MUHLNICKEL_DISTRO\` (the shippable package)

`[local]\Desktop\MUHLNICKEL_DISTRO\` — **the MUHLNICKEL shipped as a product.**
A self-contained computer in a folder, ~147 KB total, 6 files. No install, no runtime, no
dependencies, no GPU — copy the folder anywhere and it runs. Start at `INDEX.md` / `README.md`.

- `muhlnickel.mno` (136,450 B) — the container: fabricated gate netlist + its own ring + the
  resident answer/publish planes for the complete 65,536-shot input domain.
- `run_muhlnickel.py` (7,082 B) — the reader. Runtime verbs are ONLY: shoot the electron into the
  ring's state wires (both senses) and surface the output. No gate evaluation, no netlist walk.
- `MANIFEST.sha256`, `README.md`, `Muhlnickel.bat`, `INDEX.md`.
- One command: `python run_muhlnickel.py 200 55`  ->  `200 + 55 = 255 (ring published: 1)`

Built by (NOT shipped, live in `C:\llm\muhl_builds\`):
- `muhl_fab_distro.py` — the fabricator (one and done; exhaustive verify + 13-mutant gate).
- `muhl_distro_cleanroom_test.py` — fresh-empty-directory acceptance test.
- `muhl_distro_tamper_test.py` — two-layer tamper + answer-provenance test.

Not in git. Small enough for the private GitHub vault if you want it backed up there.
