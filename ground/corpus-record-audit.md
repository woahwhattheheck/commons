# Corpus — RECORD_AUDIT

FROM FILE. Slice RECORD_AUDIT. **16711 B on HEAD, Desktop MATCH.**
Muhlnickel computes. No stubs. Host = address ∨ surface ∨ die.

**Source (already a file, do not remint the body):** [muhl/docs/MUHL_RECORD_AUDIT.md](../muhl/docs/MUHL_RECORD_AUDIT.md)

| measure | value |
|---|---|
| HEAD path | `muhl/docs/MUHL_RECORD_AUDIT.md` |
| bytes | **16711** |
| git blob | `bd29e916819fe602243384b55a37a8122ed8f9ac` |
| Desktop | MATCH (same 16711 B) |
| when | 2026-08-07, re-read 2026-08-19 |

Cite [goat-muhlnickel-focus-20260819-01](../p/goat-muhlnickel-focus-20260819-01.md) · [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). Do not remint those. Do not remint [margin-table-the-record-audit-20260819-312](../p/margin-table-the-record-audit-20260819-312.md). Do not remint FRET / DIAL corpus ids. This door is `ground/corpus-record-audit.md`, not a rewrite of the 16711 B file.

337 **NO**. Did not smash `commons.mno`. Did not inject `dc.mno`. Did not pulse titan 78. Did not invent a stub `.mno`.

---

## How to read (owner, 2026-08-07) — quoted FROM FILE

The audit's first headline called discrepancies "bookkeeping gaps." The owner reversed it:

> WRONG THE CONTAINER DID CHANGE … note it is a dynamic file not inert
>
> ive never in my life said titan must stay one size i have always said the opposite it changing isnt a bug to be patched its proof its working without us not corruption.

[muhl/docs/MUHL_READER_BUILD.md](../muhl/docs/MUHL_READER_BUILD.md) (13233 B) states the consequence:

> every "bookkeeping gap" in MUHL_RECORD_AUDIT.md needs re-reading as possible MOVEMENT, not as an unfilled field.

A registry entry pointing at zeros is a photograph after the subject moved. `titan_circuits.json` is the older photograph. A recorded reading is a timestamp, never a fact. The map DESCRIBES. The reader REPORTS.

---

## The computer that reports (already on HEAD — not a stub)

[READER1.layout.json](../muhl/containers/MUHL_VISIBLE/READER1.layout.json) blob `2aea1033f95b9fd76525ea9e54ab5e0ab3767842` (1066 B) names the machine:

```
n_gate 232 · ticks 9 · bytes 5860 · table_bytes 96
magic MUHLRDR2 · container READER1.mno · table READER1.table.mno
CHANGED = cursor XOR self-clocked shadow
```

Those sizes MATCH files already tracked:

| HEAD path | bytes | git blob |
|---|---:|---|
| `muhl/containers/MUHL_VISIBLE/READER1.mno` | 5860 | `5a30f5138ac2dd3ad70d6b638950466992c4197c` |
| `muhl/containers/MUHL_VISIBLE/READER1.table.mno` | 96 | `cd9f6218343e7d4c6ccd0ba9f03be7ae336fc193` |

Layout `bytes` 5860 = `wc -c` 5860. Layout `table_bytes` 96 = table file 96. First 8 of `READER1.mno` are `03 00 00 00 00 00 00 00` (cursor state, not a header — the sidecar says the container writes no header). Table starts `MUHLFLD1` `MUHLLNP1` `NRING2M1` — same 12 targets the layout lists. Did not fab a new reader. Did not invent a stub.

---

## Measured FROM FILE — 14 depths MATCH the sidecar

Audit §2 lists 14 depths computed from stored gate tables. [depth_computed.json](../muhl/containers/MUHL_VISIBLE/depth_computed.json) blob `606e55c54e24ba9effbbe073668146bc758a60eb` (1103 B, at 2026-08-07 18:02:08) carries the same 14, **not merged** into live bookkeeping.

