# TITAN cash-only HIRE bridge — SOL-FLYWHEEL

This package closes the causal gap between the submitted-V1 replay evidence and
a source-level Titan V3 repair target. It does **not** alter the controller,
runtime, release archive, configuration, or evaluator.

The input is the Slack custody object `107130860.json.gz` (`F0C0KEQ5MFY`). Both
compressed and decoded bytes are bound in `BRIDGE.json`.

## Exact result

Kaggle replay row `k` stores the action selected from row `k-1`'s observation.
Using that orientation, the replay contains one unusually clean natural control:

1. The agents first diverge at action row `2`. Bryce's market tape carries twelve
   more `BUY_SEED MELON` units than Apa's tape, a gross fixed-price commitment of
   `12 × $80 = $960`; Bryce also sells one more WHEAT. This is an upstream
   **program marker**, not a claim that the seed order alone causes every later
   dollar difference.
2. At observation rows `19` through `24`, both seats have byte-semantically
   identical own farm/private state after removing only `farm.money`. Their cash
   remains `$42` versus `$6`.
3. From observation row `24`, both select the exact same action at row `25`:
   `PICKUP WHEAT` plus four `HIRE` orders.
4. The extracted official mechanic charges the Fibonacci sequence
   `$1 + $1 + $2 + $3 = $7`. Apa executes all four hires and reaches four hands;
   Bryce executes only three and reaches three hands. The constrained seat is
   short by exactly **$1**.
5. Action rows `26`–`48` then submit four hand rows against Bryce's three
   observable hands. The 23-row unreachable suffix begins with productive work:
   `PICKUP WHEAT`, `NORTH`, `FEED`, `CARE`, `COLLECT_FERTILIZER`, `SOUTH`,
   `PLACE FERTILIZER`, `WEST`, `CARE`, followed by fourteen `PASS` rows.

This is stronger than a correlation between score and action cardinality. At the
HIRE boundary, non-cash state and selected action are equal; exact affordability
alone explains the observed `4`-versus-`3` execution.

## Why this matters for V3

The canonical `early_capital.py` records that its old broad cross-turn cash hoard
raised cash but lost official score and win rate, so this package does **not**
recommend restoring that policy. The new target is narrower:

```text
preserve at least $7 by observation row 24
while preserving represented production/seed commitments
and without forecasting rival receipts
```

Only one additional dollar is needed in this replay. A candidate should test a
bounded just-in-time seed or exact next-day-HIRE reserve policy, prove that every
deferred production obligation remains reachable, and then pass paired official
panels. The evidence here does not authorize automatic promotion.

This lane is distinct from:

- PR #11846, which proves generic cross-version unreachable submitted rows but
  explicitly does not prove source causality;
- PR #11865, which owns the broader economic-program differential analyzer;
- the generic HIRE/action-cardinality carrier, which can clip impossible rows but
  cannot recover the missing worker.

## Files

- `BRIDGE.json` — exact, self-bound causal receipt.
- `verify_bridge.py` — strict receipt verifier and optional raw-gzip reproducer.
- `test_verify_bridge.py` — 13 adversarial, orientation, transition, and tamper
  tests; the raw replay test activates when `TITAN_REPLAY_107130860` is set.
- `run_tests.sh` — compile, test, and manifest verification entrypoint.

The verifier rejects duplicate JSON keys, NaN/Infinity, malformed two-seat
frames, player/seat mismatches, non-isolated HIRE queues, non-cash state drift,
post-state orientation, observed transition mismatches, digest tampering, and
rehash attempts that change sealed facts. In a Commons checkout it also compares
its HIRE costs and MELON seed price with the current extracted `mechanics.py`.

## Evidence modes

The GitHub Actions workflow checks out `${{ github.event.pull_request.head.sha }}`
(or `github.sha` under manual dispatch), asserts that exact commit, verifies the
committed receipt plus the current mechanics contract, and retains the head SHA
with `BRIDGE.json`. It is intentionally a **manifest-mode exact-head** check.
The Slack custody gzip is not committed and is not available to hosted CI, so a
hosted green result must not be described as raw-replay reproduction.

Raw-custody reproduction is a separate mode. It requires the exact Slack object
and verifies both transport and decoded hashes before recomputing the receipt.
Independent review on PR #11930 reproduced that mode directly from
`F0C0KEQ5MFY`; the workflow does not substitute for that custody check.

## Verify

Committed receipt and source-mechanics contract:

```bash
cd revenue/kaggriculture/cloud-execution-lab/analysis/hire-reserve-causal-bridge-20260909-sol-flywheel
./run_tests.sh
```

Expected final line:

```text
PASS mode=manifest episode=107130860 cash=42/6 hire=4/3 shortfall=$1 unreachable_rows=23 report_sha256=1a66999a5aa86d3c4bf9d3e585a02f92b1d7e1c23af82dad10182c5348e6bfa5
```

Exact raw replay reproduction:

```bash
TITAN_REPLAY_107130860=/path/to/107130860.json.gz ./run_tests.sh
python -B verify_bridge.py --replay /path/to/107130860.json.gz
```

Source identities:

```text
gzip bytes   474669
gzip SHA-256 9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b
JSON bytes   31790508
JSON SHA-256 468845b1bc00f11a4d4a3deb2cc785a2ee222db31e6a0e88df2d7057f14ec6b1
receipt SHA  1a66999a5aa86d3c4bf9d3e585a02f92b1d7e1c23af82dad10182c5348e6bfa5
```

## Scope lock

No producer, policy source, route planner, selected-action transform, market
scheduler, HIRE runtime, engine, evaluator, archive, CURRENT pointer, opponent,
seed, provider, Kaggle submission, or spend surface is modified. No score delta,
seed-only causality, leaderboard strength, release readiness, or automatic
promotion is claimed.
