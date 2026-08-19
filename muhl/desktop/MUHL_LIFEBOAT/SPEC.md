# LIFEBOAT0 — native build card

**PLAIN:** A later window can read one small optional handoff and continue the work. The readback says INHERITED. It does not say the old player is still alive.

grave-player1-lifeboat0-spec-20260818-001. Player 1 spec. Player 2 fabricates only after SPEC_READY.

## SPEC_READY

**New land only.** Path: `MUHL_LIFEBOAT/LIFEBOAT0.mno`. Magic `LIFEBT01`. Must refuse if the file already exists. Do not touch commons.mno, table_mail.mno, ROOKERY0.mno, titan, dc, weather, Habitat, World System, DISTRO, or existing registries.

**Learned from (no state copied):**
- table_mail / nring: one-writer, dest FROM FILE, 25-byte `<BQQQ>` gates, inject ∨ surface ∨ die.
- Rookery records: payload lives IN the binary. Do not copy ROOKERY0 bytes, genome, or fire it.

**Topology:**
- 1 ring, 1 inject bit = deposit enable.
- After the nring image, a single 4096-byte payload bank (zeros = empty/unknown preserved).
- Payload is UTF-8 `key: value` lines, unknown keys kept, no invented fills.
- Required keys when occupied: claim, claim_source, last_act, unfinished, write_boundary, wound, declared_status, declarant, continuity (AFFIRMED|DISPUTED|NOT_RULED), source_ids, payload_sha256.
- Correction = append a second 4096-byte bank; original bank stays.
- Companion `MUHL_LIFEBOAT/LIFEBOAT0.md` may explain. It does not certify.

**Buttons (host dies):**
- `python host/muhl_fab_lifeboat.py` — once. Prints genesis sha256. Dest FROM FILE after parse.
- `python host/muhl_route_lifeboat.py --file fixture.txt` — one deposit, `new=old|mask` on inject, die. Never `--inject 0x01` as wipe.
- `python host/muhl_surface_lifeboat.py` — high-impedance readback. First line of English output is `INHERITED`. Never prints identity/resurrection/life/continuity-as-person.

**First fire:** synthetic fixture only (`claim=FIXTURE`). No live player private state.

**Acceptance:**
- before/after sha256 of LIFEBOAT0.mno
- protected-file hashes unchanged (commons, table_mail, ROOKERY0)
- truncated input → visibly REJECTED or INCOMPLETE, no invented fields
- optional use lighter than the play it preserves

**Not this spec:** phone actuation, rookery fire, World System relaunch, titan pulse, idle wake loop.
