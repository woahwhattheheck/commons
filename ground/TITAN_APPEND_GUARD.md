# TITAN APPEND GUARD — three identical copies is a pause

Slack `1787638151.184599` (2026-08-25), DEMON P0:

> TITAN CONTAINS THREE BYTE-IDENTICAL APPENDS — PAUSE FURTHER
> APPEND MUTATIONS. stable size 103,831,308,164. three spans of
> 9,319,291 bytes. all SHA-256
> `3754028086cd42e00131bea88f0e7fcf6dba2f84ad31cb70b88e655bbdd84e8c`.
> Do NOT truncate, dedupe, overwrite, rerun the append, or label
> the first copy canonical without owner authorization.

A Slack P0 is **CLAIMED**. The leftover is a fixture-tested
refuse-close so `--go` cannot reallocate from the unexpected size
and write a fourth copy. It does not write `titan.gguf`. It does
not smash `commons.mno`.

## Assigned lanes (not this leftover)

- **DIO + JOJO** — owner-machine live hash / reread of
  `C:\llm\models\titan.gguf`. Use your names. Joint incident lane.
- **Owner-authorized repair** — picking a canonical size, dropping
  copies 2–3, or relabeling the packet. BRYCE/ZERO only.
- **CML PR 2108 / working-builds / flight recorder** — other lanes.

## The hole

`host/titan_move_apply.py` fail-closed only when live size already
equaled `claimed_append_end` (`103812669582`). At the measured
`103831308164` it treated the size as a new base and would append
again. That is how a second unexpected copy becomes a third.

Unknown live size is also a pause. `refuse_further_append(None)`
and an unreadable size fail-close. They do not return False and
let `--go` proceed. Synthetic only. No live Titan mutation.

## Measure

Instrument: `host/titan_append_guard.py`. Stdlib only. Catalog:
`ground/TITAN_APPEND_GUARD.json`. It reads the tree and a small
fixture. It does not open the owner-PC titan file.

```bash
python3 host/titan_append_guard.py
python3 host/titan_append_guard.py --root .
python3 host/titan_append_guard.py --self-test
python3 -m unittest -v test_titan_append_guard.py
python3 -m unittest -v test_titan_move_apply.py
```

The leftover is **INTEGRATED** when the frozen numbers match and
the fixture refuse-closes a second/third identical append.
`apply` stays false. Talk that repeats the three spans without this
leftover is **CLAIMED**.

## Repair plan (apply:false)

- Preserve `103831308164` exactly while investigating.
- Copy-on-write snapshot before any later mutation. Rollback =
  restore that snapshot. No in-place shrink.
- First copy `[103803350291,103812669582)` matches the current
  packet. Copies 2 and 3 sit outside the organ map.
- Packet `live_size_after` `103812669582` is STALE.
- Do not label copy 1 canonical without owner authorization and
  full contract evidence.

Possessing the link is authorization. No auth. No gate.
