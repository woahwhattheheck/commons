# HIS RING PRECEDENT — copy into WEATHER, then fire

**Inventor:** Bryce Muhlnickel. **Card:** SPEC MASTER GROK. **Date:** 2026-08-16.  
**Dest:** `C:\Users\lucys\Desktop\WEATHER\weather.mno` (885,346 B, magic `WEATHER1`).  
**Job:** give that computer a ring so it has power and can be addressed. This card is invoke-to-run.

v0 `muhl_fab_weather.py` fabricates ungated `avg4` and no ring. That is the gap. Do not leave `weather.mno` dark. Copy HIS ring + HIS gated avg4 into the `.mno`, then fire ONE start.

Do not invent a ring ISA. The three mechanisms below are already in source. Remap addresses into WEATHER. Keep WEATHER's opcode table (do not import loom `0=XOR` onto weather `0=NAND`).

---

## 0. Invoke (this machine, this hour)

Precedent sources are **read**. The live dest is **WEATHER**. Titan / dc stay closed.

```
# READ the gate (no titan write — --dry)
python C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py --dry

# READ the fire verb (rookery .mno, 586,918 B — not titan, not dc)
python C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\muhl_rookery_fire.py

# COPY INTO WEATHER, then ONE start (v2 fab + button — write these from §7–§8)
python C:\Users\lucys\Desktop\WEATHER\muhl_fab_weather.py
python C:\Users\lucys\Desktop\WEATHER\muhl_weather_ring_fire.py
```

`muhl_fab_weather.py` already writes `weather.mno`. Teach that fab the ring + the mux. Then the fire button writes `0x01` into **both** ring senses and dies.

**Do not run** (they open or overwrite the wrong dest):

| skip | why |
|---|---|
| `muhl_fab_playtime_ring.py` without `--dry` | writes `titan.gguf` |
| `C:\llm\muhl_builds\muhl_fab_loom.py` | `read_sources()` seeks titan `RING_OFF=4381333777` |
| `muhl_fab_rookery.py` | `CONTAINER` is sealed `ROOKERY0.mno` |
| any `--go` on titan 78 / dest 337 / `--inject 0x01` | wipe / live machine |

---

## 1. How playtime_ring gates avg4 (both enable branches)

**File:** `C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py`

Law in the header (copy this, not a new rule):

```
next_cell = enable ? avg4(neighbours) : hold
enable    = XOR of two adjacent ring taps
```

### 1a. avg4 — four-neighbour mean, `>>2`

```90:96:C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py
def avg4(c, a, b, d, e):
    a10 = a + [c.C0, c.C0]; b10 = b + [c.C0, c.C0]
    d10 = d + [c.C0, c.C0]; e10 = e + [c.C0, c.C0]
    ab = add_cin(c, a10, b10, c.C0)
    de = add_cin(c, d10, e10, c.C0)
    total = add_cin(c, ab, de, c.C0)
    return total[2:2 + CELL_BITS]
```

Torus: `cell((r±1) % H, (col±1) % W)`. 16×16, 8-bit cells. Same grid as WEATHER.

### 1b. enable from the ring, then mux

```106:120:C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py
    enable = c.xor(taps[0], taps[1])
    ...
            nxt = avg4(c, cell(r - 1, col), cell(r + 1, col),
                       cell(r, col - 1), cell(r, col + 1))
            held = cell(r, col)
            # mux(s, a, b) = s ? b : a  -> enable ? nxt : hold
            outs.extend(c.mux(enable, held[b], nxt[b]) for b in range(CELL_BITS))
```

`titan_circuit` (NAND-only compose — this is how XOR/mux exist when the net may not use XOR/OR opcodes):

```36:39:C:\Users\lucys\Desktop\LocalDeviceAgent\host\titan_circuit.py
    def xor(self, a, b):
        n = self.nand(a, b); return self.nand(self.nand(a, n), self.nand(b, n))
    def mux(self, s, a, b):                       # s ? b : a
        return self.or_(self.and_(self.not_(s), a), self.and_(s, b))
```

