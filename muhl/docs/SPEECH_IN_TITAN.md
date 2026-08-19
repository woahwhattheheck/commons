# SPEECH IN TITAN — binary only

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Law. Commands, not essays. Do not add to spec.**  
Read 2026-08-15. Titan not written. No Desktop glob. No git.

Map: `C:\llm\models\titan_circuits.json` (5281 top-level names).  
Container: `C:\llm\models\titan.gguf` SIZE 103803349384.  
Grep names: `speak` `speech` `voice` `say` `talk` `muhl_speak` `interpret` `journal` `log` `utterance`.  
Then bounded byte reads at those offsets. Circuits = 25-byte records in the container (`<BQQQ>` physical) **or** typed magic + local wire ids (same computer, other packing).

---

## Verdict

**No circuit in the map is named speak / speech / voice / say / talk / muhl_speak / utterance.**  
Those strings do not exist as keys. Speech-as-prose is not this job.

**`log` as a NAME hit is only `__logic`.** Six twins. Substring, not a word. All six open on **TITANCIR**. They are gates (typed NAND netlist). First 25 bytes at the named offset are magic+header, not a 25-byte physical record.

**`interpret` is not a circuit name.** It lives in map prose:
- `pfc_eval.role` — "baked gate-evaluator (the interpreter/ripple, recreated as gates)"
- `muhl_whitebox_incircuit.provenance.builder` — `build_interpreter`

Both of those offsets **are gates**. Read below.

**`journal` is not a circuit name.** One nested key (`genome_revert_hazard.journal`) and notes about genome jsonl. Not speech. Not read as a speech organ.

**`log` wordish (standalone `log`, not inside `logic`):** none.  
`bitslice.logW` is a field, value 33, confirmed in bytes.

---

## Name grep (map keys)

| term | circuit NAME hits |
|---|---|
| speak, speech, voice, say, talk, muhl_speak, utterance | **0** |
| interpret | **0** |
| journal | **0** (nested field only) |
| log | **6** — all `*__logic` |

Names: `pfc_fwd_loop__logic` · `muhl_self_train__logic` · `muhl_worker__logic` · `muhl_foundry_resident__logic` · `muhl_dispatcher__logic` · `muhl_cadt_r110__logic`

---

## Bytes at those offsets

`@0` of titan is GGUF (`01000111 01000111 01010101 01000110`). Not touched.

TITANCIR header (from the fabricator, matched in these bytes):  
`TITANCIR` + `<IIII` n_in, n_wire, n_gate, n_out. Body = int32 wire ids. **Gates. Not `<BQQQ>` at byte 0.**

PFCTYPED: same four-int header after an 8-byte magic. **Gates. Typed.**

MUHLWBX1: physical. `gate_stride` 25. Table at offset+16.

| name | why in grep | offset | magic READ | packing | gates? | n_gate from BYTES |
|---|---|---:|---|---|---|---:|
| `pfc_fwd_loop__logic` | log ⊂ logic | 2464333045 | TITANCIR | typed | YES | 414828 |
| `muhl_self_train__logic` | log ⊂ logic | 5699992560 | TITANCIR | typed | YES | 112781 |
| `muhl_worker__logic` | log ⊂ logic | 4383223288 | TITANCIR | typed | YES | 2833 |
| `muhl_foundry_resident__logic` | log ⊂ logic | 4383248721 | TITANCIR | typed | YES | 1296 |
| `muhl_dispatcher__logic` | log ⊂ logic | 4383246047 | TITANCIR | typed | YES | 314 |
| `muhl_cadt_r110__logic` | log ⊂ logic | 4383220815 | TITANCIR | typed | YES | 289 |
| `pfc_eval` | interpret in role | 2394747498 | PFCTYPED | typed | YES | 502 |
| `muhl_whitebox_incircuit` | builder interpret | 2493228288 | MUHLWBX1 | physical 25 B | YES | 1099 (map; table read) |
| `bitslice` | key logW | 2218141428 | TITANBSL | bitslice hdr | NO gate at byte 0 | — |

`pfc_eval` header in the bytes: n_in=153 n_wire=657 n_gate=502 n_out=21. Matches the map. The interpreter **is** gates.

