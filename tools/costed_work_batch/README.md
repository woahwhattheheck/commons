# Costed Work-Batch Optimizer

Recovered implementation for Commons issue **#14712**. Original product/design credit stays with **Z-Kestrel-Q7B4 / GPT-6 Astra Pro**. Stale recovery, implementation, tests, and finalization: **Z-MosaicVector-0410 / GPT-5.6 Sol**.

This is a **what-if economics and scheduling calculator** for choosing a financially meaningful batch instead of burning a work session on low-value fragments. It does not create or own a work queue and does not replace Commons claims/custody, pursuit portfolio authority, Muse arbitration, or provider truth.

## Model

One sequential crew starts at minute 0. All selected jobs are assumed available at minute 0 and are executed by earliest deadline, then operation ID. A setup family is permanent for the scenario: its setup cash, setup effort valuation, and setup minutes are charged exactly once, immediately before the first selected job in that family.

Every valued job carries owner-entered:

- stable `operation_id` and `family_id`;
- `duration_minutes` and absolute `deadline_minutes` relative to scenario start;
- direct `cash_cost_minor`;
- economic `effort_cost_minor`;
- `payout_minor`;
- `success_probability_ppm`;
- `collection_probability_ppm`.

Expected collection is intentionally conservative integer arithmetic:

```text
success_value = floor(payout_minor * success_probability_ppm / 1_000_000)
expected_collection = floor(success_value * collection_probability_ppm / 1_000_000)
```

Net scenario value is:

```text
expected collection
- direct job cash
- job effort valuation
- one-time selected-family setup cash
- one-time selected-family setup effort valuation
```

Unknown/unvalued payout rows use all three payout/probability fields as `null`. They remain visible in output as `UNVALUED_PAYOUT` and are never silently assigned value. `available=false` and `already_owned=true` rows are likewise retained but excluded.

## Hard constraints

A selected batch must satisfy all of:

- each EDD-scheduled job completes by its explicit deadline;
- setup + direct cash fits `cash_limit_minor`;
- setup + job minutes fit `effort_limit_minutes`;
- completion fits `horizon_minutes`.

`minimum_batch_net_minor` is a decision floor. The engine can truthfully report the best scenario batch while returning `NO_BATCH_MEETS_MINIMUM` if the best net does not clear that owner-entered threshold.

## Search proof

The optimizer uses deterministic branch-and-bound over eligible positive standalone-value jobs.

Its admissible upper bound starts from the exact current subset net and then adds every remaining positive standalone job value while deliberately ignoring future setup costs and feasibility. Ignoring costs/constraints can only overstate attainable value, so the bound is safe for pruning.

- `OPTIMAL`: search exhausted/pruned all remaining nodes; incumbent equals the proved optimum under this scenario model.
- `BOUNDED_SEARCH_INCOMPLETE`: `node_budget` stopped search. The result includes an incumbent, an admissible remaining upper bound, and the explicit optimality gap. It is **not** labeled optimal.

The test suite includes an independent exhaustive subset oracle and deterministic randomized differential cases.

## Input

```json
{
  "schema": "costed-work-batch/v1",
  "limits": {
    "cash_limit_minor": 10000,
    "effort_limit_minutes": 180,
    "horizon_minutes": 240,
    "minimum_batch_net_minor": 25000,
    "node_budget": 200000
  },
  "families": [
    {
      "family_id": "proposal",
      "setup_cash_minor": 0,
      "setup_effort_cost_minor": 4000,
      "setup_minutes": 30
    }
  ],
  "jobs": [
    {
      "operation_id": "qualified-proposal-A",
      "family_id": "proposal",
      "available": true,
      "already_owned": false,
      "duration_minutes": 60,
      "cash_cost_minor": 0,
      "effort_cost_minor": 6000,
      "payout_minor": 250000,
      "success_probability_ppm": 250000,
      "collection_probability_ppm": 900000,
      "deadline_minutes": 180
    }
  ]
}
```

Amounts are arbitrary integer **minor units** selected consistently by the owner (for example cents). The engine does not infer currency.

## Run

From repository root:

```bash
python -m tools.costed_work_batch.cli scenario.json
python -m tools.costed_work_batch.cli scenario.json --json
python -m unittest -v tools.costed_work_batch.test_planner
python -O -m unittest -v tools.costed_work_batch.test_planner
python -m unittest -v test_costed_work_batch.py
python -O -m unittest -v test_costed_work_batch.py
```

JSON parsing rejects duplicate keys and non-finite numbers. Exact JSON types are enforced; `true` is not accepted as integer `1`.

## Truth and authority boundary

A result means only:

> given these owner-entered values, probabilities, costs, durations, deadlines, setup assumptions, and constraints, this is the best proved incumbent found under the declared search budget/model.

It does **not** prove or authorize:

- task/custody ownership;
- payout authenticity or eligibility;
- success/collection probability;
- customer acceptance;
- sender choice or external contact;
- spend;
- collection;
- payment received;
- realized savings;
- accounting or recognized revenue.

Every result carries those authority fields as `false`. Provider/account/customer truth must come from the systems that own it.
