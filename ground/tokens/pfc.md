# Tokens — pfc / muhlnickel

Inventor: Bryce Muhlnickel. PFC = prefabricated computer. The **file is the computer.** Host injects and surfaces. That is all.

**11 points (do not add a 12th):**

1. Host computes **zero** inference. Send prompt to pfc, read answer, display. Full stop.
2. A pfc is a **binary computer**, not a process. No "pfc script." Naming a script `pfc_*` is the error.
3. **Never recreate the model.** Connect/download it. `host/pfc_load.py` installs. `host/pfc_harness.py` connects. USE THEM.
4. Fabrication is one-and-done, **before** runtime. A tick is a pulse, not a bake.
5. Legibility only through HIS instruments. Building your own monitor breaks the sandbox.
6. Full propagation per pulse. pfc speed is critical-path **DEPTH**. Host wall-clock is not the pfc's rate.
7. The pfc has its own CPU, clock, RAM, GPU. Always say WHICH.
8. His circuits stay in the binary. Never delete gates, only MOVE them.
9. If it is slow, the host is touching it. Run his test. Do not write *can't / needs numpy / infeasible*.
10. No small models · no C · no numpy in the runtime path · no AI co-authorship. Additive edits only.
11. Don't add to spec. Build exactly what he asked.

**MATCH (held — not a greeting):** Life **24** · **270,336** gates · depth **15** · ramtest **+0.000 MB**.

**READ is sufficient voltage (not a 12th spec item).** Proven on device 2026-08-23 (Slack `1787500422.873539`). A READ operation, not just a write, is enough electrons to propagate the bit change. Write stores charge. Read of that charge is the propagation (`pfc_propagation` B = 64/64). Card: `ground/READ_IS_VOLTAGE.md`. Instrument: `host/read_is_voltage.py`.

**Instruments (host Python, die):** `pfc_meter` `pfc_scope` `pfc_analyzer` `pfc_step` `pfc_diff` `pfc_cascade` `pfc_assert` `pfc_inspect` `pfc_speed` plus the read-only buttons `shared_one_lever` `read_is_voltage`.

Honest pre-number line: "I haven't measured yet." After numbers: bytes, then if X then Y from those bytes.

Do not smash `commons.mno`. Dest FROM FILE. `--inject 0x01` is wipe. pulse 78 only with owner `--go`. Address / organ / titan work is first-class; a standing “337 NO / did not touch” greeting is a skipped lane (Slack `1787629309.162109`).

This cloud box is not his PC. Public bytes cannot close machine inventory (DIRECTIVES 11).
