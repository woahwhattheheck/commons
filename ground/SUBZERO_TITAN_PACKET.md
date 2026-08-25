# SUBZERO_TITAN_PACKET — journaled MOVE packet 2026-08-23

Public-tree packet with dest-FROM-FILE claimed append offsets.
This is not a titan write until `host/titan_move_apply.py --go`.

`titan.gguf` is the computer. The excerpts in `excerpts/20260823/` are
standalone copies. Git copies do not run.

## Law

- Claimed append offsets dest FROM FILE (`titan.gguf` size
  103803350291). Apply reallocates if live size differs.
- Journal every pre-image. `new = old | mask`. Ones only rise.
- Re-read before every write.
- Fabrication is one-and-done, before runtime, never during.
- Pure stdlib. No host loop over gates. No host schedule.

## Packet

`excerpts/20260823/titan_move_packet.json` is built from every
`*_circuits.json` sidecar in that directory. Each row carries magic,
`n_gate`, `len`, sha256, a nonzero `offset` packed from
`claimed_append_base` 103803350291, and
`requested_offset_band: CLAIMED_APPEND dest FROM FILE titan_size=103803350291`.

`titan: NOT_WRITTEN` on every row until apply + reread.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_titan_move_packet.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_titan_move_packet.py --dry
python3 host/titan_move_dry.py
python3 host/titan_move_apply.py --journal
python3 host/titan_move_apply.py
```

`--dry` manufactures the packet in memory and writes nothing. It does not
open `titan.gguf`. `--journal` OR-writes the 31 excerpt binaries and
rereads. `host/titan_move_apply.py --go` writes only when the file is
present. Do not smash `commons.mno`. Do not remint a landed excerpt.
Card: [TITAN_MOVE.md](./TITAN_MOVE.md).