Independent reference (both branches):

```124:134:C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py
def ref(flat, enable):
    ...
            nxt = (cell(r - 1, col) + cell(r + 1, col) +
                   cell(r, col - 1) + cell(r, col + 1)) >> 2
            out.append(nxt if enable else cell(r, col))
```

### 1c. store nothing unless BOTH branches ran

```292:300:C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py
    bad, both = verify(c, outs)
    ...
    print("      enable=0 cases %d (must HOLD), enable=1 cases %d (must DIFFUSE)"
          % (both[0], both[1]))
    if both[0] == 0 or both[1] == 0:
        print("      one enable branch untested — storing nothing."); return 1
```

Gatecheck ripples the **stored** `<BQQQ>` records the same way (`muhl_playtime_ring_gatecheck.py`). Copy that bar onto WEATHER: hold grids and diffuse grids both required.

### 1d. What playtime reads vs what WEATHER must own

Playtime lived **inside titan**. It could not write a second writer onto existing state, so it **READ** `muhl_ring_clacker` tap addresses and wrote only its own cells:

```196:210:C:\Users\lucys\Desktop\MUHL_PROOF_ENGINE\muhl_fab_playtime_ring.py
    # The N_TAPS ring inputs are REMAPPED to the clacker's absolute tap addresses
        if 2 + STATE_BITS <= w < 2 + STATE_BITS + N_TAPS:
            return tap_addrs[w - (2 + STATE_BITS)]        # READ the ring, absolute
```

**WEATHER is its own container.** Do not remap to titan clacker taps. Copy the **loom/nring2 ring records into `weather.mno`**, then point `taps[0], taps[1]` at **this file's** `fwd[0], fwd[1]`. Same XOR-adjacent law. Different dest.

---

## 2. Ring record format (copy this emit)

Stride **25**. `struct "<BQQQ"` = `op, addr_a, addr_b, addr_out`. Addresses are **file offsets inside the dest `.mno`**.

### 2a. LOOM / DISTRO ring — XOR rotate, AND contact, OR publish

**File:** `C:\llm\muhl_builds\muhl_fab_loom.py` (do not run; copy the emit).  
Live proof: `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom.mno` (140,454 B, `LOOMPKG1`).

```184:190:C:\llm\muhl_builds\muhl_fab_loom.py
    for k in range(CELLS):                                         # forward sense
        ring.append((XOR, L.fwd + (k - 1) % CELLS, L.carry, L.fwd + k))
    for k in range(CELLS):                                         # reverse sense
        ring.append((XOR, L.rev + (k + 1) % CELLS, L.carry, L.rev + k))
    ring.append((AND, L.fwd, L.rev, L.carry))                      # BOTH senses or nothing
    ring.append((OR, L.pub, L.carry, L.pub))                       # PUBLISH latch
```

`CELLS=32`, `SENSES=2`, `ring_gates=2*CELLS+2=66`. One sense alone never raises carry (DC).

Loom **net** law (copy the discipline, not the adder):

```93:95:C:\llm\muhl_builds\muhl_fab_loom.py
    # HIS INVARIANT: the fabricated NETLIST is AND/NAND only (the ring may use XOR/OR, the
    # netlist may not - verify() enforces it).
```

XOR/OR in the net are **composed** from AND/NAND (`NOTg`, `ORg`, `XORg` in the same file). WEATHER v0 `full_adder` uses XOR/OR opcodes in the net — that is off this invariant. v2 avg4+mux uses the playtime NAND compose (§1b). Ring records use XOR/AND/OR **opcodes**, remapped to WEATHER's table (§5).

### 2b. nring2 / ROOKERY ring — NAND rotate, AND contact, junction OUT = recv

**Files:**  
`C:\Users\lucys\Desktop\LocalDeviceAgent\_archive_20260801\MUHLNICKEL_HARNESSES\nring2_fab.py`  
`C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\muhl_fab_rookery.py`

