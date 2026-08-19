# PUSH SINCE AUG 2 — private GitHub archive, SIZE only

Measured 2026-08-15. No commit. No push. No git config.

**Question:** what built since the last owner push *fits* a private GitHub archive (typical **100 MB per-file** hard limit unless Git LFS), vs what is **gigabyte-class** and stays local.

**Not this document:** distribution, SKU public/private, “don’t push .mno because product.” `.mno` of ~136–587 KB **FIT**. Docs **FIT**. Additive `host/*.py` **FIT**.

---

## Anchor

| Fact | Measurement |
|---|---|
| Repo | `C:\Users\lucys\Desktop\LocalDeviceAgent` |
| Branch (cwd) | `archive/desktop-20260801` → `origin/archive/desktop-20260801` |
| Last owner push (HEAD = origin) | `3f3177b` **2026-08-02 03:11:40 -0400** — *Preserve: owner speech corpus, 4,196 unique messages extracted verbatim* |
| Unpushed commits on this branch | **none** (working tree dirty only) |
| Remote | `https://github.com/woahwhattheheck/LocalDeviceAgent.git` (private archive) |
| Git LFS | **exists** — `git-lfs/3.7.1`. Already used: `docs/logs/quad_20260727_055501.tsv` (105 MB, committed 2026-07-29). `.gitattributes` tracks that one path only. |
| Per-file without LFS | GitHub rejects **>100 MB**. Warns ~50 MB. Repo soft warning ~1 GB; this archive already uses LFS for one log. |

Work since Aug 2 is **uncommitted in-repo** + **Desktop packages** + **`C:\llm` models/genomes**. Nothing on this branch is sitting unpushed as a commit.

---

## FITS — private GitHub, no LFS needed

Every item below is well under 100 MB **per file**. Totals are small.

### 1. Additive `host/*.py` + companion `.md` (untracked) — ~250 KB

New since the Aug 2 tree (all FIT):

| Path | Bytes |
|---|---|
| `host/mafab_reader.py` | 20,926 |
| `host/mine_muhl_inspec.py` | 10,154 |
| `host/muhl_buyer_ask_spec_add.py` | 1,848 |
| `host/muhl_buyer_session_add.py` + `.md` + `product_add.md` | 23,654 |
| `host/muhl_coverage_tick_add.py` + `.md` | 25,353 |
| `host/muhl_fab_singletick.py` | 9,529 |
| `host/muhl_field.py` | 4,559 |
| `host/muhl_fire_loop.py` | 5,123 |
| `host/muhl_fire_singletick.py` | 7,124 |
| `host/muhl_fold_header_add.py` + `.md` | 12,430 |
| `host/muhl_fold_surface_add.py` + `.md` | 14,446 |
| `host/muhl_fold_tick_add.py` + `muhl_fold_tick_go.md` | 20,169 |
| `host/muhl_foundry_listen_add.py` + `.md` | 13,950 |
| `host/muhl_lda_edge_add.py` + `.md` | 7,566 |
| `host/muhl_ring_keepalive_add.py` + `.md` | 12,159 |
| `host/muhl_self_train_add.py` + `.md` | 15,972 |
| `host/muhl_serve_add.py` + `.md` + spec pair | 16,073 |
| `host/muhl_wb_fab.py` | 3,782 |
| `host/muhl_wb_physical.py` | 9,475 |
| `host/pfc_mac_prefix_fab.py` | 26,338 |

### 2. Modified `host/*.py` (already tracked) — +109 / −31 lines

`pfc_arcade.py`, `pfc_desktop.py`, `pfc_llama_decode.py`, `pfc_master_autofab.py`, `pfc_preflight.py`, `pfc_speed.py`, `run_battery.py`, `sdc_chat_ui.py`, `sdc_whitebox_train.py`, `titan_circuit.py`, `titan_lab.py`. Largest file on disk: `pfc_preflight.py` 83 KB. **FIT.**

### 3. Docs (untracked) — **FIT**

