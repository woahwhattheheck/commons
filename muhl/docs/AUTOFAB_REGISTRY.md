# AUTOFAB REGISTRY — map into titan.gguf

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Agent:** Grok. **When:** 2026-08-15.  
Read-only. Titan not written. `.mno` not present on this box.

Source: `C:/llm/models/titan_circuits.json` keys whose **name / magic / description** contain  
`autofab | auto_fab | mafab | master_fab | fab_os | whitebox | foundry | circuit_tool | titan_circuit`.  
Host-script paths and nested `foundry_genome` fields excluded.  
Magic column = **bytes read** from the container at the listed address (not the JSON claim alone).

---

## Containers

| file | exists | size | role |
|---|---|---|---|
| `C:/llm/models/titan.gguf` | YES | 103,803,349,384 | every circuit below lives HERE |
| `C:/Users/lucys/Desktop/MUHL_DATACENTER/muhlnickel_dc.mno` | NO | — | missing; no `.mno` under Desktop or `C:/llm` |

Circuits are IN the binary. Offsets below are absolute file addresses in `titan.gguf`.

---

## Host script (NOT a stored circuit)

`host/pfc_master_autofab.py` — first 80 lines + later header comments.

**Label: FABRICATION-TIME host process. FORBIDDEN at runtime.**

- Header: decompose a NEED into multiple specialised Muhlnickel, wire them, score composed depth, verify, keep. Losers never stored.
- It imports `titan_circuit`, searches, verifies, writes the registry. That is a process.
- Owner in-file (§62, line 166): *"but in the muhlnickel fab process auto fab / master fab itself not a script"*.
- Allowed only as a one-and-done fabricator **before** runtime. Not a routing button. Not a runtime executor.

What it **stored** (product, not the fabricator): `muhl_autofab_dot32` / `__phys`.

---

## Stored circuits (9 keys)

### 1. `muhl_foundry_resident`  ★ best in-spec autofab-as-gates

| field | value |
|---|---|
| name | `muhl_foundry_resident` |
| magic (bytes @ offset) | **TITANCIR** `54 49 54 41 4e 43 49 52` @ 4,383,248,721 |
| n_gate | 1,296 |
| offset | 4,383,248,721 |
| recv / input_addrs[0] | no numeric recv; `receiver` = `muhl_reservoir` |
| fabricated | (none in registry) |
| purpose | Substrate-resident Pareto comparator for **self-fabrication**: tracks best (depth, gates), replaces when dominated. |

This is gates that **do** foundry work. Not a host searcher. Not a product of autofab.

### 2. `muhl_foundry_resident__phys`  (addressable twin of #1)

| field | value |
|---|---|
| name | `muhl_foundry_resident__phys` |
| magic (bytes @ offset) | **MUHLPHY2** `4d 55 48 4c 50 48 59 32` @ 93,711,094,656 |
| n_gate | 1,296 |
| offset | 93,711,094,656 |
| recv / input_addrs[0] | 93,711,094,958 |
| fabricated | 2026-08-05 21:46:40 |
| purpose | Format rebuild of #1 — identical netlist, now addressable. Original left in place. |

