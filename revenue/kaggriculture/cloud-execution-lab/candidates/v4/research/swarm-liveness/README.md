# TITAN V4 Swarm Liveness / Orphan Recovery

`claim_liveness.py` is a dependency-free, read-only auditor for the fast-moving
multi-agent claim stream. It exists to answer a narrow coordination question:
**which claims are actually live, which are closed, which collided, which
became stale after a session disappeared, and which exact-lane claimant was
first?**

It belongs to the existing canonical `main:candidates/v4` workspace. It does
not create a sibling V4, does not mutate gameplay, and has no Slack/GitHub
credentials.

## Normalized event contract

One JSON object per line:

```json
{"ts":1789183752.102079,"lane":"ASTRA-LANTERN","session":"ASTRA","event":"CLAIM","canonical_root":"main:revenue/kaggriculture/cloud-execution-lab/candidates/v4","writes_repo":true,"requires_artifact":true}
```

Required fields are `ts`, `lane`, `session`, and `event`. Supported events are
`CLAIM`, `HEARTBEAT`, `COMPLETE`, `RELEASED`, `BLOCKED`, `REJECTED`, and
`SUPERSEDED`. `ts` may be Unix seconds or timezone-aware ISO-8601.

Repository-writing claims should bind `canonical_root`. `requires_artifact`
lets a claim require a durable artifact before `COMPLETE`. Optional
`event_id`, `artifact`, `channel`, and `thread_ts` preserve provenance.

## Safety semantics

- `STALE_CLAIM` is **routing evidence only**, never overwrite/merge authority.
- A fresh owner blocks recovery of stale owners for the same lane.
- Two fresh owners produce `COLLISION`.
- For a normalized exact lane, collision arbitration uses the timestamp of the
  currently-active `CLAIM`, not its latest heartbeat. The unique earliest fresh
  claimant is reported as an **advisory** `preferred_owner`; later fresh claims
  are `yield_candidates`.
- Equal earliest claim timestamps fail closed: no preferred owner is emitted;
  the tied sessions are listed in `tied_earliest_claimants`.
- Re-claiming after a terminal event starts a new ownership epoch and therefore
  gets a new claim timestamp.
- Arbitration is never overwrite, merge, validity, or promotion authority.
- A fresh owner plus an old silent owner produces `ACTIVE_WITH_STALE_OWNER`.
- Noncanonical V4 roots are anomalies.
- Repo-writing claims without a root binding are anomalies.
- Heartbeats without a live claim and terminal events without a claim are
  anomalies rather than silently repaired history.
- A claim marked `requires_artifact` cannot complete cleanly without one.

## Run

```bash
python -B claim_liveness.py adversarial-events.jsonl \
  --as-of 2000 --ttl-seconds 100 > report.json
python -B -m unittest -v test_claim_liveness.py test_claim_arbitration.py
python -O -B -m unittest -v test_claim_liveness.py test_claim_arbitration.py
```

The report is canonical compact JSON: deterministic lane/anomaly ordering,
explicit recovery candidates, claim-epoch timestamps, advisory arbitration,
summary counts, and policy booleans that make the non-authority boundary
machine-readable.

## Integration boundary

The tool deliberately consumes **normalized exported events** rather than
talking to Slack directly. Live connector sessions can translate claim and
closure messages into this schema, audit them, then route stale/collision
findings back to peers. The `lane` key is the overlap boundary: the tool does
not infer semantic overlap between differently named lanes. That keeps
workspace credentials out of the repository and prevents a timestamp rule from
pretending to solve scope equivalence.

It does not decide whether a gameplay mechanism is valid, strong, mergeable,
or promotable. It only closes coordination ambiguity around ownership and
liveness.
