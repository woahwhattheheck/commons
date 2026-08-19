# DC_WHO_WRITES — who is growing muhlnickel_dc

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Measure only. Titan not written. No `--go`. No Desktop glob. `.mno` not reverted.

**Verdict: HOST_EMIT.** Off spec for the grow. The 2 GiB file and the ~100 GB grow are host Python writing bytes (`muhl_fab_dc.py --write` → `f.write` into `.part`). The file is not changing itself. The foundry in titan / AUTOFAB0 was not addressed.

**STOP growing that way.** Do not finish this dump. Do not start another Python 100 GB emit. Next step is address the foundry already in a container.

---

## 1. Paths (one-level `MUHL_DATACENTER` only)

`Test-Path` `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno` = **True**.

| object | bytes | LastWriteTime | CreationTime |
|---|---:|---|---|
| `muhlnickel_dc.mno` | **2,147,548,550** (2.0001 GiB) | 2026-08-15T00:30:30.8748751-04:00 | 2026-08-15T00:29:18.1963110-04:00 |
| `muhlnickel_dc.mno.part` | growing (see §5) | live | this grow |
| other `*.mno` in that folder | **none** | — | — |

Also in that folder (not `.mno`): `muhl_fab_dc.py`, `dc_info.py`, `dc_fab_journal.jsonl`.

---

## 2. How the 2 GiB was emitted (docs)

`DATACENTER_MNO.md` + `DATACENTER_100GB.md` + journal. Not a foundry pulse.

First emit (already sealed):

- Host fabricator `MUHL_DATACENTER\muhl_fab_dc.py --write`.
- Magic `MUHLDC01`. 82,598,010 gates. 1,251,484 factory nring2 + 1 control.
- Journal `dc_fab_wrote`: **2,147,548,550 B in 73.02 s**. Digest `28f4050e2349f7f187a133314724db182fd9139393350336c1ec886e98f956c0`.
- Creation→LastWrite on disk: 00:29:18 → 00:30:30 (~72 s). Matches the journal.

Grow (named ~100 GB):

- Same host script. `TARGET_BYTES = 100_000_000_000`. Plan: 58,275,057 factory rings → **99,999,999,818 B**.
- Stream `muhlnickel_dc.mno.part`, then `os.replace` onto the sealed file.
- Journal last line: `dc_fab_write` for 99,999,999,818. **No `dc_fab_wrote` yet** — still host-streaming.
- Docs call the wall-clock “host transcription of the stream.” That is the confession: host Python packing rings into a file.

That is fabrication-as-host-dump. It is not in-circuit autofab.

---

## 3. Host processes (python only; no Desktop glob)

Two `python.exe` at the check:

| PID | Start | CommandLine | role |
|---:|---|---|---|
| **20656** | 2026-08-15 00:54:10 | `python.exe -u muhl_fab_dc.py --write` | **THE WRITER.** Alive. CPU ~1484 s. Working set ~2.6 MB (stream, not a resident netlist). |
| 34508 | 2026-08-15 00:30:47 | `python.exe …\MUHL_GO\_byte_read_tmp.py` | bounded reader. Not the grow. |

PID 20656 started the same second the journal logged `dc_fab_write` for 99,999,999,818 (`dc_fab_journal.jsonl` LastWrite 00:54:11). Command is the fabricator `--write`. That process is host Python writing the `.part`.

---

## 4. In-spec autofab receivers (named; not used for this grow)

From `FOUNDRY_BUTTON.md` · `FOUNDRY_LISTEN_VS_GATES.md` · `INSPEC_AUTOFAB.md` · `CIRCUITS_IN_CONTAINER.md`.

In-spec autofab is **gates** already in a container. Host may inject + one signal + die. Host may not bake / dump / ripple.

