# WEATHER SETTLE + HEADER — SPEC MASTER RULING

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-16. Seat: SPEC MASTER GROK.  
**File touched:** `C:\Users\lucys\Desktop\WEATHER\weather.mno` (high-Z read). Titan not opened. 337 not fired. No wipe. No dest invented. Titan 78 not pulsed.

Header law exists so THIS FILE can be addressed with a HIS-parseable layout. Not so the computer stays off.

Σ:WEATHER_SETTLE_HEADER  
verify-host-ok-at-fab **Y**  
runtime-host-executor-as-computer **N**

---

## Live v1 (read off disk this turn)

`weather.mno` **885,346 B**. First 8: `WEATHER1`.

| off | packed as (Cairn v1) | live value | HIS `<IIII` at +8 would name it |
|---:|---|---:|---|
| 0 | 8s magic | `WEATHER1` | magic |
| 8 | I n_gate | **34048** | **n_in** ← WRONG SLOT |
| 12 | I n_wire | **34050** | n_wire |
| 16 | I n_state | **2048** | **n_gate** ← WRONG SLOT |
| 20 | I n_state | **2048** | n_out |
| 24 | I depth | **292** | (5th I; game-class wants W) |
| 28 | I W | 16 | |
| 32 | I H | 16 | |
| 36 | I CELL_BITS | 8 | |
| 40 | I STRIDE | 25 | |
| 44 | Q wire_base | **96** | dest in THIS FILE |
| 52 | Q cell_base | **98** | dest in THIS FILE |
| 60–95 | pad | 0 | |

Computed, not invented: `gate_base = 96 + 34050 = 34146`. Size check: `96 + 34050 + 34048 × 25 = 885346`. Matches disk.

Cell plane @98, first 16 bytes: all `00000000` (row 0). Kite is later (rows 6–9). Plane is addressable now.

Cairn packed 8+`<IIIII>` already. Field **order** is what breaks inspect-class parse.

---

## 1. Header weather_v2 must use

**Magic stays `WEATHER1`.** This file's identity. Already on disk.

Do **not** become:

| magic | why not |
|---|---|
| `PFCGAME1` / `PFCLANGT` / `PFCWIRLD` / `PFCTURNG` / `PFCCYCLE` | those files then emit **9-byte** `<Bii>` index records. Weather records are **25-byte** `<BQQQ>` absolute file addrs. Same count block, different body. Lying magic = wrong walk. |
| `MUHLPKG1` / `LOOMPKG1` | DISTRO/LOOM buttons (`KNOWN_MAGIC`) would take dest from header QWORDs (`ans`/`pub`/`fwd`/`rev`). Weather does not have those mouths. That is inventing dest. `DRY_WALLS.md`: unknown MAGIC → GO REFUSED. Keep it refused. |
| `MUHLDC01` | dc class. Not this computer. |

`pfc_inspect.py` unpacks `<IIII` at +8 as `(n_in, n_wire, n_gate, n_out)` and today only mmaps titan. **Do not run it on titan.** The same 16-byte contract is what a path-pointed inspect would apply to THIS FILE. `pfc_analyzer.py` already takes a file path (64 B channels, no titan). `pfc_game.py` / `pfc_langton.py` / `pfc_speed.py life` use the same count order on isolated files.

HIS isolated count block (evidence: `host/pfc_inspect.py` L22, `host/pfc_game.py` L145, `host/pfc_langton.py` L74, `MUHL_GO/DISTRO_SCALE.md` §2):

```
+8   I  n_in
+12  I  n_wire
+16  I  n_gate
+20  I  n_out
```

DISTRO/LOOM put those four at the same offsets, then a 224 B package map. Weather is not that package. Weather keeps a **96 B** header (v1 window) so records stay at `gate_base`. Do not pad to 224 — that would move every `<BQQQ>` and invent a new dest map.

### Exact v2 struct (96 bytes, little-endian)

```
off   type   field        v1→v2 value (this emit)
0     8s     magic        WEATHER1
8     I      n_in         2048          # state bits = W*H*CELL_BITS
12    I      n_wire       34050
16    I      n_gate       34048
20    I      n_out        2048          # self-clock writes; one per state bit
24    I      W            16            # 5th I = width (PFCLANGT/PFCGAME1 GW slot)
28    I      H            16            # 6th I = height (PFCGAME1 GH slot)
32    I      CELL_BITS    8
36    I      STRIDE       25            # <BQQQ>
40    I      depth        292           # critical-path TICKS, not host wall-clock
44    I      reserved     0
48    Q      wire_base    96            # dest in THIS FILE
56    Q      cell_base    98            # dest in THIS FILE (state[0])
64    Q      gate_base    34146         # dest in THIS FILE (record 0)
72    Q      total        885346        # this emit; rewrite on refab if size moves
80    16s    pad          zeros
```

