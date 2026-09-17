# Revenue lane current-state compiler

Issue contract: `#15750`.

This package turns retained, explicit coordination/provider/human/procurement
events for one `opportunity × counterparty × purpose` lane into a deterministic
current operational state. It exists to keep stale issue prose from being
mistaken for current outbound authority.

## Safety boundary

The compiler is offline and source-reference opaque. It never sends email,
calls Muse, dereferences an evidence URL, updates a provider, moves money,
submits a proposal, or recognizes revenue. Every rendered CURRENT STATE block
contains the same all-false authority ceiling.

Provider state must come from provider-class events; human reply/decline or
partner acceptance must come from human-class events. Coordination intent
(`TAKE`, `MUSE_PENDING`, `MUSE_SELECTED`) cannot mint a sent or human state.
A second provider send in the same authorization generation is preserved and
classified as `COLLISION_DUPLICATE_SEND_DNR`, not silently deduplicated.

Each event repeats the lane/opportunity/counterparty/purpose identity, so a
retained event transplanted from another lane fails closed. Alternate route IDs
do not change the business identity or reset permission.

## Currentness

The trusted evaluation timestamp is supplied outside the event packet. Packets
also carry an owner-authored `currentness_seconds`. Actionable intent/readiness
states age to `HOLD_EVIDENCE`; terminal/DNR transport truth is retained rather
than incorrectly becoming fresh authority on replay.

## Projection

Output includes:
- canonical state + semantic receipt;
- a bounded Markdown block marked by
  `REVENUE_LANE_CURRENT_STATE:BEGIN/END`;
- stale-body findings for contradicted phrases such as `NOT SENT`,
  `MUSE_PENDING`, `PACKET_PENDING`, `awaiting reply`, or `no partner contact`;
- a **dry-run only** patch plan with expected/proposed body SHA-256.

The core does not apply the patch. A future writer must compare the expected
body digest and may replace only the bounded machine-owned block.

## CLI

```text
python -m coordination.revenue_lane_state.cli compile \
  --events lane.json --body issue.md \
  --evaluation-time 2026-09-17T21:00:00Z --output state.json

python -m coordination.revenue_lane_state.cli verify \
  --events lane.json --body issue.md \
  --evaluation-time 2026-09-17T21:00:00Z --artifact state.json
```

`compile` uses create-exclusive output and refuses overwrite.

## Acceptance coverage

`test_revenue_lane_current_state.py` contains redacted synthetic fixtures for:
- Raleigh/CrossVue stale `NOT SENT` after provider send;
- E-470 identity-separated same-state reduction;
- Legal Aid/Pi9 bounced first route plus two concurrent sends in the next
  generation;
- CPCA packet-pending → packet-received progression;
- Pragmatic-style human timeline decline;
- Kentucky-style stale `no partner contact` after outreach;
- transport bounce vs human decline;
- strict JSON, duplicate keys/event IDs, floats/nonfinite, unsafe integers,
  bool-as-int, lone surrogates, control-shaped IDs, future events,
  generation regression, event transplant, replay/currentness, supersession,
  malformed projection blocks, semantic tamper, and CLI create-exclusive replay.

Expected proof:
`python -m unittest -v test_revenue_lane_current_state.py`,
the same under real `python -O`, plus `py_compile`.
