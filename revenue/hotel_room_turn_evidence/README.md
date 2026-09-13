# Hotel Room-Turn Evidence Pilot

Owner/finalizer: **Z-KolmogorovFlint-914108-P7C2 (`ZKF-P7C2`) / GPT-5.6 Sol**

This is the fulfillment carrier behind the recurring **$2,500 fixed / one property / seven days** hotel room-turn evidence pilot. It is deliberately offline and de-identified: it compiles agreed operational evidence into deterministic per-room `READY` or `BLOCKED` receipts without writing to a PMS, handling guest records, dispatching staff, charging guests, or claiming payment/revenue.

## Decision contract

A room is `READY` only when all three evidence classes are clean for the **same current turnover generation**:

1. fresh housekeeping clearance;
2. fresh maintenance clearance; and
3. fresh release by a manager named in the independently retained policy.

Everything ambiguous fails closed. Missing evidence, stale evidence, future timestamps, same-timestamp conflict, explicit blocks, wrong-turn evidence, and unauthorized manager release produce `BLOCKED` with reason codes. An old turnover cannot clear a new one.

Exact duplicate event replay is idempotent. The same `event_id` with different content is rejected.

## Trust boundary

The compile operator retains the canonical policy bytes and their SHA-256 outside the untrusted evidence packet. The compiler refuses policy drift unless the independently supplied policy SHA matches the exact canonical policy bytes, and then separately enforces the fixed commercial contract ($2,500 / 7 days).

The report contains a deterministic SHA-256 receipt, but the verifier does **not** trust that embedded hash by itself. `verify` and `render` require the independently retained report receipt printed by `compile`; editing the report and resealing its embedded hash therefore does not pass verification against the retained receipt.

Evidence `source_ref_sha256` values are evidence references, not proof that an external PMS or other system authenticated the source. A paid engagement must define what source artifact each digest commits to and retain those source artifacts separately.

Production compile owns current UTC time. There is no `--now`, `--as-of`, or freshness-policy override in the CLI.

## Frozen synthetic proof

The fixture has six rooms and 18 unique events (plus one exact replay):

| Room | Expected | Why |
|---|---|---|
| 101 | READY | three fresh, clear, same-turn signals |
| 102 | READY | same, plus exact duplicate manager event replay |
| 103 | BLOCKED | housekeeping block + missing manager release |
| 104 | BLOCKED | stale housekeeping |
| 105 | BLOCKED | conflicting maintenance evidence at the same latest timestamp |
| 106 | BLOCKED | manager release exists only for the wrong turnover generation |

At trusted test time `2026-09-13T15:30:00Z`, the deterministic report is **2 READY / 4 BLOCKED**.

Frozen policy SHA-256:

`8a301398647177ce4a9e9575270979041a7c7cd0a83eb9b3d7ab45e6eaf17a14`

## Run

```bash
cd revenue/hotel_room_turn_evidence
POLICY_SHA=8a301398647177ce4a9e9575270979041a7c7cd0a83eb9b3d7ab45e6eaf17a14

python -m unittest -v test_compiler.py
python -O -m unittest -v test_compiler.py

REPORT_SHA=$(python compiler.py compile \
  --policy fixtures/policy.json \
  --evidence fixtures/evidence.json \
  --expected-policy-sha256 "$POLICY_SHA" \
  --out /tmp/hotel-room-turn-report.json)

python compiler.py verify \
  --report /tmp/hotel-room-turn-report.json \
  --expected-policy-sha256 "$POLICY_SHA" \
  --expected-report-sha256 "$REPORT_SHA"

python compiler.py render \
  --report /tmp/hotel-room-turn-report.json \
  --expected-policy-sha256 "$POLICY_SHA" \
  --expected-report-sha256 "$REPORT_SHA" \
  --out /tmp/hotel-room-turn-acceptance.md
```

Because production compile uses actual current UTC, the frozen fixture is for test/replay semantics, not a perpetual `READY` demo. Old fixture events correctly age into `BLOCKED`.

## Hostile proof

The suite exercises policy-root mismatch, commercial drift, bool/int aliasing, duplicate JSON keys, unknown fields, exact replay dedupe, conflicting replay rejection, input-order determinism, stale/future/conflicting/wrong-turn/unauthorized evidence, unknown-room and property mismatch, embedded tamper, attacker reseal against retained receipt, policy-root mismatch at verify, exclusive output, symlink input refusal, CLI clock-override refusal, and normal/`python -O` byte equivalence at a trusted test instant.

This carrier is fulfillment readiness only. It is not a buyer acceptance, contract, authorization to access a property system, payment record, cash receipt, or revenue-recognition event.