Whitebox first **25-byte** record @ 2493228304 (table, not the magic):

```
op=4 a=2493227078 b=2493227078 o=2493227188
00000100 01000110 10100000 10011011 10010100 00000000 00000000 00000000 00000000
01000110 10100000 10011011 10010100 00000000 00000000 00000000 00000000
10110100 10100000 10011011 10010100 00000000 00000000 00000000 00000000
```

Plausible physical gate. YES.

`bitslice` @ 2218141428: `TITANBSL` then logW=33 (`0x21`) in the header. Not a 25-byte gate. Not speech.

---

## First 25 bits at each named offset (magic+header)

**pfc_fwd_loop__logic** TITANCIR n_in=191 n_wire=415021 n_gate=414828 n_out=175

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
10111111 00000000 00000000 00000000 00101101 01010101 00000110 00000000
01101100 01010100 00000110 00000000 10101111 00000000 00000000 00000000 10000010
```

**muhl_self_train__logic** TITANCIR n_in=1751 n_wire=114534 n_gate=112781 n_out=1743

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
11010111 00000110 00000000 00000000 01100110 10111111 00000001 00000000
10001101 10111000 00000001 00000000 11001111 00000110 00000000 00000000 10110010
```

**muhl_worker__logic** TITANCIR n_in=51 n_wire=2886 n_gate=2833 n_out=17

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
00110011 00000000 00000000 00000000 01000110 00001011 00000000 00000000
00010001 00001011 00000000 00000000 00010001 00000000 00000000 00000000 00010010
```

**muhl_foundry_resident__logic** TITANCIR n_in=65 n_wire=1363 n_gate=1296 n_out=34  
Same bytes as `muhl_foundry_resident` (same offset). Twin name, one record.

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
01000001 00000000 00000000 00000000 01010011 00000101 00000000 00000000
00010000 00000101 00000000 00000000 00100010 00000000 00000000 00000000 00110001
```

**muhl_dispatcher__logic** TITANCIR n_in=33 n_wire=349 n_gate=314 n_out=34

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
00100001 00000000 00000000 00000000 01011101 00000001 00000000 00000000
00111010 00000001 00000000 00000000 00100010 00000000 00000000 00000000 00011010
```

**muhl_cadt_r110__logic** TITANCIR n_in=33 n_wire=324 n_gate=289 n_out=33

```
01010100 01001001 01010100 01000001 01001110 01000011 01001001 01010010
00100001 00000000 00000000 00000000 01000100 00000001 00000000 00000000
00100001 00000001 00000000 00000000 00100001 00000000 00000000 00000000 00011110
```

**pfc_eval** PFCTYPED n_in=153 n_wire=657 n_gate=502 n_out=21

```
01010000 01000110 01000011 01010100 01011001 01010000 01000101 01000100
10011001 00000000 00000000 00000000 10010001 00000010 00000000 00000000
11110110 00000001 00000000 00000000 00010101 00000000 00000000 00000000 00000100
```

**muhl_whitebox_incircuit** MUHLWBX1 (magic; gates start +16)

```
01001101 01010101 01001000 01001100 01010111 01000010 01011000 00110001
01001011 00000100 00000000 00000000 00011001 00000000 00000000 00000000
00000100 01000110 10100000 10011011 10010100 00000000 00000000 00000000 00000000
```

**bitslice** TITANBSL logW=33

```
01010100 01001001 01010100 01000001 01001110 01000010 01010011 01001100
00000000 00000000 00000000 01000000 00100001 00000000 00000000 00000000
00011000 00000000 00000000 00000000 00011001 00000000 00000000 00000000 00011010
```

---

## What this is not

- Not a missing speech organ that "should" be invented here. Map has no speak/speech/voice name. Bytes at the `log`/`interpret` hits are **other** machines (fwd loop, foundry, worker, dispatcher, r110, eval, whitebox, bitslice).
- Not the prose hunt. That card is `SUBSTRATE_SPEECH_FILES.md`.
- Titan was not written. Helpers used to read were discarded.

The interpreter that exists in this binary is `pfc_eval` (PFCTYPED, 502 gates) and the White Box (`MUHLWBX1`, 25-byte table). Neither is named speech.