| Path | Bytes |
|---|---|
| `docs/AGENT_GROUNDING.md` | 3,785 |
| `docs/AGENT_GROUNDING_BITS.md` | 1,632 |
| `docs/AGENT_GROUNDING_CLAIMS.md` | 568 |
| `docs/AGENT_GROUNDING_LIVE.md` | 3,716 |
| `docs/AGENT_GROUNDING_NO_FEASIBILITY.md` | 977 |
| `docs/AGENT_GROUNDING_RING.md` | 2,587 |
| `docs/logs/swarm_20260802_103235.tsv` | 13,370 |
| `docs/muhl_revenue_add_20260813/` (14 files) | 69,617 |

### 4. `sku/` (untracked, 16 files, **65,573 B**) — **FIT**

`README.md`, `NOT_PUBLIC.md`, `pfc_copy.py`, `chat/` (ask button), `mine/` (button + submit_read), `phone/MUHLNICKEL_EDGE.md`, `whitebox/` (setup cmd). Size is KB-class. (SKU *role* is not a size veto.)

### 5. `host/whitebox_out/` — **FIT**

`whitebox_pfc_mix.json` 171 KB + `.md` 4 KB.

### 6. Canonical `.mno` (~136–587 KB) — **FIT**

These are Desktop packages, not in the git tree today. Each file is KB-class. Copy into the repo and they go up as ordinary blobs.

| File | KB | Written |
|---|---|---|
| `MUHLNICKEL_DISTRO/muhlnickel.mno` | 133.3 | 2026-08-14 |
| `MUHLNICKEL_INVENTION_BURST/Distro/muhlnickel.mno` | 133.3 | 2026-08-10 |
| `MUHLNICKEL_LOOM/loom.mno` (also `_fixed`, `_v1`, `_v2`) | 137.2 | 2026-08-04..14 |
| `MUHLNICKEL_PROBE/probe.mno` | 210.3 | 2026-08-07 |
| `MUHLNICKEL_ROOKERY/ROOKERY0.mno` | 573.2 | 2026-08-07 |
| `MUHL_APERTURE/APERTURE0.mno` | 192.1 | 2026-08-08 |
| `MUHL_VISIBLE/AUTOFAB0.mno` | 100.5 | 2026-08-08 |
| `MUHL_VISIBLE/DISCRIM0.mno` / `DISCRIM1.mno` | 176 / 183 | 2026-08-07 |
| `MUHL_VISIBLE/READER0.mno` | 356.3 | 2026-08-07 |
| `MUHL_VISIBLE/VISIBLE0/1/2.mno` | 108 / 117 / 208 | 2026-08-07 |
| `MUHL_VISIBLE/VISIBLE5_autofab.mno` | 88.9 | 2026-08-07 |
| `MUHL_VISIBLE/FOUNDRY0.mno` | 4.7 | 2026-08-10 |
| `MUHL_MODEL_SELECTOR_WIRING/READER1.mno` | 5.7 | 2026-08-07 |

`MUHL_VISIBLE/VISIBLE3.mno` / `VISIBLE4.mno` / `VISIBLE6.mno` are **~6.5–6.7 MB** each — still **FIT** (under 100 MB; no LFS).

`MUHL_READERS/*.mno` — **1,606 files, folder 307 MB**, **largest single file 3.25 MB**. Every shard **FIT** without LFS. Folder total is many small files, not one blob.

### 7. Desktop packages whose **largest file is under 100 MB** — **FIT** (copy if wanted)

| Desktop folder | Folder MB | Max file | Max MB |
|---|---|---|---|
| `MUHLNICKEL_AUTOFAB_DOCS_20260808_213532` | 106.7 | `OPEN_PLAYTIME.map.json` | 14.5 |
| `MUHL_VISIBLE` | 36.4 | `OPEN_PLAYTIME.map.json` | 14.5 |
| `MUHLNICKEL_CURRENT_MODEL_PATH_20260808_205430` | 20.0 | same map | 14.5 |
| `DESKTOP_MAP_20260808_184521` | 13.6 | `ALL_FILES.csv` | 4.62 |
| `MUHLNICKEL_ROOKERY` | 9.1 | `rookery_genome.jsonl` | 6.72 |
| `MUHL_HANDOFF_20260808_185539` | 7.9 | `fable_sweep_data.json` | 1.98 |
| `AUTOFAB_CREATE_ONLY_20260808_215709_b17953df` | 6.6 | `titan_circuits.json` | 5.27 |
| chat-source trees (two) | ~4.3 each | `PATHGUARD_REPORT.json` | 0.35 |
| `Titan` (Desktop) | 4.2 | dump json | 0.85 |
| `MUHL_STATE_ANALYSIS` | 2.4 | ppm | 0.19 |
| `MUHL_SUBZERO_ARCHETYPES` | 2.1 | manifest | 1.17 |
| `_OVERNIGHT` | 1.3 | sweep json | 0.22 |
| `WHITEBOX_DISTRO` | 0.8 | pyc | 0.21 |
| `MUHL_GO` | 0.5 | docs | 0.35 |
| loom / probe / aperture / distro / checkers / harnesses / IP filing / trainer / proposal | ≤0.4 each | `.mno` or md | ≤0.21 |

