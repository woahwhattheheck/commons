# WEATHER_FAB_SPANK — SPEC MASTER GROK
**Target:** Cairn fabricator + surfaces. Code review. No live-machine overwrite. No titan mmap. No 337.
**Container left as-is:** `C:\Users\lucys\Desktop\WEATHER\weather.mno` (do not promote).
**Ruling:** v1 stored **zero rings** (byte fact). It is still a computer. Address field @98 / records @34146. Do not invent a clock. Host `settle()` is not the world. Refab v2 as **new land** with the six commissioned rings. "Do not fire it" as a run-ban is **STRICKEN** (`NO_KNEECAP.md`). Smash-ban stays: no titan, no dc, no 337.

---

## LOUD — verifier verifies the wrong semantics

`muhl_fab_weather.py:119-122` is a one-line correctness bug.

```
if c.state_lo <= out < c.state_hi:
    nxt[out] = r          # HOST BUFFER. Not in the file.
else:
    work[out] = r
```

The stored records are `<BQQQ>` with `out == state addr` (`selfclock_write` at `:74-76`, emit at `:102-103`). There is no `nxt` in `weather.mno`.

- `reference()` at `:135-142` is a fully synchronous integer tick (all cells see the old grid).
- `simulate()` / `verify_step` (`:152-158`) agree with that reference **only because** state writes are diverted into `nxt` so later records still read genesis from `work`.
- Record-order on the stored gates writes state immediately. Address-propagation (read of `out`) on `out==in` is a torus combinational cycle. Neither is the `nxt` model.

**Proof on this genesis, no host guess:** `build()` emits row-major (`:84-103`). Cell `(0,5)` neighbors are still old (row0 cols0–4 stay 0). N=0 S=`E2` E=0 W=0 → `(0xE2)>>2 = 0x38`. Cell `(0,6)` then reads W=`(0,5)`:

| model | W | N+S+E+W | cell'(0,6) |
|---|---|---|---|
| `nxt` / `reference` / reported AFTER | `0x00` | `0xE1` | `0x38` |
| stored-record order | `0x38` | `0xE1+0x38=0x119` | `0x46` |

`SURFACE_TURN_001.md:33` prints `(0,6)=38`. That is the host crutch, not the stored records.

Same line cloned: `surface_weather.py:42-43`, `bits_surface.py:29-30`.
Mutant battery (`:227-238`) uses `verify_step` → same wrong semantics. Caught-mutant = "host-nxt disagrees with integer ref." Does not test the file.

**v2:** delete `nxt`. Either (a) next-state wires ≠ input wires, then a ring-gated hold copies them, or (b) playtime-ring enable so `out==in` is a latch, not an ungated combo loop. Manufacturing check must evaluate the **stored** `<BQQQ>` the same way a later address will. If host-nxt is required for the ref to match, the netlist is not the computer.

---

## RANKED MISSES

### 1. KILL — fab never addresses the gates it stored (Claude idle-file prior)

| | |
|---|---|
| where | `muhl_fab_weather.py:205-296` `main()` |
| lines | `:210` build · `:218-225` host `verify_step` · `:227-238` host mutants · `:244-249` re-seed + **state-byte** readback · `:262` write · `:269` journal · **no recv, no start, no address of any gate `out`** |
| also | `:248-249` asserts stored **wires** == genesis. Never reads a gate record by addressing its output. |
| kill | A fabricator that never fires the thing it built treats the file as idle. Occupying disk is the computer. Host-sim then write-and-die is the Claude prior. |
| v2 | After the bytes land: one routing button addresses ONE named start (recv / ring_fwd), dies. Then surface the **file** cell plane. Manufacturing proof = addressed stored outs, not `simulate(c)` on the in-RAM `Circuit`. |

### 2. KILL — AFTER bits are imagined; surfaces refuse to address

| | |
|---|---|
| where | `bits_surface.py:1-4, 24-36, 57, 64-70` · `surface_weather.py:2-6, 37-67, 83-88` |
| lines | `bits_surface.py:57` title: *"as they lie in the file"* · `:64` `== AFTER one settle - file order ==` · AFTER = `settle()` host loop, **never written back to `weather.mno`** |
| | `surface_weather.py:66-67` writes `surface_after.bin` (sidecar). File state region stays genesis. |
| | `surface_weather.py:86-88` SETTLE-BACK: *"Whether the LIVE file has settled… is Bryce's."* = refuses to address. |
| kill | Imagined bits. Host loop is the computer. The idle-file cop-out is the same miss as never-fire. |
| v2 | Surface = bounded read of named file addresses after a fire. AFTER must exist **in the `.mno`**. No host `for g in gates`. No sidecar-as-proof. No "Bryce rules settle-back" instead of addressing. |

