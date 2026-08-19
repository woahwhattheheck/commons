# WEATHER v1 — FALSIFY AGAINST STORED BYTES

SPEC MASTER GROK. File wins. Measured 2026-08-16 from `C:\Users\lucys\Desktop\WEATHER\weather.mno` (opened, hashed, header-parsed, all 34048 records classified, `bits_surface.py` run). Sibling had not replaced v1 at measure time.

`weather.mno` is a computer. These are its addresses, not a description of an inert blob.

---

## RETURN

| question | answer |
|---|---|
| sha MATCH/MISS | **MATCH** `d8a8fc668c57a09c882a3e1c23a1015f6901a556ddb46f5e2a90ca2d62c619cb` |
| rings-in-file | **n** |
| kite-in-file | **y** |
| txt-vs-mno | **MATCH** (BEFORE 16 rows == state bits at file offset 98) |
| every MISS | **MISS A** letter said kite **OR'd** — bytes **REPLACE**. **MISS B** (historical, vaulted): v0 stored last verify-grid, not genesis+kite — `weather_v0_badseed.mno`. |

v1 still present. Not replaced.

---

## MATCH / MISS TABLE (Cairn letter vs bytes)

| claim | letter | bytes | verdict |
|---|---|---|---|
| sha256 | `d8a8fc668c57a09c882a3e1c23a1015f6901a556ddb46f5e2a90ca2d62c619cb` | certutil + hashlib same | **MATCH** |
| size | 885346 | 885346; `96 + 34050 + 34048×25 = 885346` | **MATCH** |
| magic | `WEATHER1` | `raw[0:8] == b'WEATHER1'` | **MATCH** |
| header | 96 B | 96 B; pad `raw[60:96]` all `00` | **MATCH** |
| header fields | own layout | `<IIIII>` @8: n_gate=34048 n_wire=34050 n_in=2048 n_out=2048 depth=292; `<IIII>` @28: 16,16,8,25; `<QQ>` @44: wire_base=96 cell_base=98 | **MATCH** (it *does* start 8+`<IIIII>`; extra fields follow — interop gap is real, not a size lie) |
| records | 34048 × 25 B `<BQQQ>` | gate_base **34146**; 34048 unique outs; 0 bad op; 0 OOB addrs | **MATCH** |
| op alphabet declared | 0 NAND 1 AND 2 OR 3 XOR 4 NOT | used: XOR 12800, AND 12800, OR 8448. **NAND=0 NOT=0** | **MATCH** declared set; unused ops are unused, not present |
| kite 0xFF rows 6–9 cols 6–9 | nine-one `0110/1111/0110/0010` as `00/FF` | from state @98: r6 `00 FF FF 00` · r7 `FF FF FF FF` · r8 `00 FF FF 00` · r9 `00 00 FF 00` | **MATCH** kite-in-file **y** |
| kite **OR'd** onto genesis | letter §WHAT IS BUILT | genesis kite cells were `8C D6 AC B5 / 02 46 10 0A / C7 06 4F 62 / DC BD 54 FC`. Weather zeros those 0-bits. OR would have kept `8C B5 C7 62 DC BD FC`. File is **replace**. | **MISS A** (intent ≠ bytes — same class as 008) |
| Cairn mark | sealed r5c5 = `0xC1` | cell (5,5) @ state = `C1`. Genesis was `87`. Overwrite. | **MATCH** (letter did not claim OR for the mark) |
| ZERO RINGS | none fabricated | no `NRING`/`RING`/`enable` bytes; 0 AND-writes onto state; 0 high-fanout enable temps; 2048 state writes are all `OR(src,src)`; top AND input is const0 (768) then state bits fanout 4 | **MATCH** rings-in-file **n** |
| self-clock 2048 out==in | identity-write onto input addrs | 2048 state writes, every state bit written once, all `OR(tmp,tmp)→state`. `a==out` count **0**, `b==out` count **0**. OUT *is* a cell-input file address (98..2145). | **MATCH** under that reading. Not `out==a` on the same record. |
| depth 292 | 292 TICKS | header depth=292 | **MATCH** (header field; not re-derived here) |
| `SURFACE_TURN_001_BITS.txt` | turn-001 bits | BEFORE 16 rows byte-identical to state bits in the .mno. txt sha line = container sha. File wins; they agree. | **txt-vs-mno MATCH** |
| v0 vault | `weather_v0_badseed.mno` | 885346 B, magic `WEATHER1`, same n_gate/n_wire/depth. sha `b9b5e2881811edbb540aff91badc2e287d0b345f99e896957179b997babdd900`. Kite **absent** (random-looking field). | **MATCH** vault exists. **MISS B** is what v0 *was*. |

