# SUBZERO_WALK — one public GRBN settle

Work order `kimi-subzero-walker-20260829-01`. Additive fabrication-verification
land. One stdlib host walk over ONE public excerpt. Not a remint of
`SUBZERO_GRBN`, `SUBZERO_TECH`, `SUBZERO_PROOF`, or `SUBZERO_EXPLORER`.

## What was measured

| field | value |
|---|---|
| excerpt | `excerpts/20260823/muhl_grbn.mno` |
| magic | `MUHLGRBN` |
| n_gate | 8704 |
| n_in / n_out | 256 / 256 |
| clock | state out IS state in |
| excerpt sha256 | `09214540b3f3117ab93a4c509017a5e7b9c5f12d86545069af4ffcdae99c6632` |
| excerpt git blob | `e39bad0d1703c1d44ad135cebbc09cded26a6027` |
| sidecar git blob | `d2c190f25d083e428f9589f78b4b2e64beb96306` |
| fabricator git blob | `f20609aacb1bb362bc98e5af4912bdf1df4e3aa3` |
| walker | `host/subzero_walk.py` |
| printed next-state | `excerpts/20260823/grbn_next_state.txt` |
| init popcount | 0 (as stored) |
| next popcount | 125 |
| class | `RUNTIME_MEASURED` |
| titan | `NOT_WRITTEN` |

One update = one settle. The walker snapshots the 256 state-in bytes and then
evaluates every stored `<BQQQ>` gate. Later nodes therefore still see the
pre-tick state. An async walk that reads live state after earlier roots write
back is a different number (128 ones) and is not this land.

## Honest label

This is one settle on one public excerpt. It is not organ certification. It is
not a customer claim. It does not open `titan.gguf`. It does not write
`commons.mno` or the excerpt. Copies of the git file still do not run as a
live container.

```
python3 host/subzero_walk.py
python3 host/subzero_walk.py --self-test
python3 -m unittest -v test_subzero_walk.py
```

No auth. No gate. Talk is not a land.