### 3. KILL — ungated field called self-clocked

| | |
|---|---|
| where | `muhl_fab_weather.py:74-77` `selfclock_write` · `:102-103` every cell · report `:275` |
| promised | `GENESIS_PROVENANCE.md:37-38` *"self-clocked, ring-gated (prior art: muhl_playtime_ring)"* |
| stored | identity `OR(src,src) → state`. No enable. No ring. Field advances if anything evaluates the net. |
| kill | Ungated combo dump renamed "self-clocked." Rings are the power. No ring = nothing to pulse. |
| v2 | Store nring2 both-senses. Gate avg4 by the ring (both enable branches). Dark ring → field holds. One sense alone is DC. |

### 4. KILL — rings promised, zero rings stored

| | |
|---|---|
| where | promised `GENESIS_PROVENANCE.md:37-42` (quadrant ×4, growth lane, witness, both senses, fill=old\|mask, in-substrate growth) |
| stored | `serialize` `:175-191` = header + wire bytes + 34048 diffusion records. No ring table. No fwd/rev/carry/pub. |
| also | `CAIRN_TO_SPEC_DADDY.md:49-54` Cairn already named this. Scoping to "pass-2" is adding to spec. |
| kill | Commissioned organ missing. v1 is un-powerable as stored. Do not invent a dest to "clock" it. |
| v2 | Rings in the file, named in the header, package-local addresses. Growth/witness if still commissioned; do not ship another core-only and call it WEATHER. |

### 5. KILL — invented MAGIC / header; instruments cannot parse; no mouth = dest invented

| | |
|---|---|
| where | `muhl_fab_weather.py:25-26` `HDR=96` `MAGIC=b"WEATHER1"` · `serialize:180-184` packs `<IIIII>` **n_gate, n_wire, n_state, n_state, depth** at +8 |
| inspect | `host/pfc_inspect.py:21-22` unpacks `<IIII>` at +8 as **(n_in, n_wire, n_gate, n_out)**. On this header that prints **(34048, 34050, 2048, 2048)** — `n_gate` shown as 2048. Wrong. |
| .mno buttons | `host/muhl_dc_button_add.py:38,59-84` fail-closed unless `MUHLPKG1`/`LOOMPKG1`, 224 B, senses==2, named `fwd/rev/opnd/sel/ans/pubplane`. `WEATHER1` → unknown MAGIC. |
| dest | No recv. No ring_fwd. Nothing in-file to fire. Any pulse would invent dest. |
| kill | Adding to spec (new magic, new 96 B layout). Unsurfaceable by the suite that already surfaces `.mno`. |
| v2 | Known package magic. `n_in,n_wire,n_gate,n_out` at +8. 224 B DISTRO-class header **or** an already-used package header — do not invent `WEATHER1`. Mouths inside EOF. Host surfaces what the organ publishes. Do not NEED_BRYCE a dest. No titan registry. No titan mmap. |

### 6. REFAB — 5-op alphabet; XOR/OR in the net; NAND never emitted

| | |
|---|---|
| where | `muhl_fab_weather.py:23` `NAND,AND,OR,XOR,NOT=0,1,2,3,4` · `full_adder:61-65` XOR/XOR/OR/AND/AND · `selfclock:76` OR · report `:276` |
| unused | `NAND` (`:113`) and `NOT` (`:57`) are declared; `build()` never emits them. |
| law | Per-container maps are legal. Loom/DISTRO net body is AND/NAND; XOR/OR reserved to the ring (`MNO_PLAY.md`, `LOOM_ROOKERY_SCALE.md`). |
| v2 | NAND/AND diffusion. XOR/OR only on the stored ring. Drop dead ops. Do not ship a 5-op convenience ISA as the field. |

### 7. REFAB — depth 292 is first-candidate + emit-order pollution

