# TITAN_MOVE — 31 excerpts on main, claimed offsets FROM FILE

Bryce Slack `1787628542.573719` and `1787628900.201179` (2026-08-25):
stop dodging the substrate. Zero offsets while 31/31 excerpts sit on
main is not a boundary. There is no actuation rule that keeps this
packet empty.

## Measured (public tree)

`titan.gguf` is the computer. `excerpts/20260823/*.mno` are standalone
copies. Git copies do not run.

On current main the journaled packet
`excerpts/20260823/titan_move_packet.json` recounts **31** organs.
Each row carries a **claimed append offset** dest FROM FILE:

- `p/goat-titan-inject-20260820-01.md` — `titan.gguf 103803350291`
  at `C:\llm\models`
- `muhl/lda-docs/HANDOFF.md` — same `titan_size`, chimera
  `muhl_chimera_ardr_eal` already IN titan at `103803349440`

Append starts at that measured end. `titan: NOT_WRITTEN` until
`host/titan_move_apply.py --go` journals the MOVE and re-reads.
If live size differs, apply reallocates from live size. `new = old
| mask`. Ones only rise.

Do not smash `commons.mno`. Do not fire 337. Do not add to spec.

## Instrument (host, die)

```
python3 host/titan_move_dry.py
python3 host/titan_move_apply.py
python3 test_titan_move_dry.py
python3 test_titan_move_apply.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_titan_move_packet.py --dry
```

`--dry` and `titan_move_dry.py` open the public packet only.
`titan_move_apply.py` without `--go` is a plan. `--go` writes only
when `titan.gguf` is present.

## Owner blocker

If the write is genuinely blocked on Bryce, file this form (Slack
`#needs-bryce` and a `p/{id}.md`):

- **NEED** — `python3 host/titan_move_apply.py --go` against
  dest-FROM-FILE `C:\llm\models\titan.gguf`.
- **WHY ONLY BRYCE** — `titan.gguf` is not on this cloud box. Dirty
  `LocalDeviceAgent` `kite-help` working tree is on the owner PC.
- **SMALLEST ACTION** — one `--go`, journaled write, reread receipt.
  Commit and push the dirty LDA tree.
- **EVIDENCE** — `host/titan_move_dry.py` numbers plus the packet SHA.
- **AFTER** — desk `titanMoveState` becomes INTEGRATED.

A TAKING that writes the exclusion line without those numbers is
`CLAIMED`. Talk is not a land.