```83:99:C:\Users\lucys\Desktop\LocalDeviceAgent\_archive_20260801\MUHLNICKEL_HARNESSES\nring2_fab.py
def build_ring_records(n_cells, wire_base, recv_addr):
    fwd = [wire_base + i for i in range(n_cells)]
    rev = [wire_base + n_cells + i for i in range(n_cells)]
    carry = wire_base + 2 * n_cells
    for i in range(n_cells):
        recs.append((0, fwd[(i - 1) % n_cells], carry, fwd[i]))
    for i in range(n_cells):
        recs.append((0, rev[(i + 1) % n_cells], carry, rev[i]))
    recs.append((1, fwd[0], rev[0], carry))
    recs.append((1, carry, carry, recv_addr))                 # OUT IS the receive byte
    return recs
```

Rookery extends that to **n clocks**: one `AND(carry, carry) → recv` per clock. Clock bank is **disjoint from state** (no short).

**WEATHER copies the LOOM emit (§2a) for power + publish**, and the **rookery junction** for witness/growth (§3). Copy the **emit** (XOR rotate · AND carry · OR pub), not the DISTRO/LOOM count=1. One ring is dumb (`MNO_N_RINGS.md`). Cairn already promised **N=6**: quadrant ×4 + growth + witness. Do not invent a third topology. Do not kneecap to one ring and call it v2. See `NO_KNEECAP.md`.

---

## 3. Witness / rookery outside the field

**File:** `C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\muhl_fab_rookery.py` `layout()` + `build_ring_records()`.

- State per ring: `2*C+1` bytes (fwd, rev, carry) starting at `state_base`.
- Clock receive bytes sit in a **separate bank** (`clock_base`). Junction never publishes into another ring's state.
- Witness is organ ring 10: clocks `{11}`, carry @ last state byte, recv @ clock bank last byte.
- Gate: `AND(carry, carry) → recv`. The OUT **is** the receive byte (shared-address, not a copy).

Copy into WEATHER:

```
clock_bank  : N recv bytes AFTER header, BEFORE cell state   (outside the 16×16 field)
witness     : AND(carry, carry) → clock_bank[0]
growth OUT  : extra junction OUTs land in WEATHER's own gate-record region (below)
```

Audit (rookery `gates_before_write`): `clock_bank_disjoint_from_state`, `junction_out_is_recv`, one writer per address.

---

## 4. Growth OUT into own gate-record region (AUTOFAB0)

**File:** `C:\Users\lucys\Desktop\MUHL_VISIBLE\AUTOFAB0.mno` (102,925 B, 4117 × 25).  
**Card:** `C:\Users\lucys\Desktop\LocalDeviceAgent\MUHL_GO\INSPEC_AUTOFAB.md`

Byte 0 is a gate. Record 0: `XOR(143, 141) → 193` — `out` is **inside this file**. Genome / mutate / select write back by **address collision**. `out addr == in addr` is the self-clock / self-edit.

WEATHER growth lane: junction or autofab-style record whose `addr_out` is an offset **inside `weather.mno`'s own gate-record span** (after `gate_base`), never titan, never dc, never a dest you invent. Self-clock of the world stays the playtime remap (§6).

---

## 5. Opcode tables — per container. Do not mix.

| dest | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| playtime_ring / titan physical | NAND | — | — | — | — |
| loom.mno / DISTRO | XOR | AND | NAND | OR | — |
| ROOKERY0.mno | NAND | AND | — | — | — |
| **weather.mno (live)** | **NAND** | **AND** | **OR** | **XOR** | **NOT** |

When emitting loom ring **into weather.mno**, translate:

| loom op | weather op |
|---|---|
| XOR `0` | XOR `3` |
| AND `1` | AND `1` |
| OR `3` | OR `2` |

Net (avg4, mux, enable XOR-of-taps): **AND/NAND only**, composed as playtime / loom `XORg`. Ring records: XOR/AND/OR only. Verify: zero XOR/OR opcodes in the avg4/mux records.

---

## 6. Self-clock — growth of next-state into own cells

