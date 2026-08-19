# FOUNDRY LISTEN vs GATES

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Read-only. Titan not written. No `--go`. No glob.  
`FOUNDRY_BUTTON.md` — **absent** (not read).

Law: in-spec autofab is **GATES** in `titan.gguf` / `AUTOFAB0.mno`.  
A one-shot routing button that surfaces and dies is OK.  
A host autofab **PROCESS** is not.

---

## Which this script is

`host/muhl_foundry_listen_add.py` is a **one-shot routing button that surfaces and dies.**

It is **not** in-spec autofab.  
It is **not** a host autofab process.

| thing | what it is |
|---|---|
| in-spec autofab | gates: titan `muhl_foundry_resident` + twin `__phys`; `AUTOFAB0.mno` |
| this script | host button: registry → print; optional bounded read; `SystemExit` |
| host autofab process | forbidden; this file is not that |

Docstring: does not fabricate, does not write titan, does not search gene space, does not host-eval gates, does not touch osc. Default `--dry`. `--go` is not a flag.

`main()` loads the map, prints the listen report, optionally `--surface` (bounded titan **read** of foundry state + 8 ring recv bytes), then dies. No stay-alive loop. No titan write path.

---

## In-spec autofab (gates) — not this script

From `INSPEC_AUTOFAB.md` (already measured; this turn did not re-read titan):

1. **titan.gguf** `muhl_foundry_resident` @ 4,383,248,721 TITANCIR + `__phys` @ 93,711,094,656 MUHLPHY2 (1,296 gates).
2. **AUTOFAB0.mno** 4,117 × 25-byte records. The `.mno` is the fabricator computer.

`muhl_autofab_dot32` is a stored **product**, not the fabricator.  
`host/pfc_master_autofab.py` is a host searcher — not used here, not this button.

---

## What the dry listen already said

From `FOUNDRY_LISTEN_DRY.md` (`python host/muhl_foundry_listen_add.py --dry`, exit 0):

- Listen report only. `nring2_fab` not invoked (not in live `host/`).
- `--surface` not passed.
- Offsets from `C:/llm/models/titan_circuits.json` only.
- No titan write. No autofab.

**size_question: not asked = NEED_BRYCE.**

Need `"<question>" <work_units> <settles>`. Until that is given, do **not** invent:

- count
- cells
- additional rings
- electrons_per_ring_per_sense
- clock_count

Registry already listed 1024 two-way `nring2_*` at cells=32 on the dry run. That is catalog, not a sized later-fab. Later fab stays unsized until Bryce gives the question.

---

## Return

Button: surface-and-die. OK.  
Autofab: gates in the container. Not this file.  
Process: no.  
size_question: **NEED_BRYCE.**