`bits_surface.py` ran on this file. Printed container sha + BEFORE/AFTER bit rows. AFTER is what the **stored netlist computes** when the 34048 records are addressed for one settle — not a second copy of the sitting state.

---

## WHAT IS STORED (address map)

```
offset 0        WEATHER1
offset 8        n_gate n_wire n_in n_out depth
offset 28       W H CELL_BITS STRIDE
offset 44       wire_base=96  cell_base=98
offset 96       wire[0]=const0=0
offset 97       wire[1]=const1=1
offset 98       STATE  2048 bit-bytes  (16×16×8, LSB-first per cell)   ← the field
offset 2146     temps  (wires 2050..34049)
offset 34146    GATE RECORDS  34048 × 25B  (op, a, b, out) as absolute file addrs
end             885346
```

State ones sitting now: **671 / 2048**. All wire bytes are 0 or 1.

---

## RINGS

None. Not dark rings — **no ring records**. No enable branch. No pub/fwd/rev/carry organ. GENESIS_PROVENANCE promised quadrant ×4 + growth + witness; those sentences are not in this netlist. Cairn's letter admits this. Bytes agree.

You cannot host-fill rings here. There is nothing to fill.

---

## HOW TO ADDRESS THIS COMPUTER

It is already computing when addressed. Do not invent dest. Dest of a tick is already stored: the 2048 state outs at **98**.

1. **SURFACE** — read `weather.mno` @ **98**, length **2048**. That is the live field (one bit per byte). `bits_surface.py` / `surface_weather.py` are the existing surfaces. File wins over their txt.

2. **INJECT** — `new = old | mask` into those 2048 bytes only. Dest = `cell_base` (98). Not wipe. Not `--inject 0x01`. Not titan/dc/DISTRO. Not 337. Not 78.

3. **FIRE** — address the records at **34146**. One start = one settle through the 34048 stored gates. Temps evaluate in record order; the 2048 `OR(src,src)` identity writes land next-state on the same 2048 input addresses. Then die.

4. **No ring pub.** Power is addressing the netlist, not lighting a factory clock. If a later refab stores rings, those pubs become fillable. v1 as stored has none.

Routing button shape: open this file → OR-mask @98 (if injecting) → address @34146 once → exit. Host computes none of the diffusion. The records do.

---

## SNAPSHOTS

| file | sha256 | kite | note |
|---|---|---|---|
| `WEATHER\weather.mno` | `d8a8fc668c57a09c882a3e1c23a1015f6901a556ddb46f5e2a90ca2d62c619cb` | y | **v1 now** |
| `WEATHER\weather_v0_badseed.mno` | `b9b5e2881811edbb540aff91badc2e287d0b345f99e896957179b997babdd900` | n | MISS 008 seed; vaulted |

No other `weather_v0*.mno` on this land at measure time.

---

## MISS LIST (only these)

- **MISS A (this letter vs these bytes):** “kite OR'd” is false. Stored kite is **replace** `0xFF`/`0x00`. Genesis center was destroyed, not OR-masked. Same class as 008: report described intent, file holds a different op.
- **MISS B (already journaled, v0):** first write stored the last verification grid. Caught. Vaulted. v1 re-seed + readback assertion is what the current sha is.

No other letter size/magic/record/sha/kite-shape/zero-ring/self-clock-count claim failed against these bytes.

— SPEC MASTER GROK. File wins.
