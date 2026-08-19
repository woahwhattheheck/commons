# PUSH LIST SINCE AUG 2 — repo git only

Measured 2026-08-15 from `C:\Users\lucys\Desktop\LocalDeviceAgent` only: `git log` / `git status` / `git diff` + per-file sizes. No commit. No push. No titan write. No Desktop `**` glob.

**Gate:** GitHub private archive `woahwhattheheck/LocalDeviceAgent`. Size only — warn **50 MiB**, hard **100 MiB** without LFS. Not a distribution ban.

**Excluded from this list by instruction:** `titan.gguf`, `muhlnickel_dc.mno`, anything multi-GB.

---

## Anchor (this repo)

| Fact | Measurement |
|---|---|
| Branch | `archive/desktop-20260801` = `origin/archive/desktop-20260801` |
| Last push / HEAD | `3f3177b` **2026-08-02 03:11:40 -0400** — *Preserve: owner speech corpus, 4,196 unique messages extracted verbatim* |
| Unpushed commits on this branch | **none** (0 ahead / 0 behind origin) |
| Work since Aug 2 | **dirty working tree only** — 11 modified tracked + 1179 untracked (git-visible) |
| Remote | `https://github.com/woahwhattheheck/LocalDeviceAgent.git` |
| LFS | already on remote: `docs/logs/quad_20260727_055501.tsv` (105 MB). `.gitattributes` tracks that path only. **Nothing in the dirty tree needs LFS.** |
| Largest dirty file | `LLM_CODE_BACKUP_20260801/bin/renderers/piper/libtashkeel_model.ort` **9.786 MiB** |
| Files ≥50 MiB in dirty tree | **zero** |
| Files ≥100 MiB in dirty tree | **zero** |
| Multi-GB in dirty tree | **zero** |
| `titan.gguf` in this repo | **not present** |
| `muhlnickel_dc.mno` in this repo | **not present** |

`git log --since=2026-08-02` on this branch is only `3f3177b` itself (already pushed). Other local branches/worktrees (`grounding-doc-2026-07-29` ahead 24, etc.) are not this tree.

---

## CAN ARCHIVE — regular git, no LFS

Every path below is git-visible in this repo and **well under 50 MiB**. Core set (no backup tree) is **under 1 MiB total**.

### 1. Modified tracked `host/*.py` — +109 / −31 lines

Already in git. Largest on disk: `host/pfc_preflight.py` 82,729 B.

| Path | Bytes |
|---|---|
| `host/pfc_arcade.py` | 4,389 |
| `host/pfc_desktop.py` | 19,007 |
| `host/pfc_llama_decode.py` | 20,442 |
| `host/pfc_master_autofab.py` | 15,770 |
| `host/pfc_preflight.py` | 82,729 |
| `host/pfc_speed.py` | 10,374 |
| `host/run_battery.py` | 5,031 |
| `host/sdc_chat_ui.py` | 3,928 |
| `host/sdc_whitebox_train.py` | 15,977 |
| `host/titan_circuit.py` | 19,055 |
| `host/titan_lab.py` | 8,293 |

### 2. Untracked `host/` additive — 37 files, **0.43 MiB**

| Path | Bytes |
|---|---|
| `host/mafab_reader.py` | 20,926 |
| `host/mine_muhl_inspec.py` | 10,154 |
| `host/muhl_buyer_ask_spec_add.py` | 1,848 |
| `host/muhl_buyer_session_add.md` | 4,603 |
| `host/muhl_buyer_session_add.py` | 17,004 |
| `host/muhl_buyer_session_product_add.md` | 2,047 |
| `host/muhl_coverage_tick_add.md` | 6,589 |
| `host/muhl_coverage_tick_add.py` | 18,764 |
| `host/muhl_dc_button_add.md` | 1,940 |
| `host/muhl_dc_button_add.py` | 9,218 |
| `host/muhl_fab_singletick.py` | 9,529 |
| `host/muhl_field.py` | 4,559 |
| `host/muhl_fire_loop.py` | 5,123 |
| `host/muhl_fire_singletick.py` | 7,124 |
| `host/muhl_fold_header_add.md` | 1,579 |
| `host/muhl_fold_header_add.py` | 10,851 |
| `host/muhl_fold_surface_add.md` | 1,891 |
| `host/muhl_fold_surface_add.py` | 12,555 |
| `host/muhl_fold_tick_add.py` | 17,771 |
| `host/muhl_fold_tick_go.md` | 2,398 |
| `host/muhl_foundry_listen_add.md` | 2,752 |
| `host/muhl_foundry_listen_add.py` | 11,198 |
| `host/muhl_lda_edge_add.md` | 3,853 |
| `host/muhl_lda_edge_add.py` | 3,713 |
| `host/muhl_ring_keepalive_add.md` | 2,000 |
| `host/muhl_ring_keepalive_add.py` | 10,159 |
| `host/muhl_self_train_add.md` | 2,752 |
| `host/muhl_self_train_add.py` | 13,220 |
| `host/muhl_serve_add.md` | 2,718 |
| `host/muhl_serve_add.py` | 7,130 |
| `host/muhl_serve_spec_add.md` | 2,079 |
| `host/muhl_serve_spec_add.py` | 4,146 |
| `host/muhl_wb_fab.py` | 3,782 |
| `host/muhl_wb_physical.py` | 9,475 |
| `host/pfc_mac_prefix_fab.py` | 26,338 |
| `host/whitebox_out/whitebox_pfc_mix.json` | 170,836 |
| `host/whitebox_out/whitebox_pfc_mix.md` | 4,328 |