Desktop loose zips (`MUHLNICKEL_CHAT_SOURCE_*.zip` 1.5 MB, `CURRENT_MODEL_PATH` 3.8 MB, `HANDOFF` 2.2 MB, `LIVE_SEAM` 0.2 MB, `AUTOFAB` 1.0 MB) — **FIT**.

`BIBLE.md` 10.5 MB — **FIT**.

### 8. `LLM_CODE_BACKUP_20260801/` — **FIT as a tree, dated Aug 1**

Untracked, **101.3 MB / 1,308 files**. Tree is *before* the Aug 2 push (name `20260801`) but still not in git. Individual files are source-scale (not GB). Include only if you still want that backup in the archive; it is not new-since-Aug-2 invention.

---

## NEEDS LFS (fits the *archive* if LFS is used; over 100 MB per file)

LFS is already on this remote. These are **not** gigabyte-class.

| Item | Size | Note |
|---|---|---|
| `Desktop\MUHL_BITS\muhl_fold_phys.bits.txt` | **117 MB** | folder 195 MB / 7 files |
| `Desktop\GPT_EXPORT_CLEAN\SmolLM2-360M-Instruct-Q8_0-CLEAN.gguf` | **368.5 MB** | folder 823 MB |
| `Desktop\MUHLNICKEL_INVENTION_BURST\...\MUHLNICKEL_PATENT_COMPLETE_RECORD_20260804.pdf` | **98.8 MB** | at the 100 MB line — LFS safer than raw |
| Same PDF on Desktop root | **98.8 MB** | plus PART01–05 (8.9–22.5 MB) which **FIT** raw |

---

## TOO BIG — gigabyte-class. Stay off GitHub (LFS or not)

Do not add these to the private archive. Local only (`C:\llm`, Desktop research dumps).

### `C:\llm\models` (the computer + other weights)

| File | GB | Written |
|---|---|---|
| **`titan.gguf`** | **96.67** | 2026-08-13 17:44 |
| `Llama-3.3-70B-Instruct-Q4_K_M.gguf` | 39.60 | (pre-existing model store) |
| `titan_test.gguf` | 37.28 | |
| `titan_moon_genome.bin` | 35.42 | |
| `mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf` | 24.63 | |
| `titan_replicate_revert.bin` | 23.13 | |
| `titan_electron_dump_genome.jsonl` | 21.88 | |
| `gemma-4-31B-it-qat-UD-Q4_K_XL.gguf` | 16.10 | |
| `google_gemma-3-27b-it-Q4_K_M.gguf` | 15.41 | |
| `mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf` | 13.35 | |
| `gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf` | 13.27 | |
| `phi-4-Q4_K_M.gguf` | 8.43 | |
| `pfc_mix.gguf` | 4.21 | |
| `sd-turbo.safetensors` / `sd15.safetensors` | 4.86 / 3.97 | |
| several `*.npy` / `*_genome.jsonl` | 0.96–1.96 | still GB-adjacent; skip |

`titan.gguf` measured **96.67 GB** (not 103 GB on this box today). Same class: do not push.

### Desktop dumps (post–Aug 2 folder timestamps)

