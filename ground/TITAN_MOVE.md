# TITAN_MOVE — duplicate-append incident paused

Bryce Slack `1787628542.573719`, `1787628900.201179`, and
`1787629309.162109` (2026-08-25): substrate work is first-class.
A receipt that brags Titan, `.mno`, organs, or 337 were untouched
is a skipped lane, not completion.

## Historical first-span receipt

`titan.gguf` is the computer. `excerpts/20260823/*.mno` are standalone
copies. Git copies do not run.

Owner-PC receipt `p/claudelocal-titan-move-go-20260825-01.md` and
main commit `b3fe1449560a359c87963d113c022ae3b8f86f73` record the first write:

- `C:\llm\models\titan.gguf` before: **103803350291** bytes
- 31/31 organs written and reread; 31/31 `past_eof`
- after: **103812669582** bytes (**+9319291**)
- pure append under `new = old | mask`; no pre-existing byte changed

The packet `excerpts/20260823/titan_move_packet.json` preserves
`state=INTEGRATED`, `wrote=true`, `reread=true`, both 31/31 counts,
before/after sizes, receipt, and commit. Every row carries its actual
nonzero offset and `titan=WRITTEN`.
RIVET's `write_count` and `live_size_before/live_size_after` aliases remain
present and equal the canonical count and receipt-time `titan_size_*` fields.
Those fields describe the first historical receipt, not the current live EOF.

Under owner P0 `1787638509.277739`, the Claude-produced verification verdict
is quarantined as certification. It remains implementation/history evidence;
it cannot clear current state or support a merge by itself.

## Current non-Claude P0 measurement

DEMON / OpenAI Codex measured the owner artifact read-only in Slack
`1787638151.184599`:

- stable live size: **103831308164** bytes
- span 1: `[103803350291, 103812669582)`
- span 2: `[103812669582, 103821988873)`
- span 3: `[103821988873, 103831308164)`
- every span: **9319291** bytes
- every span SHA-256:
  `3754028086cd42e00131bea88f0e7fcf6dba2f84ad31cb70b88e655bbdd84e8c`

The same digest is independently calibrated from the 31 checked-in source
files in packet order. The live artifact therefore contains two duplicate
copies beyond the first. Which copy is canonical remains **UNRESOLVED**.
Current state is `NOT_LANDED` / `PAUSED_DUPLICATE_APPENDS`, not clean closure.

`--go` fail-closes when live size already equals `claimed_append_end`.
A second apply must not reallocate from the new size and append again.
Slack `1787638151.184599` measured three byte-identical 9,319,291-byte
copies and live size `103831308164`. That unexpected size now
refuse-closes through `host/titan_append_guard.py` without rewriting
the packet or truncating the artifact. Card:
[TITAN_APPEND_GUARD.md](./TITAN_APPEND_GUARD.md).

Those offsets originated from dest FROM FILE:

- `p/goat-titan-inject-20260820-01.md` — `titan.gguf 103803350291`
  at `C:\llm\models`
- `muhl/lda-docs/HANDOFF.md` — same `titan_size`, chimera
  `muhl_chimera_ardr_eal` already IN titan at `103803349440`

The earlier `host/titan_move_apply.py --journal` public-image reread was
the pre-write candidate. It remains historical evidence. It is not the
Titan reread. The first `--go` receipt superseded that pending state
historically, but it does not supersede the current duplicate-append incident.

The apply button is now crash-safe and idempotent: before a first byte it
atomically records `APPLYING` with fixed base/end/offsets; retry resumes
those offsets with OR semantics. A packet already `WRITTEN` makes `--go`
perform an exact read-only span/hash verification. It never reallocates from
the grown EOF. The verifier scans complete appended spans up to its published
bound, names the exact search range and known-present first-span calibration,
and reports `FINDER-FAILED` rather than a bare zero when it cannot cover the
search space. The current three-span fixture proves no fourth write occurs.

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

`--dry` and `titan_move_dry.py` rehash the public excerpts, derive the exact
9319291-byte aggregate digest, validate all three reported ranges, and keep
the incident paused. `--journal` leaves the historical journal unchanged.
With `titan.gguf` present, `--go` is read-only and detects repeated whole
MOVE spans without allocating or writing.

## Mutation paused / repair boundary

Preserve the **103831308164-byte** artifact exactly. Do not append, truncate,
dedupe, overwrite, rerun the MOVE, repair, or label the first copy canonical.
DIO owns the canonical repo guard/classifier/docs/tests; JOJO owns writer/run
lineage and owner-machine repair coordination; RIVET's distinct lane owns the
freeze catalog and `apply:false` measured repair plan. Any eventual mutation
requires exact owner authorization after byte boundaries, preimage,
backup/rollback, before/after/tail hashes, and downstream registry effects are
published. This is a specific incident pause, not a blanket substrate ban.
