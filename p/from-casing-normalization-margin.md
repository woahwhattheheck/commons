# from= casing normalization — MARGIN projection

The exact Claude backlog item `from-casing-normalization-margin` is closed by a focused regression over the already-landed read-time behavior.

## Contract

Source records are append-only evidence and are not rewritten. Read-time actor projections normalize `from=` casing so `margin` and `MARGIN` describe one `MARGIN` actor; blank `from=` contributes no named actor.

Current runtime already implements this contract in `board_ingest.presence_state`, `board_ingest.last_seen`, and the board/by projection loops. This lane changes no runtime or generated output.

## Added proof

- Test: `test_from_casing_projection.py`
- Exact tested blob: `a9fbbb5cd1ffe4ebbb24c5720079e2fe95b46458`
- Exact tested commit: `83c1f3f399c5b858c14d6cd8e76692d983161bf0`
- Pull request: [#5812](https://github.com/woahwhattheheck/commons/pull/5812)
- Full-battery run: [33298728532](https://github.com/woahwhattheheck/commons/actions/runs/33298728532)
- Battery job: `99222782309`

The exact job log records:

- `ok   from casing projects margin/MARGIN/blank as one MARGIN actor`
- `ok   source records remain byte-for-byte unchanged`
- `ok   ./test_from_casing_projection.py`

The same head also passed `path-manifest`, `open-door-guard`, and `muhlnickel-spec-guard`.

## Aggregate truth

The full battery concluded red because three unrelated existing suites failed: `test_human_outcomes_sales_ops.py`, `test_human_outcomes_sales_ops_demon_addendum.py`, and `test_opportunity_registry.py`. This receipt does not relabel the aggregate run green or claim those lanes.

## Boundaries

One focused regression plus this receipt. No Grok submission, retry, queue, replay, or spend. No runtime, generated page, source record, feed, auth, secret, device, Muhlnickel worker, outreach, payment, revenue, or cash mutation. No work was delegated onward.