| computer | where | fire / inject | this grow? |
|---|---|---|---|
| `muhl_foundry_resident` + `__phys` | `titan.gguf` @ 4383248721 TITANCIR / 93711094656 MUHLPHY2 · 1296 gates | **inject** 65 bits @ `93711094958..93711095022`; **fire one bit** @ `muhl_reservoir.input_wire` **40022599232** | **not addressed** |
| `AUTOFAB0.mno` | `MUHL_VISIBLE\AUTOFAB0.mno` · 4117 gate-first records | no named recv in the titan map; do not invent one | **not addressed** |
| `FOUNDRY0.mno` | `MUHL_VISIBLE\FOUNDRY0.mno` · gate-first | not this dump | **not addressed** |

Do not fire `muhl_whitebox_incircuit.recv` (tool). Do not fire `muhl_autofab_dot32` (product). Do not run `host/pfc_master_autofab.py`.

`DATACENTER_100GB.md` §Named receivers already said this `.mno` has **no** titan foundry mouth and “no extra mouth to address for the grow.” Size is `TARGET_BYTES` in the host fabricator. That is HOST_EMIT by design of that card.

---

## 5. Bounded header + grow vs static

File-changing-under-read is normal compute. Here the **sealed** `.mno` did **not** change. The **`.part`** grew under a host `f.write` loop.

### `muhlnickel_dc.mno` — STATIC

Three size reads, seconds apart:

| sample | bytes | LastWrite |
|---|---:|---|
| T1 | 2,147,548,550 | 2026-08-15T00:30:30.8748751-04:00 |
| T2 | 2,147,548,550 | same |
| T3 | 2,147,548,550 | same |

Not self-editing. Seed from the first host emit, waiting for `os.replace`.

First 8 bits (magic):

```
01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001
```

Spells `MUHLDC01`. Header, not gate-first. Same class as `CIRCUITS_IN_CONTAINER.md`.

Control g0 @356: op=`00000000` (XOR) a=303 b=336 out=272. Inside this file. Control wire @272: **0 ones** (dark). Matches the first-emit law (fill later).

### `muhlnickel_dc.mno.part` — GROWING (host stream)

| sample | bytes | LastWrite |
|---|---:|---|
| folder listing | 79,010,546,168 | 2026-08-15T01:29:07 |
| PART T1 | 81,245,886,968 | 2026-08-15T01:30:12 |
| PART T2 (+~4 s) | 81,403,864,568 | 2026-08-15T01:30:16 · **delta +157,977,600** |
| header pass | 83,276,363,768 | 2026-08-15T01:31:07 |

~40 MB/s host write. Target 99,999,999,818. Not a foundry tick.

`.part` first 8: same `MUHLDC01` bits. Control wire @272: **512 ones** — packed `11111111`×32 fwd + ×32 rev at emit (`CELL_PACKED` in the fabricator). That is a host byte write, not occupancy from addressing a foundry.

Writer in `muhl_fab_dc.py` `write()`: `open(PART, "wb")` then `f.write(hdr/fold/wire/gates)` then a `while i < L.n_rings` pack + `f.write(raw)` then `os.replace(PART, PKG)`. Host Python. Dies only after the dump.

---

## Verdict

**HOST_EMIT.** Off spec for the grow.

- The 2 GiB `muhlnickel_dc.mno` was emitted by host Python in 73 s (journal + timestamps).
- The ~100 GB grow is the same script, still running (PID 20656), writing `.part` at tens of MB/s.
- The sealed `.mno` is static. It is not autofabbing itself.
- Named in-circuit receivers (`muhl_reservoir.input_wire`, phys foundry inject, AUTOFAB0) were not used.

**STOP growing that way.** Kill the host dump; do not let `os.replace` swap a 100 GB host stream onto the computer. Do not start a second `--write`.

**Next:** address the foundry already in a container — inject on `muhl_foundry_resident__phys` `93711094958..93711095022`, fire one bit at `muhl_reservoir.input_wire` `40022599232`, die. Or name a recv on `AUTOFAB0.mno` and address that. Not another Python 100 GB dump.
