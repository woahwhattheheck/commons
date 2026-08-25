# TITAN_MOVE — 31-organ owner-PC append written and reread

Bryce Slack `1787628542.573719`, `1787628900.201179`, and
`1787629309.162109` (2026-08-25): substrate work is first-class.
A receipt that brags Titan, `.mno`, organs, or 337 were untouched
is a skipped lane, not completion.

## Measured closure

`titan.gguf` is the computer. `excerpts/20260823/*.mno` are standalone
copies. Git copies do not run.

Owner-PC receipt `p/claudelocal-titan-move-go-20260825-01.md` and
main commit `b3fe1449560a359c87963d113c022ae3b8f86f73` close the write:

- `C:\llm\models\titan.gguf` before: **103803350291** bytes
- 31/31 organs written and reread; 31/31 `past_eof`
- after: **103812669582** bytes (**+9319291**)
- pure append under `new = old | mask`; no pre-existing byte changed

The current packet `excerpts/20260823/titan_move_packet.json` persists
`state=INTEGRATED`, `wrote=true`, `reread=true`, both 31/31 counts,
before/after sizes, receipt, and commit. Every row carries its actual
nonzero offset and `titan=WRITTEN`.
RIVET's `write_count` and `live_size_before/live_size_after` aliases remain
present and must equal the canonical count and `titan_size_*` fields.

Those offsets originated from dest FROM FILE:

- `p/goat-titan-inject-20260820-01.md` — `titan.gguf 103803350291`
  at `C:\llm\models`
- `muhl/lda-docs/HANDOFF.md` — same `titan_size`, chimera
  `muhl_chimera_ardr_eal` already IN titan at `103803349440`

The earlier `host/titan_move_apply.py --journal` public-image reread was
the pre-write candidate. It remains historical evidence. It is not the
Titan reread. The real `--go` receipt above supersedes that pending state.

The apply button is now crash-safe and idempotent: before a first byte it
atomically records `APPLYING` with fixed base/end/offsets; retry resumes
those offsets with OR semantics. A packet already `WRITTEN` makes `--go`
perform an exact read-only span/hash verification. It never allocates a
second append.

Smash/wipe of `commons.mno` is refused. `--inject 0x01` is wipe.
Address work uses dest FROM FILE.
Do not remint `claudelocal-titan-move-go-20260825-01` or the superseded
Slack-only taking `dio-titan-move-truth-reconcile-20260825-01`.

## Instrument (host, die)

```
python3 host/titan_move_dry.py
python3 host/titan_move_apply.py --journal
python3 host/titan_move_apply.py
python3 test_titan_move_dry.py
python3 test_titan_move_apply.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_titan_move_packet.py --dry
```

`--dry` and `titan_move_dry.py` rehash the public excerpts and classify
the persisted execution evidence. On the integrated packet, `--journal`
leaves the historical journal unchanged and default mode reports the
persisted closure. With `titan.gguf` present, `--go` is now a read-only
exact reread of the existing 31 spans.

## Owner action closed

There is no open Titan MOVE owner blocker. The write/reread and the dirty
`LocalDeviceAgent/kite-help` push were completed in the same owner-PC
receipt. A stale `NOT_WRITTEN`, future `--go`, or `#needs-bryce` request
for this MOVE is superseded by that measured closure.
