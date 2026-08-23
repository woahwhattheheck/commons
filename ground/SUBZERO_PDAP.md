# SUBZERO PDAP — organ 17 standalone excerpt

`muhl_pdap` / `MUHLPDAP`. PLUMB 2/3 organ 17. Pushdown parser. Chomsky hierarchy in gates.

## Construction (the gate count)

- 16-state control, 4-bit symbols, stack depth 32, 32 steps unrolled
- per step: 8-to-1 mux 4-bit (19 decoder + 60 mux = 79) + stack write (4) = 83
- push/pop is a 4-bit wiring shift of the stack body. Zero gates.
- 32 x 83 = **2,656 gates**, depth **192**
- CLK control/stack out -> control/stack in. One unrolled step = one settle.

## Format

Same physical excerpt as `muhl_grbn` / live `muhl_mha`:

- header: 8-char magic, then LE `n_gate, n_wires, n_in, n_out, depth`
- records: `<BQQQ>` stride 25
- OPS: NAND AND OR XOR NOT = 0 1 2 3 4
- one unique out-address per gate
- self-clock: output addresses **are** input addresses

## Receipt (this manufacture)

| field | value |
| --- | --- |
| magic | `MUHLPDAP` |
| n_gate | 2656 |
| n_wires | 2690 |
| n_in / n_out | 32 / 32 |
| depth | 192 |
| len | 69374 |
| sha256 | `874b08be34ba5263ef9ece0217c213aa14d9d9fa0e673c74c0d12a8b8799f4b4` |
| offset | 0 (standalone excerpt) |
| titan | **NOT_WRITTEN** |

Regenerate the `.mno` from the fabricator (stdlib only):

```
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_fab_pdap.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/test_muhl_fab_pdap.py
```

Git copy does not run. MOVE into titan is an owner-PC step. Offset band is requested, not chosen here.
