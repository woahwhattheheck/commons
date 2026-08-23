# SUBZERO_TITAN_PACKET — journaled MOVE packet 2026-08-23

Read-only public-tree packet. This is not a titan write.

`titan.gguf` is the computer. The excerpts in `excerpts/20260823/` are
standalone copies. Git copies do not run. MOVE is an owner-PC step after
a fresh band is allocated locally.

## Law

- Offset request goes in the claim. Do not choose a public band.
- Journal every pre-image. `new = old | mask`. Ones only rise.
- Re-read before every write.
- Fabrication is one-and-done, before runtime, never during.
- Pure stdlib. No host loop over gates. No host schedule.

## Packet

`excerpts/20260823/titan_move_packet.json` is built from every
`*_circuits.json` sidecar in that directory. Each row carries magic,
`n_gate`, `len`, sha256, `offset: 0`, and
`requested_offset_band: OWNER_LOCAL_ALLOCATOR; not chosen in public tree`.

`titan: NOT_WRITTEN` on every row.

## Receipt commands

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_titan_move_packet.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_titan_move_packet.py --dry
```

`--dry` manufactures the packet in memory and writes nothing. It does not
open `titan.gguf`. Do not smash `commons.mno`. Do not remint a landed excerpt.