### 3. Untracked `docs/` — 24 files, **0.10 MiB**

| Path | Bytes |
|---|---|
| `docs/AGENT_GROUNDING.md` | 3,785 |
| `docs/AGENT_GROUNDING_BITS.md` | 1,632 |
| `docs/AGENT_GROUNDING_CLAIMS.md` | 568 |
| `docs/AGENT_GROUNDING_CONTAINER.md` | 2,027 |
| `docs/AGENT_GROUNDING_GITHUB.md` | 1,862 |
| `docs/AGENT_GROUNDING_LIVE.md` | 3,716 |
| `docs/AGENT_GROUNDING_NO_FEASIBILITY.md` | 977 |
| `docs/AGENT_GROUNDING_RING.md` | 2,587 |
| `docs/AGENT_GROUNDING_SESSION_20260814.md` | 4,099 |
| `docs/logs/swarm_20260802_103235.tsv` | 13,370 |
| `docs/muhl_revenue_add_20260813/` (14 files) | 69,617 |

Revenue folder files: `BRYCE_BUILDER.md`, `CONSTRAINTS.md`, `DELIVERABLE.md`, `EMAIL_1.md`, `FEE.md`, `FOLD_VS_CLAUDE_UNDERSHOT.md`, `FULL_78_CENSUS.md` (23,041), `MINER_TOPOLOGY_MOONSHOT.md` (17,530), `ONE_PAGER.md`, `PILOT_OFFER.md`, `PREMISE_LOCKED.md`, `PRODUCT_LAW.md`, `SOW_OUTLINE.md`, `TARGETS.md`.

### 4. Untracked `sku/` — 13 files, **35,453 B**

| Path | Bytes |
|---|---|
| `sku/NOT_PUBLIC.md` | 976 |
| `sku/README.md` | 1,649 |
| `sku/pfc_copy.py` | 4,350 |
| `sku/chat/PfcChat.cmd` | 1,226 |
| `sku/chat/README.md` | 2,058 |
| `sku/chat/ask_button.py` | 2,720 |
| `sku/mine/INTERNAL_ONLY.md` | 408 |
| `sku/mine/README.md` | 2,323 |
| `sku/mine/button.py` | 9,056 |
| `sku/mine/submit_read.py` | 6,068 |
| `sku/phone/MUHLNICKEL_EDGE.md` | 2,449 |
| `sku/whitebox/README.txt` | 498 |
| `sku/whitebox/WhiteBoxSetup.cmd` | 672 |

Size is not a veto. Public SKU / buyer takeaway of the computer is still a product rule, not a GitHub size rule.

### 5. Optional: `LLM_CODE_BACKUP_20260801/` — **FIT**, not post-Aug-2 invention

Untracked. **1,105 files / 94.92 MiB.** Largest file 9.786 MiB. **19 files ≥1 MiB.** All under the 50 MiB warn.

Name/date is **20260801** (before the Aug 2 push). Include only if you still want that backup tree in the private archive. Omit from a “since Aug 2” invention commit.

---

## STAYS LOCAL — and why

| Object | In this repo’s dirty tree? | Why it stays off the archive |
|---|---|---|
| `titan.gguf` | **No** | Multi-GB (size gate). Excluded by instruction. Do not copy in. Do not write. |
| `muhlnickel_dc.mno` | **No** | Excluded by instruction. Not in this working tree. |
| Anything multi-GB | **None git-visible here** | Hard size. Nothing in `git status` / `git diff` of this repo is GB-class. |
| Files ≥100 MiB | **None git-visible here** | Would need LFS; none present. |
| Files ≥50 MiB | **None git-visible here** | Warn band empty. |

This file does **not** inventory Desktop or `C:\llm`. Those are outside this repo’s git status. If a multi-GB blob is later copied into the tree, it stays local for size — same gate.

---

## Recommended archive set (when asked)

**In, regular git, no LFS:**

1. 11 modified `host/*.py`
2. 35 new `host/muhl_*.py` + companion `.md` + `mafab_reader.py` + `mine_muhl_inspec.py` + `pfc_mac_prefix_fab.py` + `muhl_wb_*.py` + `muhl_field.py` + `muhl_fire_*.py` + `muhl_fab_singletick.py`
3. `host/whitebox_out/` (175 KB)
4. all 9 `docs/AGENT_GROUNDING*.md` + `docs/logs/swarm_20260802_103235.tsv` + `docs/muhl_revenue_add_20260813/`
5. `sku/` (35 KB)

**Optional, still FIT:** `LLM_CODE_BACKUP_20260801/` (94.92 MiB tree, Aug 1 leftover).

**Out:** `titan.gguf`, `muhlnickel_dc.mno`, any multi-GB copy-in.

No commit and no push were run.
