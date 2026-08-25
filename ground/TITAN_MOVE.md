# TITAN_MOVE — 31 excerpts written and reread on titan.gguf

Bryce Slack `1787628542.573719`, `1787628900.201179`, and
`1787629309.162109` (2026-08-25): substrate work is first-class.
A receipt that brags Titan, `.mno`, organs, or 337 were untouched
is a skipped lane, not completion.

## Measured (public tree + owner-PC write)

`titan.gguf` is the computer. `excerpts/20260823/*.mno` are standalone
copies. Git copies do not run.

Owner-PC `--go` on dest-FROM-FILE `C:\llm\models\titan.gguf` is already
real. Receipt `p/claudelocal-titan-move-go-20260825-01.md` at
`b3fe1449560a359c87963d113c022ae3b8f86f73`:

- live size before = claimed base `103803350291`
- 31/31 organs journaled, 31/31 reread true, 31/31 past_eof
- live size after `103812669582` (`+9319291`)
- packet `titan=WRITTEN`

The leftover after that write was classification, not another append.
`land.js` used to discard packet reread (`reread: false`). The desk now
maps the checked-in packet through `packetRowFromJson` into
`titanMoveState`. A WRITTEN packet with `reread` / `write_count` /
`reread_count` / size facts classifies **INTEGRATED**.

`--go` fail-closes when live size already equals `claimed_append_end`.
A second apply must not reallocate from the new size and append again.

Smash/wipe of `commons.mno` is refused. `--inject 0x01` is wipe.
Address work uses dest FROM FILE. Do not remint
`claudelocal-titan-move-go-20260825-01` or
`dio-titan-move-truth-reconcile-20260825-01`.

## Instrument (host, die)

```
python3 host/titan_move_dry.py
python3 host/titan_move_apply.py --journal
python3 host/titan_move_apply.py
python3 test_titan_move_dry.py
python3 test_titan_move_apply.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_titan_move_packet.py --dry
```

`--dry` and `titan_move_dry.py` open the public packet only.
`--journal` works the 31 `.mno` binaries. `titan_move_apply.py`
without `--go` is a plan. `--go` writes only when `titan.gguf`
is present and not already at `claimed_append_end`.

## Owner blocker

Closed for this MOVE. The write/reread already happened on the owner
PC. A TAKING that still says NOT_WRITTEN / CANDIDATE without measuring
the packet facts is `CLAIMED`. Talk is not a land.
