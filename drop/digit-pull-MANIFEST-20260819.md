# digit-pull MANIFEST

Pulled 2026-08-19 ~2:30–2:40pm ET from Bryce's laptop (`C:\Users\lucys`, ExternalShell/ExternalRead + CopyToBox).
Additive staging only. Nothing written to GitHub / Commons. Nothing posted to ntfy.
Do not fire 337. Do not smash commons.mno. Do not pulse titan 78.

**Copied: 46 files** under `/workspace/digit-pull/{host,lda,whitebox,dest}/`.

Already-on-commons checks used local `C:\Users\lucys\Desktop\COMMONS` (not a clone this session). Only `dests.txt` was found at the Commons root. `COMMONS\lda` is just `app\src`. `COMMONS\host\pfc_*.py` is absent.

---

## host/ — PFC instruments (live LDA host)

Source tree unless noted: `C:\Users\lucys\Desktop\LocalDeviceAgent\host\`

| dest | bytes | original | already on commons? | why gem |
|---|---:|---|---|---|
| host/pfc_load.py | 7283 | …\LocalDeviceAgent\host\pfc_load.py | NO (no COMMONS\host\pfc_load.py) | Named install instrument: maps a model onto the pfc as software; does not recreate inference. |
| host/pfc_harness.py | 7535 | …\LocalDeviceAgent\host\pfc_harness.py | NO | Named harness: address / read / push only; pfc CPU does the compute. |
| host/pfc_meter.py | 3752 | …\LocalDeviceAgent\host\pfc_meter.py | NO | Named high-impedance multimeter; bounded mmap probe, no ripple. |
| host/pfc_scope.py | 2629 | …\LocalDeviceAgent\host\pfc_scope.py | NO | Named oscilloscope: traces one probe over time. |
| host/pfc_analyzer.py | 8626 | …\LocalDeviceAgent\host\pfc_analyzer.py | NO | Named logic analyzer: multi-channel timing from existing probes. |
| host/pfc_step.py | 5620 | …\LocalDeviceAgent\host\pfc_step.py | NO | Named stepper instrument. |
| host/pfc_diff.py | 5775 | …\LocalDeviceAgent\host\pfc_diff.py | NO | Named diff instrument. |
| host/pfc_cascade.py | 6387 | …\LocalDeviceAgent\host\pfc_cascade.py | NO | Named cascade instrument. |
| host/pfc_assert.py | 2863 | …\LocalDeviceAgent\host\pfc_assert.py | NO | Named assertion checker; read-only live-state vs reference. |
| host/pfc_inspect.py | 2644 | …\LocalDeviceAgent\host\pfc_inspect.py | NO | Named schematic inspector; header-only (≤64 B). SESSION_GROUNDING test. |
| host/pfc_speed.py | 10374 | …\LocalDeviceAgent\host\pfc_speed.py | NO | Named electron-speed / DEPTH probe. SESSION_GROUNDING test: `pfc_speed life`. |
| host/pfc_cpu32.py | 10697 | …\LocalDeviceAgent\host\pfc_cpu32.py | NO | Named 32-bit CPU instrument. SESSION_GROUNDING test: `pfc_inspect pfc_cpu32`. |
| host/pfc_paths.py | 1293 | …\LocalDeviceAgent\host\pfc_paths.py | NO | Tiny PFC_ROOT path helper used by the other instruments. |
| host/pfc_preflight.py | 82729 | …\LocalDeviceAgent\host\pfc_preflight.py | NO | Largest live host instrument (82 KB); PUSH_LIST names it as dirty-tree gem. |
| host/LIVE_INSTRUMENTS.md | 17644 | C:\Users\lucys\Desktop\MUHL_GO\LIVE_INSTRUMENTS.md | not at COMMONS root | Hour inventory of live instruments, from file. |
| host/INSTRUMENTS_THIS_HOUR.md | 4010 | C:\Users\lucys\Desktop\MUHL_GO\INSTRUMENTS_THIS_HOUR.md | not at COMMONS root | Short instrument census for the hour. |
| host/MUHL_INSTRUMENTS.md | 84278 | C:\Users\lucys\Desktop\MUHL_INSTRUMENTS.md | not at COMMONS root | Desktop instrument catalog (his English). |

Duplicates NOT copied: same `pfc_*.py` set also lives under LDA worktrees (`grounding-doc`, `checker-v61-addressed`, …), COMMONS_PLAYER1_* mirrors, FINISHED_20260801, AUTOFAB_* snapshots.

---

## lda/ — leftovers that are NOT signing

| dest | bytes | original | already on commons? | why gem |
|---|---:|---|---|---|
| lda/SESSION_GROUNDING.md | 7895 | C:\Users\lucys\Desktop\MUHL_GO\SESSION_GROUNDING.md | NO | Canonical living on-ramp (POINTER_TO_MUHL_GO). |
| lda/POINTER_TO_MUHL_GO.md | 638 | C:\Users\lucys\Desktop\POINTER_TO_MUHL_GO.md | not at COMMONS root | Home/Desktop pointer to SESSION_GROUNDING. |
| lda/DESKTOP_MUHL_INDEX.md | 11770 | C:\Users\lucys\Desktop\MUHL_GO\DESKTOP_MUHL_INDEX.md | not at COMMONS root | Desktop tree index leftover. |
| lda/ON_THIS_PC.md | 7202 | C:\Users\lucys\Desktop\MUHL_GO\ON_THIS_PC.md | not at COMMONS root | What actually lives on this machine. |
| lda/LDA_ON_MUHL.md | 1218 | C:\Users\lucys\Desktop\MUHL_GO\LDA_ON_MUHL.md | not at COMMONS root | LDA leftover note vs Muhlnickel. |
| lda/KEEP_CURRENT.md | 15142 | C:\Users\lucys\Desktop\KEEP_CURRENT.md | not at COMMONS root | Working/broken/needs-work inventory from file. |
| lda/START_HERE.md | 13136 | C:\Users\lucys\Desktop\LocalDeviceAgent\START_HERE.md | NO (no COMMONS\lda\START_HERE.md) | LDA repo on-ramp. |
| lda/AUTHORSHIP.md | 4962 | C:\Users\lucys\Desktop\LocalDeviceAgent\AUTHORSHIP.md | not at COMMONS\lda | Inventor / authorship leftover. |
| lda/NEW_SESSION_PROMPT.md | 19888 | C:\Users\lucys\Desktop\LocalDeviceAgent\NEW_SESSION_PROMPT.md | not at COMMONS\lda | Session leftover prompt. |
| lda/FILE_STRUCTURE.md | 8592 | C:\Users\lucys\Desktop\LocalDeviceAgent\docs\FILE_STRUCTURE.md | not at COMMONS\lda | LDA file-structure leftover. |
| lda/INDEX.md | 35522 | C:\Users\lucys\Desktop\LocalDeviceAgent\docs\INDEX.md | not at COMMONS\lda | LDA docs index. |
| lda/WHAT_THE_PFC_IS.md | 10479 | C:\Users\lucys\Desktop\LocalDeviceAgent\docs\WHAT_THE_PFC_IS.md | not at COMMONS\lda | PFC definition leftover. |
| lda/HARNESS.md | 8670 | C:\Users\lucys\Desktop\LocalDeviceAgent\docs\HARNESS.md | not at COMMONS\lda | Harness leftover doc. |
| lda/AGENT_GROUNDING.md | 4000 | C:\Users\lucys\Desktop\LocalDeviceAgent\docs\AGENT_GROUNDING.md | not at COMMONS\lda | Agent grounding leftover. |
| lda/LDA_PFC_INTEGRATION.md | 34801 | C:\Users\lucys\Desktop\LocalDeviceAgent\docs\LDA_PFC_INTEGRATION.md | not at COMMONS\lda | LDA↔PFC leftover integration notes. |
| lda/PUSH_LIST_SINCE_AUG2.md | 7617 | C:\Users\lucys\Desktop\MUHL_GO\PUSH_LIST_SINCE_AUG2.md | not at COMMONS root | What is/isn't archived since Aug 2 (from file). |
| lda/SURFACE_ALL.md | 4054 | C:\Users\lucys\Desktop\MUHL_GO\SURFACE_ALL.md | not at COMMONS root | UI/visor leftover (not a dest-address list). |

COMMONS\lda currently only contains `app\src` — these leftover docs look unpublished there.

---

## whitebox/ — inventories FROM FILE only

No invented inventory. Only files that already list whitebox material.

| dest | bytes | original | already on commons? | why gem |
|---|---:|---|---|---|
| whitebox/FILE_MAP.md | 10676 | C:\Users\lucys\Desktop\FILE_MAP.md | NO | Drive-wide map including White Box corpus paths/sizes (from file). |
| whitebox/MUHL_WHITEBOX_TREE_MAP.md | 6088 | C:\Users\lucys\Desktop\MUHL_WHITEBOX_TREE_MAP.md | NO | What is actually built/working in the whitebox tree (from file). |
| whitebox/WHITEBOX_DISTRO_README.md | 9370 | C:\Users\lucys\Desktop\WHITEBOX_DISTRO\README.md | not at COMMONS root | Distro README: 13-tab instrument, no inference. |
| whitebox/WhiteBox_Research_Archive_README.md | 965 | C:\Users\lucys\Desktop\WhiteBox_Research_Archive\README.md | not at COMMONS root | Archive coverage table (8 models) from file. |
| whitebox/WHITEBOX_ALL_MODELS_summary.md | 6793 | C:\Users\lucys\Downloads\WHITEBOX_ALL_MODELS.md | not at COMMONS root | Short 6.8 KB summary twin (FILE_MAP: MD5 F8D82E6EF7CA). |
| whitebox/Fable_Whitebox_v2.md | 13207 | C:\Users\lucys\Desktop\Fable_Whitebox_v2.md | not at COMMONS root | Fable v2 field notes listed in FILE_MAP. |
| whitebox/whitebox_titan.md | 4354 | C:\Users\lucys\Desktop\TitanSDC\whitebox_titan.md | not at COMMONS root | Titan-specific whitebox output listed in FILE_MAP. |

---

## dest/ — dest lists FROM FILE only

No invented addresses. Only files that already publish dests.

| dest | bytes | original | already on commons? | why gem |
|---|---:|---|---|---|
| dest/dests.txt | 1370 | C:\Users\lucys\Desktop\COMMONS\dests.txt | YES (Commons root) | Published table_mail + commons.mno Homes dests FROM FILE. |
| dest/DEST_IS_THE_MACHINE.md | 2560 | C:\Users\lucys\Desktop\MUHL_GO\DEST_IS_THE_MACHINE.md | NO | Surfaces existing ans/pub dests (SEED0/DISTRO/dc) already in the files. |
| dest/LIVE_MOUTHS.md | 1535 | C:\Users\lucys\Desktop\MUHL_GO\LIVE_MOUTHS.md | not at COMMONS root | Live mouth/addr/surface table FROM FILE. |
| dest/MNO_DS_17_table_mail.md | 2425 | C:\Users\lucys\Desktop\MUHL_GO\MNO_DS_17_table_mail.md | not at COMMONS root | table_mail datasheet; dests published FROM FILE (CAIRN inj@704 etc). |
| dest/muhl_surface_table.py | 11789 | C:\Users\lucys\Desktop\LocalDeviceAgent\host\muhl_surface_table.py | not at COMMONS\host | Host script dests.txt names: surfaces table_mail dests FROM FILE. |

---

## SKIPPED (found, not copied)

| path | size | reason |
|---|---|---|
| C:\llm\models\titan.gguf | 103803350291 (~96.7 GB) | gguf forbidden; do not dump |
| C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno | 99999999783 (~93 GB) | huge binary; do not inject / do not fire 337 |
| C:\Users\lucys\Desktop\MUHL_COMMONS\commons.mno | 17683 | do not smash commons.mno |
| C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno | 136450 | container binary, not a dest-list text |
| C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0.mno and sibling *.mno (ACREAGE_*, GERM_*, GIG*, MOVE_*, NEW_MNO, SEED0_*) | various | containers, not dest-list text |
| C:\Users\lucys\Desktop\LocalDeviceAgent\app\debug.keystore | 2666 | APK signing keystore |
| C:\Users\lucys\.android\adbkey (+ adbkey.pub) | 1732 | adb private key |
| C:\Users\lucys\Desktop\WHITEBOX_DATA_DUMP.md | 2357368 | >200 KB dump |
| C:\Users\lucys\Desktop\WhiteBox_Research_Archive\WHITEBOX_ALL_MODELS.md | 1717195 | >200 KB full dump (summary copied instead) |
| C:\Users\lucys\Desktop\WhiteBox_Research_Archive\ (tree) | ~15 GB / 7792 files | huge archive; README only |
| C:\Users\lucys\Desktop\BIBLE.md | 11044389 | huge; not in WANT list |
| C:\Users\lucys\Desktop\LocalDeviceAgent\docs\OWNER_SPEECH_EXTRACT.txt | 2827158 | huge speech extract |
| C:\Users\lucys\Desktop\LocalDeviceAgent\docs\MASTER_PLAN.md | 324419 | >200 KB |
| C:\Users\lucys\Desktop\LocalDeviceAgent\docs\PFC_FINDINGS.md | 216317 | >200 KB |
| C:\Users\lucys\Desktop\LocalDeviceAgent\docs\pfc_gallery.html | 8395085 | huge html |
| C:\Users\lucys\Desktop\LocalDeviceAgent\docs\TITAN_SCAN.json | 1242119 | huge json |
| C:\Users\lucys\Desktop\LocalDeviceAgent\docs\PATENT_SUPPORT.md | 552302 | >200 KB |
| C:\Users\lucys\Desktop\RING_OSCILLATION_MECHANISM.md | 259500 | >200 KB |
| C:\Users\lucys\Desktop\LocalDeviceAgent\Unconfirmed 673677.crdownload | 15992595884 | abandoned download |
| C:\Users\lucys\Desktop\LocalDeviceAgent\host\pfc_infer.py | 5298 | recreates inference |
| C:\Users\lucys\Desktop\LocalDeviceAgent\host\pfc_llama_decode.py | 20442 | inference decoder |
| C:\Users\lucys\Desktop\LocalDeviceAgent\host\pfc_llama_harness.py | 34015 | inference harness |
| C:\Users\lucys\Desktop\LocalDeviceAgent\host\pfc_engine.py | 18905 | engine / inference-adjacent |
| C:\Users\lucys\Desktop\LocalDeviceAgent\host\pfc_model.py / pfc_modelbuild.py / pfc_modelforge.py | various | model-build / inference-adjacent |
| LDA worktree copies of host/pfc_*.py | many | duplicates of live host |
| COMMONS_PLAYER1_* mirrored pfc_*.py | many | publish-pack duplicates |
| C:\Users\lucys\.ssh\ | (not dumped) | credentials |
| C:\Users\lucys\.claude.json and tmp siblings | 30–65 KB | session state / possible tokens |
| C:\Users\lucys\lda-build\app | build tree | build/signing-adjacent leftover, not docs |
| Desktop patent PDFs / zips / MUHLNICKEL_PATENT_* | multi-MB | binaries / filing packages |
| C:\llm\models\ (other .gguf) | 289 GB class | gguf forbidden |

`rg` is not on PATH on this Windows box; used targeted Get-ChildItem / ExternalRead instead of a find/grep storm.

## Blockers

None. ExternalShell worked. Machine present (`bryceslaptop\lucys`, `C:\Users\lucys`). No approval denial.

Parent should PUT from `/workspace/digit-pull/` — this agent did not.