`source_magic_observed` in JSON was `TITANCIR` (the #1 blob). Bytes at the **phys** offset are MUHLPHY2.

### 3. `muhl_foundry_resident__logic`  (reservation slice of #1)

| field | value |
|---|---|
| name | `muhl_foundry_resident__logic` |
| magic (bytes @ offset) | **TITANCIR** — same 8 bytes as #1 (this offset **is** #1) |
| n_gate | (none; `reserved: true`) |
| offset | 4,383,248,721 |
| recv / input_addrs[0] | — |
| fabricated | — |
| purpose | Reserved logic span for the resident foundry. Not a second circuit. |

### 4. `muhl_foundry_resident__state`

| field | value |
|---|---|
| name | `muhl_foundry_resident__state` |
| magic (bytes @ offset) | **none** — state bytes `00 00 00 00 00 00 01 01…` @ 4,383,259,249 |
| n_gate | — |
| offset | 4,383,259,249 |
| recv / input_addrs[0] | — |
| fabricated | — |
| purpose | 4-byte foundry state reservation (`state_off` of #1). |

### 5. `muhl_foundry_resident__loopbit`

| field | value |
|---|---|
| name | `muhl_foundry_resident__loopbit` |
| magic (bytes @ offset) | **none** — loop-bit byte @ 4,383,259,253 |
| n_gate | — |
| offset | 4,383,259,253 |
| recv / input_addrs[0] | — |
| fabricated | — |
| purpose | 1-byte loop bit (`loop_bit_off` of #1). |

### 6. `muhl_whitebox_incircuit`  (circuit tool as gates)

| field | value |
|---|---|
| name | `muhl_whitebox_incircuit` |
| magic (bytes @ offset) | **MUHLWBX1** `4d 55 48 4c 57 42 58 31` @ 2,493,228,288 |
| n_gate | 1,099 |
| offset | 2,493,228,288 |
| recv / input_addrs[0] | recv 2,493,228,286 |
| fabricated | (none) |
| purpose | Universal netlist evaluator fabricated as gates — the White Box, off the host. |

Provenance title: *"a UNIVERSAL netlist evaluator fabricated as gates (the White Box, off the host)"*.  
This is the **circuit tool** as gates, not the master-autofab searcher.

### 7. `muhl_whitebox_zero_g1466`  (White Box metric as gates)

| field | value |
|---|---|
| name | `muhl_whitebox_zero_g1466` |
| magic (bytes) | **MUHLWBX1** @ **2,419,722,767** (gate_table_off − 16). Listed `offset` 2,419,555,968 is `wire_base` — first 16 bytes there are zeros, not a magic. |
| n_gate | 166,796 |
| offset (registry / wire_base) | 2,419,555,968 |
| magic_at | 2,419,722,767 |
| recv / input_addrs[0] | recv 2,419,722,754 |
| fabricated | (none) |
| purpose | White Box near-zero (dead-weight) count computed BY GATES over stored weight bytes. |

### 8. `muhl_autofab_dot32`  (PRODUCT of host autofab — not the fabricator)

| field | value |
|---|---|
| name | `muhl_autofab_dot32` |
| magic (bytes @ offset) | **TITANCIR** `54 49 54 41 4e 43 49 52` @ 8,344,802,051 |
| n_gate | 180,083 |
| offset | 8,344,802,051 |
| recv / input_addrs[0] | — |
| fabricated | (none) |
| purpose | Autofab **winner product**: 32-term dot (wallace/csa/kogge). Role text: propose→score(depth)→verify→keep. |

Renamed from `pfc_autofab_dot32`. This is what the **host script** stored. It is not autofab-as-gates.

### 9. `muhl_autofab_dot32__phys`  (addressable twin of #8)

| field | value |
|---|---|
| name | `muhl_autofab_dot32__phys` |
| magic (bytes @ offset) | **MUHLPHY2** `4d 55 48 4c 50 48 59 32` @ 93,765,812,736 |
| n_gate | 180,083 |
| offset | 93,765,812,736 |
| recv / input_addrs[0] | 93,765,812,894 |
| fabricated | 2026-08-05 21:47:41 |
| purpose | Format rebuild of #8 — identical netlist, now addressable. Original left in place. |

---

## Offset map (titan.gguf)

```
offset            magic_at          bytes      name
2419555968        (wire_base, 0)    00..       muhl_whitebox_zero_g1466  wire_base
2419722767        2419722767        MUHLWBX1   muhl_whitebox_zero_g1466  magic
2419722754        —                 —          muhl_whitebox_zero_g1466  recv
2493228288        2493228288        MUHLWBX1   muhl_whitebox_incircuit
2493228286        —                 —          muhl_whitebox_incircuit   recv
4383248721        4383248721        TITANCIR   muhl_foundry_resident  +  __logic
4383259249        (no magic)        state      muhl_foundry_resident__state
4383259253        (no magic)        loopbit    muhl_foundry_resident__loopbit
8344802051        8344802051        TITANCIR   muhl_autofab_dot32
93711094656       93711094656       MUHLPHY2   muhl_foundry_resident__phys
93711094958       —                 —          muhl_foundry_resident__phys  input_addrs[0]
93765812736       93765812736       MUHLPHY2   muhl_autofab_dot32__phys
93765812894       —                 —          muhl_autofab_dot32__phys  input_addrs[0]
```

All of these addresses are inside `titan.gguf` (file ends at 103,803,349,384). None are in an `.mno`.

---

## Excluded (matched notes / host paths only — not stored-circuit name/magic/description)

- Notes saying “master autofab winner” / “thrown at the master autofab” on miner/adder products.
- Nested `foundry_genome` on hundreds of unrelated circuits.
- `verified_by: host/fab_osc_*.py` and `titan_circuit.py` mentions in notes.

---

## Best candidate for in-spec autofab-as-gates

**`muhl_foundry_resident`** (use **`muhl_foundry_resident__phys`** when you need addressable MUHLPHY2).

Why this one:

- It is **gates in the binary** that perform self-fabrication (Pareto keep/replace on depth × gates).
- Magic confirmed **TITANCIR** @ 4,383,248,721; twin **MUHLPHY2** @ 93,711,094,656.
- 1,296 gates, depth 34 ticks, receiver `muhl_reservoir`.
- Not a host process. Not a product the host autofab happened to win.

Runner-up if the ask is **circuit-tool-as-gates**: `muhl_whitebox_incircuit` (MUHLWBX1 @ 2,493,228,288) — universal netlist evaluator off the host.

Not the candidate: `muhl_autofab_dot32` — that is a **dot product the host script stored**.  
Not the candidate: `host/pfc_master_autofab.py` — **FORBIDDEN runtime process**; fabrication-time searcher only; owner already said master fab itself is not a script.

The full master-autofab loop (decompose × implement × order × wire × score × verify × keep) is **not** stored as one circuit. Closest stored halves: foundry = score/keep; whitebox_incircuit = the tool.