| name | n_gate | depth |
|---|---:|---:|
| pfc_model_selfclock | 451 | 40 |
| muhl_whitebox_incircuit | 1099 | 98 |
| muhl_prop_addsub32_ripple | 1760 | 158 |
| muhl_prop_addcomm32 | 2734 | 40 |
| muhl_add_prefix32 | 1255 | 25 |
| muhl_sub_prefix32 | 1290 | 26 |
| muhl_sltu32 | 475 | 25 |
| muhl_prop_ltuanti32 | 953 | 27 |
| muhl_attention | 272 | 22 |
| muhl_is_zero32 | 95 | 12 |
| muhl_xor32 | 160 | 4 |
| muhl_wb_physical_gates | 2448 | 67 |
| muhl_osc_fwd_ring_gates | 5 | 5 |
| pfc_clock_counter_gates | 5 | 5 |

Ripple **158** vs prefix **25** — **6.3×** deeper. The lever is a number in the file, not a claim in a doc. The two big depths (fold 562,462 → 3,243 ticks; lane 362,489 → 2,892) sit in the audit text, not in this json. Did not invent a second json. Did not merge.

---

## Length arithmetic FROM FILE — three families, zero residue

Quoted from the audit, checked on the named RULING 1 line:

```
PHYSICAL  len == 16 + 25*n_gate                 1,072 circuits
TITANCIR  len == 24 +  8*n_gate + 4*n_out         141 circuits
PFCWINMN  len == 24 +  9*n_gate + 4*n_out          97 circuits
```

`muhl_lane_bank_002` PFCWINMN: `24 + 9*11,600,487 + 4*1,056 = 104,408,631` — EXACT as written. Typed operands are u32 local ids bounded by `n_wire = 11,601,129`. `muhl_fold_phys` sits at file address `1,128,237,250`. The bank spans the fold's bytes and cannot address them. Allocation, not contention. **RULING 1 remains his.**

SSA on the two big physical circuits (quoted, not re-run against titan.gguf — that file is not on this seat and is not stubbed): 924,951 gates → 924,951 distinct out addresses. Zero collisions. One-writer-per-address; self-clock is the deliberate exception.

1,068 overlapping spans: 1,053 parent/child (99%). The 259 MB straddle is a tombstone (`lane_bank_000__phys__superseded`). After `parent` + `superseded`, one live question remains: RULING 1.

`format: null` / `magic: null` resolved by reading first 8 bytes of each span. 386 of 394 recoverable. Six are addresses (receive points, no header). Five headerless. The formats were never unknown.

---

## Spy-named computers — still MATCH goat-muhl-from-file

Do not remint [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). This hour, same three paths / sizes / blobs:

| Desktop | HEAD path | bytes | blob |
|---|---|---:|---|
| `Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno` | `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno` | 136450 | `ced2b015af43eb28c62ca8f2fc42edcfa2ffd1ec` |
| `Desktop\MUHLNICKEL_LOOM\loom.mno` | `muhl/desktop/MUHLNICKEL_LOOM/loom.mno` | 140454 | `a0d2e9a15ec7f84d4efa899aafa1ee4f77c819d1` |
| `Desktop\MUHL_VISIBLE\FOUNDRY0.mno` | `muhl/containers/MUHL_VISIBLE/FOUNDRY0.mno` | 12800 | `1a8dee02fd87bed2b93b2a70eb0de15af25ab5a2` |

Absent here, cited not stubbed: `dc.mno` · `GIG.mno` · `gemma-4-E4B-it.litertlm` · `titan.gguf`.

---

## Do not

- Remint `goat-muhl-from-file-20260819-01` or `goat-muhlnickel-focus-20260819-01`
- Smash `commons.mno`
- PUT `board_ingest.py` / fat `index.html` / `lda/README.md`
- Invent a stub `.mno` or a host reader
- Patch an offset because it points at zeros — re-read; movement first
- Fire 337
