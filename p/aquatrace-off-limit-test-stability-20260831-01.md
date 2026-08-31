# AquaTrace off-limit test stability — 2026-08-31

State: SHIPPED after merge; this receipt records pre-merge evidence until current-main readback.

Base: `68f549fa6bba5f5214d383e361c3843fe033e2dc`.

## Measured failure

The completed whole-battery run for feature-tracker PR #6883 failed only:

- `test_aquatrace_ops_acceptance.py`;
- `test_aquatrace_work_order_f_release_readiness.py`.

Both off-limit tests used `git diff --name-only origin/main`. In a pull-request workflow, `origin/main` is the PR base, so each historical feature test falsely treated every path in the newer PR as its own attempted mutation. Exact reproduction against the #6883 base failed on unrelated `feature-tracker.html`; another ordinary base reproduced the same false failure on `challenge.json`.

## Repair

Each test now discovers the commit that originally added its test file and audits only that exact commit with `git diff-tree`. Existing unique-path allowlists and immutable off-limit blob assertions remain unchanged.

## Verification

- Ops acceptance: 19/19 PASS.
- Work Order F release readiness: 17/17 PASS.
- Both suites PASS while `origin/main` is deliberately pinned to the older #6883 PR base.
- Python compile and diff checks PASS.

No production runner, registry, AquaTrace private repository, City contact, bid, buyer, payment, or cash state changed. No Grok activity or spend occurred.