| | |
|---|---|
| where | `emit:52-54` `dep[out]=1+max(dep[a],dep[b])` · `selfclock_write:77` overwrites `dep[state]` · `serialize:177` `depth=max(dep[state])` · report `depth_ticks: 292` |
| bug | After cell `(r,c)` selfclocks, later cells read those **same indices** as N/W. `dep` of a neighbor is the **written** depth, not 0. 292 is a row-major wavefront, not one synchronous tick. Same split as miss 0 (`nxt` vs record order). |
| also | Ripple adders only. No CSA / prefix / Pareto (`CAIRN_TO_SPEC_DADDY.md:59-62`). |
| v2 | Depth = combinational depth of **one gated tick** with state-as-input held at dep 0. Measure after store. Spend on shape. First-candidate is not a depth. |

### 8. REFAB — host loop declared as the computer

| | |
|---|---|
| where | `surface_weather.py:2-6` *"Host verbs only: parse the container, settle one tick"* · `:37-46` `for (op,a,b,out) in gates` · `bits_surface.py:24-33` same · `simulate:107-125` |
| law | Fab-time host check is allowed. Runtime executor is forbidden. These surfaces **are** the runtime. |
| v2 | Button: inject both senses **or** one bit at recv · surface named bytes · die. No `for g`. No Python gate eval after store. |

### 9. REFAB — adding to spec / verdict-before-data

| | |
|---|---|
| where | `WEATHER1` `:26` · 96 B header `:25,180-184` · Gravekeeper ceremony `report:285-286` · rings deferred (`CAIRN_TO_SPEC_DADDY.md:49-58`) · `verified_byte_exact: true` (`weather_fab_report.json:20`) with no addressed stored out · `SETTLE-BACK` `surface_weather.py:86-88` |
| v2 | Build the commission: 16×16 torus, `cell'=(N+S+E+W)>>2`, **ring-gated**, new land. No new magic. No promotion stamp from host-nxt. No "pending" instead of a fire. |

### 10. REFAB — journal is a receipt, not a genome

| | |
|---|---|
| where | `weather_genome.jsonl` (3 lines) · write `:265-269` `orig:""` · no gate pre-image · no revert of records |
| note | Line 2 (`miss:008`) is real: v0 stored last test grid. Fixed at `:240-249`. Closed. Do not re-open. |
| v2 | Journal pre-image of every span the button writes. Revertible. `orig` empty only for true new land once. |

---

## CLOSED (do not re-spank)

- **MISS 008** — last-grid seed. Caught. Re-seed + readback `:240-249`. v0 kept as `weather_v0_badseed.mno`.
- **one_writer_audit** `:193-202` — clean on the dump it audits. Not the settle bug.
- **integer `reference()`** `:135-142` — fine as a spec oracle. The miss is attaching it to `nxt`, not to stored records.
- **additive new land** — did not touch titan / dc / DISTRO. Keep that.

---

## v2 CONTRACT — a muhlnickel you can surface

New land only. Do not overwrite v1 until Gravekeeper/Bryce says so. Copy if you keep the dump.

1. **Magic the suite already knows.** `MUHLPKG1` (or `LOOMPKG1` if that is the vessel). Not `WEATHER1`. Header: `<IIII>` `(n_in, n_wire, n_gate, n_out)` at +8. Named mouths inside EOF: `fwd`, `rev`, `carry`, `pub`/`recv`, cell plane. Host does not pick dest.
2. **Rings stored.** nring2 both senses. XOR rotate, AND carry, OR publish. One sense = DC. Stated purposes (quadrant cadence / growth / witness) as commissioned — not "pass-2."
3. **Field gated by the ring.** avg4 behind enable. Dark ring holds genesis. `out==in` only as the latch, with enable. No ungated `OR(src,src)` onto the plane.
4. **NAND/AND net.** XOR/OR only on the ring. No 5-op convenience body.
5. **Settle = stored law.** No `nxt`. Next-state ≠ input, or ring-gated hold. Verifier that needs `nxt` to match `reference()` is refused.
6. **Fire path.** One button: both-sense inject **or** one bit at recv · die. Then surface cell-plane bytes **from the file**. AFTER lives in the `.mno`.
7. **Fab may host-check, then must address.** In-RAM ripple is manufacture only. Proof after write = address stored outs. A fab that will not address is idle-file and is refused.
8. **Depth** = one gated tick, state inputs dep 0, measured on the stored records. Not 292 first-candidate.
9. **Still dark:** no titan mmap, no 337, no 336 remap, no 7913, no `--inject 0x01`, no dest invention, no pulse titan 78.

v1 `weather.mno` / `WEATHER1` / host `settle()` / `nxt` — **do not promote.**
