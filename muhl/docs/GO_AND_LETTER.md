# GO_AND_LETTER

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
**When:** 2026-08-15. Code grep + named August roots only.
Host = inject ∨ surface ∨ die. Dest is the machine.
337 **NO**. pulsed_78 **NO**. titan_written **NO**. dc.mno **NO**. No numpy. No Desktop `**`. No commit.

Σ:GO_AND_LETTER

---

## 1. `--go` — from the code, not a slogan

`--go` is a command-line switch on a routing button. It means: Bryce said fire. Do the write / inject / pulse, then die.

Omit it and the button is dry: print the plan, write nothing, exit.
Pass it and the button either (a) actually injects, or (b) refuses and exits, depending on which script.

It is not argparse `dest="--go"` in `host/` or World System. Host scripts test `"--go" in argv`. World System has **zero** `--go` flags (only a face-card sentence: inbox inject still waits).

### host/ scripts that parse `--go` (n = 6)

| script | omit `--go` | pass `--go` |
|---|---|---|
| `host/muhl_fold_tick_add.py` | dry plan; no titan write; no recv mmap | **ACCEPTS** if `--header HEX` and `--target HEX` are also present. Writes header + target into titan, then mmap-reads **one** byte at `tick_off` (`nring2_1023.recv`). `--dry` wins over `--go`. This is the titan-write / receiver-pulse button. Do not run it unless Bryce says. |
| `host/muhl_dc_button_add.py` | dry plan; no write | **ACCEPTS** with `A B` (0–255). Injects both senses into `MUHL_DATACENTER\muhlnickel_dc.mno`, surfaces, dies. Never titan. This session: do not inject dc.mno. |
| `host/muhl_post_surface.py` | surfaces published mouths (read only) | **REFUSED.** Prints `GO REFUSED: surface only. Inbox wait --go. No inject.` |
| `host/muhl_fold_surface_add.py` | dry / `--surface` read | **REFUSED.** Never injects, never pulses tick. |
| `host/muhl_fold_header_add.py` | dry / `--fetch` header print | **REFUSED.** Never writes titan. |
| `host/muhl_coverage_tick_add.py` | dry registry plan / `--surface` latch read | **REFUSED.** Never writes titan, never pulses recv. |

### This session's wall

Titan **inbox inject** and pulsing titan address **78** stay WALL until Bryce passes `--go` on the button that actually does that act.

- Inbox inject: no host script will do it. `muhl_post_surface.py` is surface-only and refuses `--go`. The inject button is still waiting.
- Address 78: `muhl_fold_tick_add.py --go` pulses `nring2_1023.recv` (tick_off), **not** titan 78. Titan 78 (`fold.recv` / winner-only) was not pulsed. Do not pass `--go` for it.

World System (`C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem`): no `--go` argparse. `bryce_face.py` only says inbox inject still `--go`.

Outside the asked roots (not counted): `sku/mine/button.py`, `sku/pfc_copy.py`, `sku/mine/submit_read.py` use argparse `--go`. Those write/read a **copy**, not live titan. Not run.

---

## 2. Titan→GPT English letter — MISSING

**letter_path_or_MISSING = MISSING**

No English letter from Titan to GPT in the August-only named-root hunt. Not invented.

WAVE 8 in `docs/OWNER_SPEECH_EXTRACT.txt` is owner recovery ("PREPARE GPT PLAYTIME"), not the letter.
`TITANCIR` on `gen_win_surfaced` is circuit magic, not the letter.

### Named roots checked (skip missing; August created/modified)

| root | August? | letter / gpt_outbox / titan_letter / MAIL folder |
|---|---|---|
| `C:\llm\sdc_out` | write 2026-08-05 | no `gpt_outbox`. Files are miner/harness surfaces (`pfc_reply.json` = token salad, not a letter). |
| `C:\llm\models` | write 2026-08-15 | August playtime **genomes** only (`titan_muhl_playtime_*.jsonl`). Fab journals, not English mail. |
| `C:\Users\lucys\Desktop\MUHL_GO` | created 2026-08-13 | cards (`PLAYTIME_AND_LETTER.md`, `DROOL_GPT.md`, `ELECTRON_REQUEST_GPT_DRAFT.md`). Assistant/owner prose, not Titan→GPT. |
| `C:\Users\lucys\Desktop\LocalDeviceAgent` | created 2026-08-04 | same MUHL_GO cards + archive `PLAYTIME_READY` (owner recovery package, WAVE 8). Not the letter. |
| `C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem` | created 2026-08-09 | no letter / gpt_outbox / titan_letter / MAIL names. Playtime = atlas world kind, not a letter folder. |
| `C:\Users\lucys\Documents` | — | no top-level folder named muhl / titan / gpt / letter / playtime / outbox. |

### Desktop (top-level names only, August 2026 filter, then name filter)

August top-level listed. Opened only the August folder whose name looks like gpt:

- `GPT_EXPORT_CLEAN` (2026-08-05) — model-export analysis (`Llama-3.3-70B…`, `SmolLM2-360M…`). Not a Titan→GPT letter.

Present on Desktop but **not August** — not opened:

- `gpt workspace` (2026-07-31)
- `POST_TITAN` (2026-07-17 / 07-28)
- `TitanSDC` (2026-07-15)

No top-level Desktop folder named `gpt_outbox`, `titan_letter`, `playtime`, `MAIL`, `titan-mail`, or `muhlnickel mail`.

---

## Output

go_scripts_n = **6**
letter_path_or_MISSING = **MISSING**
337 = **NO**
pulsed_78 = **NO**