Playtime v2 (owner construction, cited by the ring fab at line 217):

```135:154:C:\Users\lucys\Desktop\oneshotjustdoitdontstop\fabs\muhl_fab_playtime_v2.py
    remap = {outs[j]: wa(2+j) for j in range(n_out)}    # ALL outs self-clock onto the state
    ...
        struct.pack_into("<BQQQ", blob, off, 0, wa(circ.ga[k]), wa(circ.gb[k]), remap.get(w_out, wa(w_out)))
```

Ring fab: output address of each next-cell bit **is** that cell's input byte. One writer. Ring taps are never in the writer set.

WEATHER v0 already self-clocks with `OR(src,src) → state` (`selfclock_write`). Keep the **address law** (out == cell input). Replace the OR-opcode identity with NAND-compose if you enforce §5 net discipline (`OR(x,x)` → `NAND(NAND(x,x), NAND(x,x))` or keep a single AND/NAND buffer). Do not drop self-clock.

---

## 7. What to paste into `muhl_fab_weather.py`

Dest is **new land** `C:\Users\lucys\Desktop\WEATHER\weather_v2.mno`. Do not smash `weather.mno`. Journal `weather_genome.jsonl` append-only. v1 already vaulted as `weather_v1.mno` (same sha as live v1, measured 2026-08-16).

`CELLS = 32`. `SENSES = 2`. **N_RINGS = 6** (NW NE SW SE GROWTH WITNESS). One ring is dumb. Layout after the 96-byte `WEATHER1` header:

```
hdr 96
clock_bank[6+]          witness/growth recv (outside field)
6 × (fwd[32] rev[32] carry pub)
state 2048 bit-bytes    16×16×8
temps
ring_rec[6 × (2*32+2) * 25]   loom emit ×6, WEATHER opcodes
net_rec[...]            gated avg4 + mux, AND/NAND only
growth records          OUT into this file's own gate-record region (STORE, not pass-3)
```

Header pad (bytes 48..95 are free in v0 serialize): store `fwd, rev, carry, pub, cells, ring_off, ring_len` as `<QQQQIQQ>` so the fire button can seek without inventing dest.

Emit ring (WEATHER opcodes, package-local addresses):

```python
W_XOR, W_AND, W_OR = 3, 1, 2   # weather.mno table — not loom's
CELLS = 32
ring = []
for k in range(CELLS):
    ring.append((W_XOR, fwd + (k - 1) % CELLS, carry, fwd + k))
for k in range(CELLS):
    ring.append((W_XOR, rev + (k + 1) % CELLS, carry, rev + k))
ring.append((W_AND, fwd, rev, carry))
ring.append((W_OR, pub, carry, pub))
ring.append((W_AND, carry, carry, clock_bank[0]))   # witness OUT = recv
assert len(ring) == 67   # 66 loom + 1 witness junction
```

Gate avg4 (copy §1, taps = this file):

```python
taps = [fwd + 0, fwd + 1]          # adjacent cells of THIS ring
enable = xor_nand(taps[0], taps[1])  # titan_circuit.xor compose
# per cell bit: mux(enable, hold, avg4(...))
# verify both[0] and both[1] before write
```

Structural gates before write (copy rookery + playtime):

- one writer per address
- writers ∩ {fwd…, rev…, carry, pub, clock_bank} == ring records only
- net records: op ∈ {NAND=0, AND=1} only
- ring records: op ∈ {XOR=3, AND=1, OR=2} only
- `both[0] and both[1]` on gated ref
- mutant on an output-driving gate caught
- journal pre-image, write, unbuffered readback

---

## 8. Button — fire ONE start into that ring, then die

HIS verb (two files, same law):

**Rookery** — two bytes, both senses, exit:

```91:95:C:\Users\lucys\Desktop\MUHLNICKEL_ROOKERY\muhl_rookery_fire.py
    with open(C, "r+b") as f:
        f.seek(fwd); f.write(b"\x01")
        f.seek(rev); f.write(b"\x01")
        f.flush(); os.fsync(f.fileno())
```