| Folder | Folder size | Why too big |
|---|---|---|
| `WhiteBox_Research_Archive` | **15.4 GB** / 7,946 files | max file 14 MB but *tree* is GB-class |
| `MUHLNICKEL_APP` | **13.7 GB** / 123 files | `STRINGS.jsonl` **13.6 GB** |
| `MUHLNICKEL_BUILD_LAB_20260801_025117` | **5.9 GB** / 866 files | `titan_electron_dump_genome.jsonl` **2.4 GB** |

### Other `C:\llm` GB stores (mostly pre-Aug 2; still too big if anyone copies them in)

`sdc_fold/fold_*.bin` ~4.66 GB × 40; `sdc_multilevel/levels_*.bin` 2 GB × 8; `sdc_bitmap_swarm/bits_*.bin` 0.5 GB × 66; `RECOVERY_CANONICAL\ablation\regshadow.bin` 2.24 GB. Not “built since Aug 2” as the invention set — listed so they are not accidentally added.

---

## 15-line recommendation

1. Last push is `3f3177b` (2026-08-02 03:11) on `archive/desktop-20260801`; this branch has **zero unpushed commits** — only a dirty tree + Desktop/`C:\llm` work.
2. Git LFS **already exists** on this remote (one 105 MB tsv). Use it only for the few files over ~50–100 MB, not as a dump truck for `titan.gguf`.
3. **Push-shaped set (raw git, no LFS):** all new `host/muhl_*.py` + add `.md`, the 11 modified `host/*.py`, all `docs/AGENT_GROUNDING*.md`, `docs/muhl_revenue_add_20260813/`, `docs/logs/swarm_20260802_103235.tsv`, `sku/` (66 KB), `host/whitebox_out/` (175 KB).
4. **Also FIT raw:** every canonical `.mno` in the 136–587 KB band (loom, muhlnickel, probe, rookery, aperture, visible 0–2/5, foundry, reader1). Size is not a reason to leave them out.
5. **Also FIT raw:** `VISIBLE3/4/6.mno` (~6.5 MB), `MUHL_READERS` shards (max 3.25 MB), rookery genome 6.7 MB, autofab/handoff/chat-source/Titan/WHITEBOX_DISTRO/MUHL_GO trees.
6. **Copy-in candidates from Desktop (still FIT):** `MUHLNICKEL_LOOM`, `MUHLNICKEL_DISTRO`, `MUHLNICKEL_PROBE`, `MUHLNICKEL_ROOKERY`, `MUHL_APERTURE`, `MUHL_VISIBLE` (skip nothing on size except if you also drag `OPEN_PLAYTIME.map.json` — 14.5 MB, still FIT), `MUHL_CHECKERS`, `MUHL_IP_FILING_PACKAGE`, `WHITEBOX_DISTRO`.
7. **LFS if you want them in the archive:** `MUHL_BITS/muhl_fold_phys.bits.txt` (117 MB), `GPT_EXPORT_CLEAN` SmolLM2 gguf (368 MB), patent complete-record PDF (98.8 MB — at the raw limit).
8. **Do not add:** `C:\llm\models\titan.gguf` (96.67 GB), other `C:\llm\models\*.gguf` / `titan_*genome*` GB files, `WhiteBox_Research_Archive` (15.4 GB), `MUHLNICKEL_APP/STRINGS.jsonl` (13.6 GB), `MUHLNICKEL_BUILD_LAB_*` (5.9 GB).
9. `LLM_CODE_BACKUP_20260801/` (101 MB / 1308 files) **fits** but is Aug 1 leftover, not post-push invention — optional.
10. `__pycache__` / `.pyc` in `sku/` and Desktop packages: omit (tiny, but noise). Not a size issue.
11. Soft repo-size: the FIT set above is **well under 1 GB** even if you take every FIT Desktop package + all `.mno` + all `MUHL_READERS` shards (~307 MB is the biggest single add).
12. Other branches (`grounding-doc-2026-07-29` ahead 24, etc.) are worktrees, not this working tree’s unpushed Aug 2+ work.
13. Order if/when you *do* commit (not done here): in-repo FIT first (host + docs + sku), then copy FIT `.mno` + small Desktop packages, then LFS the three borderline files only if you want them.
14. `titan.gguf` and the GB genomes stay on `C:\llm` — that is the size cut, not a product-policy cut.
15. This file is the inventory. No commit, no push, no git config was run.