Pack:

```
magic + struct.pack("<IIIIII", n_in, n_wire, n_gate, n_out, W, H)
      + struct.pack("<IIII", CELL_BITS, STRIDE, depth, 0)
      + struct.pack("<QQQQ", wire_base, cell_base, gate_base, total)
      + b"\x00" * 16
```

Assert `len == 96`.  
`n_in == n_out == W * H * CELL_BITS`.  
`gate_base == wire_base + n_wire`.  
`total == gate_base + n_gate * STRIDE`.  
Addresses in records are **absolute file offsets** in this `.mno`. Never titan. Never 337.

A routing button on this file: read magic `WEATHER1` → unpack the struct → address `cell_base` (surface / OR-mask inject) or `gate_base` (record walk) → fire ONE start if a start mouth is later published in this header → die. Until a start mouth exists in the netlist, do not invent one. Cell plane @98 is the published dest.

v1 surfaces (`surface_weather.py`) unpack `n_gate, n_wire, n_in, n_out, depth` at +8. After v2 refab they must unpack HIS order or they mis-parse. Refab is Cairn's job; this card is the spec.

---

## 2. Settle law (stored gate netlist)

One pulse = one diffusion tick = full combinational depth. Host wall-clock is transcription, never the rate.

1. **Record order.** Combinational (temp) gates evaluate in stored `<BQQQ>` order. Fabricator must emit topo-valid order (Cairn does: per cell, adders then identity write). A later record may read a temp that an earlier record wrote.
2. **Old-state reads.** Any read whose address is in the state plane `[cell_base, cell_base + n_out)` sees the **pre-pulse** bit. Neighbours N/S/E/W are old. Mid-pulse overwrite of a state byte would make later cells see new neighbours = wrong next-state.
3. **Self-clock identity writes.** `OR(src,src) → dst` with `dst ==` that cell's state address. The write is **next-state**. It does not update the old-state view during the same pulse. Commit is the pulse end (or a next-state latch on the same address after combinational settle). One pulse later, that bit is old-state.
4. **One writer.** Each `out` address once per tick. State bytes written exactly once (identity stage).

This is the same law as `pfc_game.py` Life: ripple reads `IN` (old), produces `outs` (next), host latches after the pulse — except weather bakes the latch as identity-write to the same file address. Cairn `simulate()` / `surface_weather.settle()` stash state writes in `nxt` and apply after the record walk. That model matches this law. If a substrate wrote state through in record order, v1's byte-exact vs `cell' = (N+S+E+W)>>2` would be the wrong semantics. It is not: old-state + end-of-pulse identity is the law.

Depth 292 is critical-path TICKS of that combinational walk, not a host loop count.

---

## 3. Verifier: fab-time Y / runtime N

Cairn's host Python ripple (`for (op,a,b,out) in gates`) is **fabrication-time verify**. Allowed.

CLAUDE.md: evaluating gates in host Python is allowed **only** during fabrication, to verify byte-exact **before** store. Never as the running computer.

| when | host ripple | ruling |
|---|---|---|
| fab, before write, vs independent integer ref + mutant battery | `muhl_fab_weather.simulate` / `verify_step` | **Y** — manufacturing check |
| after store, as the thing that "runs weather" | `surface_weather.settle` claimed as the computer | **N** — banned executor |
| after store, high-Z read of `cell_base` / analyzer path / bits surface | read THIS FILE | **Y** — surface |

`surface_weather.py` currently re-ripples to print AFTER. That AFTER is a verify transcription, not a live settle of the file. Live surface = read the bytes at `cell_base`. Whether the live plane has moved is a state reading (settle-back). Do not replace the computer with the verifier.

---

## Return

| question | ruling |
|---|---|
| header | `WEATHER1` + HIS `<IIII>` at +8 = `n_in, n_wire, n_gate, n_out` then `W, H, CELL_BITS, STRIDE, depth, 0` then Q `wire_base, cell_base, gate_base, total` — 96 B. Exact struct above. |
| settle law | record-order temps; old-state reads on the cell plane; self-clock identity writes commit next-state at pulse end |
| verify-host-ok-at-fab | **Y** |
| runtime host executor | **N** |

Address the file. Cell dest is **98**. Gate dest is **34146**. Do not invent another.