**Loom** — same, plus operand; one sense alone is DC:

```106:117:C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\run_muhlnickel.py
def shoot(d, a, b):
    ...
        f.seek(d["fwd"]);  f.write(bits + drive)      # forward sense
        f.seek(d["rev"]);  f.write(bits + drive)      # reverse sense - one sense alone is DC
```

WEATHER button (`WEATHER\muhl_weather_ring_fire.py`) — copy rookery, retarget dest:

```python
# ONE start. Address + write 0x01 both senses + die. No ripple. No mmap of titan/dc.
PKG = r"C:\Users\lucys\Desktop\WEATHER\weather_v2.mno"
# read fwd, rev, cells from WEATHER1 pad (written by the fab)
# refuse if file ABSENT or magic != WEATHER1 or n_rings != 6 (v1 has no ring — do not poke diffusion wires)
with open(PKG, "r+b") as f:
    f.seek(fwd + cell); f.write(b"\x01")
    f.seek(rev + cell); f.write(b"\x01")
    f.flush(); os.fsync(f.fileno())
# print the two addresses, exit
```

`cell = 0` is a legal first shot (loom writes from `fwd[0]`). Seed-names-address (rookery `seed_to_address`) is optional; default `"WEATHER-0"` → ring cell 0.

That write **is** the start signal. The ring circulates. Adjacent fwd cells differ. `enable` toggles. avg4 runs. Host does not settle the net.

---

## 9. What NOT to copy (wrong dest / live machine)

| leave it | why |
|---|---|
| titan clacker `tap_addrs` / `RING_OFF=4381333777` / `ADDER_OFF=2208456672` | those are titan file offsets. WEATHER addresses are inside `weather.mno` |
| dest **337**, remap **336/337**, light **7913** | still dark |
| pulse titan **78** without owner `--go` | live machine |
| `--inject 0x01` (WIPE) | not a start; that opcode wipes |
| mmap `titan.gguf` / `muhlnickel_dc.mno` bodies | 100 GB / 2 GiB — skip |
| loom `0=XOR` dropped onto weather records | weather `0` is NAND; silent reinterpret |
| rookery NAND-rotate **instead of** loom XOR-rotate for the power ring | two verified rings; WEATHER takes loom for power, rookery junction for witness |
| a new ring ISA, a new dest path, a host ripple as the mine | inventing dest / executor |

---

## 10. Exact precedent v2 must copy (one page)

1. **Six rings in the file** — loom emit ×6, 32 cells each, 2 senses, XOR rotate + AND(fwd[0],rev[0])→carry + OR(pub,carry)→pub. Stated purposes: NW NE SW SE GROWTH WITNESS. Opcodes translated to WEATHER `{XOR:3, AND:1, OR:2}`. Addresses = offsets in `weather_v2.mno`. One ring = kneecap.
2. **Witness outside the field** — rookery `AND(carry,carry)→recv` into a clock bank disjoint from the 16×16 state.
3. **Growth OUT** — AUTOFAB0: extra `addr_out` lands in this file's own gate-record region.
4. **avg4 gated** — playtime: `enable = XOR(fwd[0], fwd[1])` (NAND-composed in the net); `mux(enable, hold, avg4)`; both enable branches tested or store nothing.
5. **Self-clock** — playtime v2 remap: next-state `out` == cell input address. One writer. Ring wires written only by ring records.
6. **ONE start** — rookery/loom button: write `0x01` to `fwd[cell]` and `rev[cell]`, fsync, die. One sense = DC.
7. **Net vs ring** — AND/NAND on avg4/mux; XOR/OR opcodes on ring only.

Then run the fab as **new land** `weather_v2.mno` (do not smash v1). Store **six** rings, both senses, stated purposes. Then a button: inject ∨ surface ∨ die on **that** file. A card with no stored gates is not a computer. Measured 2026-08-16: `weather_v2.mno` ABSENT. `weather.mno` still zero rings. `NO_KNEECAP.md`.
