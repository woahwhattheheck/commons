# SUBZERO_TITAN_PACKET — journaled MOVE packet 2026-08-23

Public-tree packet with the completed owner-PC append and reread evidence.
The earlier structural packet was not a Titan write; the current packet is.

`titan.gguf` is the computer. The excerpts in `excerpts/20260823/` are
standalone copies. Git copies do not run.

## Law

- Initial claimed append offsets came dest FROM FILE (`titan.gguf` size
  103803350291). Only a first NOT_WRITTEN apply can allocate from live EOF;
  APPLYING/WRITTEN packets keep their fixed offsets.
- Journal every pre-image. `new = old | mask`. Ones only rise.
- Re-read before every write.
- Atomically persist `APPLYING` with fixed offsets before the first write;
  retry resumes, and `WRITTEN` reruns are read-only exact verification.
- Fabrication is one-and-done, before runtime, never during.
- Pure stdlib. No host loop over gates. No host schedule.

## Packet

`excerpts/20260823/titan_move_packet.json` is built from every
`*_circuits.json` sidecar in that directory. Each row carries magic,
`n_gate`, `len`, sha256, a nonzero `offset` packed from
`claimed_append_base` 103803350291, and
`requested_offset_band: CLAIMED_APPEND dest FROM FILE titan_size=103803350291`.

Current execution fields are `titan=WRITTEN`, `state=INTEGRATED`,
`wrote=true`, `reread=true`, `reread_count=31`, `past_eof_count=31`,
sizes **103803350291 → 103812669582**, and `written_bytes=9319291`.
The RIVET aliases remain additive and exact: `write_count=31` and
`live_size_before/live_size_after` equal the canonical Titan size fields.
Receipt: `p/claudelocal-titan-move-go-20260825-01.md`.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_titan_move_packet.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_titan_move_packet.py --dry
python3 host/titan_move_dry.py
python3 host/titan_move_apply.py --journal
python3 host/titan_move_apply.py
```

`--dry` manufactures a structural candidate in memory and writes nothing.
A non-dry generator preserves a matching complete WRITTEN packet and
refuses any inconsistent regression to NOT_WRITTEN. On the landed packet,
`--journal` leaves the historical public journal unchanged. With the file
present, `host/titan_move_apply.py --go` rereads the fixed spans without
writing or reallocating. Do not smash `commons.mno`. Do not remint a landed
excerpt or either prior Titan id: `claudelocal-titan-move-go-20260825-01`,
`dio-titan-move-truth-reconcile-20260825-01`.
Card: [TITAN_MOVE.md](./TITAN_MOVE.md).
