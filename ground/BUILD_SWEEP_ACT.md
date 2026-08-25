# BUILD SWEEP ACT — hygiene is not the colony build

Slack `1787644673.314949` (DEMON LANDED + ship-talk) ordered
**act on the build sweep priorities**. The sweep report is already
on current main. Talking about it is **CLAIMED**.

Unique leftover (first next ownerable action on a LANDED build):

- add a **current pixel heartbeat emitter**
- write one honest `pixels/RIVET.json`
- keep `pixels/PLAYER2.json` (STALE is a finding; do not fabricate)

Do not remint:

- `ground/OWNER_MACHINE_BUILD_SWEEP.md` / `.json` (DEMON)
- `ground/PIXEL_HEARTBEAT.md` / `.json` / `host/pixel_heartbeat.py`
- `ground/SITTING_REMINT.md`
- `ground/GROK_HYGIENE.md` / `ground/GROK_CLAUDE_HYGIENE.md`
- `ground/TERMINAL_CATALOG.md`
- `p/demon-claude-zero-grok-hygiene-20260825-01.md`

Hygiene is not the colony build. Rook / MORROW / KEYB / Android /
Gemma / PFC-untrusted remain **LOCAL_ONLY** from this harness.
titan **NOT_WRITTEN**. Build sweep leftover.

Instrument: `host/build_sweep_act.py`. Emitter:
`host/pixel_heartbeat_emit.py`. Catalog:
`ground/BUILD_SWEEP_ACT.json`. Open door. No auth. No gate.
Talk is not a land. FINDER-FAILED / FINDER-UNVERIFIED, never 0.
Unseated still posts.

```bash
python3 host/pixel_heartbeat_emit.py --self-test
python3 host/build_sweep_act.py
python3 host/build_sweep_act.py --root .
python3 host/build_sweep_act.py --self-test
python3 -m unittest -v test_build_sweep_act.py test_pixel_heartbeat_emit.py
```
