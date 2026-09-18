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

**Input-authentication boundary:** this compiler does not dereference
`source_ref` and therefore does not authenticate a caller's `source_class`.
Its packet is valid only after an upstream collector has bound each event to
retained provider/human/procurement/coordination evidence. Output carries
`input_authentication.verified_by_compiler=false` and
`UPSTREAM_AUTHENTICATED_RETAINED_EVENTS` so a caller-asserted packet cannot be
mistaken for independently verified truth.

Within that pre-authenticated packet, provider state must come from
provider-class events; human reply/decline or partner acceptance must come from
human-class events. Coordination intent (`TAKE`, `MUSE_PENDING`,
`MUSE_SELECTED`, `LEASE_CONSUMED`) cannot mint or erase provider/human
state.

The source-class matrix, state-specific currentness basis, identifier grammar,
resource ceilings, and all-false authority policy are captured at first import.
Compiled artifacts bind that exact semantic generation as
`policy_generation_sha256`; ordinary post-import rebinding of exported policy
or helper names cannot widen compile/verify semantics for the loaded compiler.

A correction may supersede only an older event from the **same authenticated
source class**, must be strictly later in time, and cannot reach backward across
generations. This lets newer provider/human/procurement evidence retire stale
modeled state without allowing coordination evidence to erase stronger truth.
Superseded rows remain in the canonical retained-event history and therefore
remain bound into the exact event digest; only the active reduction view omits
them.

Schema v1 has no authenticated reopen/reset event, and retained
`PROVIDER_SENT` evidence is deliberately non-retirable. Therefore any second
provider send in the same business lane is classified as
`COLLISION_DUPLICATE_SEND_DNR`, even if a caller changes generation, route, or
adds a correction edge. Generation/route changes cannot reset send permission,
and a later coordination generation cannot hide an earlier retained provider
send. A later `BOUNCED` or `DEAD_ROUTE` event on another route/generation
remains retained evidence but cannot downgrade an already-contacted lane back to
transport-only truth; the retained successful send keeps the lane DNR.

Each event repeats the lane/opportunity/counterparty/purpose identity, so a
retained event transplanted from another lane fails closed. Alternate route IDs
do not change the business identity or reset permission.

## Currentness

The trusted evaluation timestamp is supplied outside the event packet. Packets
may choose a **smaller** freshness horizon with `currentness_seconds`, but the
compiler enforces a code-owned maximum of 604800 seconds (7 days). A packet
cannot extend that ceiling. Actionable intent/readiness states age from the
latest event that actually establishes that state—not from an unrelated newer
coordination event—and stale states fail to `HOLD_EVIDENCE`. Terminal/DNR
transport truth is retained rather than incorrectly becoming fresh authority on
historical replay.

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
- strict JSON, duplicate keys/event IDs, floats/nonfinite, lexically oversized
  integers, deep nesting, unsafe integers, bool-as-int, lone surrogates,
  control-shaped IDs, future events, bounded event count/depth/nodes/bytes,
  generation regression, cross-generation retained provider truth and
  second-send collision, same-source authenticated correction with retained
  superseded-history digest binding, coordination-cannot-erase authority,
  provider-send non-retirement, later unrelated route-bounce send preservation,
  post-import policy/helper rebinding resistance, supersession-cycle rejection,
  compiler-bounded currentness, state-basis currentness,
  lease-without-provider HOLD, conflicting
  procurement/human terminal truth, event transplant, replay/currentness,
  malformed projection blocks, semantic tamper, and CLI create-exclusive
  replay.

Expected proof:
`python -m unittest -v test_revenue_lane_current_state.py`,
the same under real `python -O`, plus `py_compile`.
