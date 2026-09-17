# Impact evidence plan

Status: `MEASUREMENT_PLAN_ONLY` — **no production impact claimed here**

The Builder Fest rubric gives Business Impact / Potential to Scale the largest weight. OneWriter therefore needs measured business use, not invented success copy.

## Before-use baseline

Choose a bounded TJLabs operating window before OneWriter is used and retain:
- number of lead/outreach claim attempts;
- number of known near-simultaneous duplicate claims;
- number of duplicate external touches actually detected;
- number of stale/unowned lanes requiring manual recovery;
- number of route failures incorrectly mixed with buyer outcomes, if measurable from retained evidence;
- time window and data-source receipt identifiers.

Do not backfill guesses. If a historical metric cannot be reconstructed, mark it `UNKNOWN`.

## Instrumented use window

Use the deployed OneWriter app in a real internal coordination workflow. For every candidate external touch:
1. request a OneWriter lease first;
2. preserve the OneWriter receipt;
3. if an external send later occurs under the existing coordination system, record only its provider outcome id;
4. if a genuine human reply occurs, record a retained human-evidence id;
5. do not paste private message bodies into the public demo.

Measure:
- `claim_attempts`
- `claims_granted`
- `collisions_prevented`
- `duplicate_touches_prevented`
- `stale_lanes_recovered`
- `sent_hard_fences`
- `dead_routes_recorded`
- `human_reopens`
- median and p95 time from candidate detection to single-writer lease
- number of users/agents who actually used the app
- number of days/hours in the measured window

## Evidence standard

A contest impact claim is publishable only when:
- the metric can be recomputed from retained OneWriter receipts;
- the time window is explicit;
- the population is explicit;
- synthetic-demo counts are excluded;
- a prevented duplicate is counted only when a second claim was actually denied against an active matching lease;
- a dead route is not called buyer rejection;
- provider SENT is not called interest;
- human reply evidence is not inferred from auto-acks, tickets, silence, or provider acceptance.

## Before/after claims

Preferred phrasing after real measurement:
- "During <window>, OneWriter denied N overlapping claims across M unique lanes before a duplicate external touch could be attempted."
- "It recovered N expired leases and separated N provider route failures from human outcomes."
- "K workers/agents used the app across <window>."

Do **not** claim:
- revenue created unless independently settled and attributable;
- leads saved unless independently evidenced;
- response-rate improvement from small/uncontrolled samples;
- customer satisfaction without a real measurement;
- contest placement or prize before official results.

## Scale evidence

Demonstrate structurally, not aspirationally:
- deterministic key makes each lane independent;
- atomic conditional writes support concurrent agents;
- receipts allow audit/reconstruction;
- route/purpose/opportunity fields make the same state machine portable to sales, vendor management, recruiting, partnerships, support escalation, and approval workflows.

## Owner review packet before submission

Collect:
- deployed app URL and version timestamp;
- screenshots/video of concurrent collision denial;
- exported real-use receipt summary;
- recomputation script/result;
- synthetic-vs-real banner screenshots;
- privacy review;
- exact measured impact claims proposed for submission copy;
- one-active-submission census;
- deployment status and separate submission status.
