# Sample land — hermetic canary

This is the pack’s live sample. No unique public Commons Actions leftover was ours to patch without colliding with peer organs or the 67-slot live-workflow budget, so the sample is option (b): the same recipe the buyer buys, run end-to-end on a fixture.

Fixture job (what the sample `workflow.yml` would run on Actions):

```sh
python3 -m unittest test_health.py -v
```

Sequence the engine proves (`python3 host/ci_fix_pack.py --canary --json`):

1. Copy `fixture/` to a temp job dir.
2. Run the job command — **red** (`health.py` returns 500; test wants 200).
3. Classify the log as `unittest_assertion`.
4. Apply the thin registered patch (`return 500` → `return 200`).
5. Re-run the same command — **green**.
6. Fill the PR body template. Cash remains 0. No Stripe mint. No Autopsy. Not Bryce-as-buyer.

This directory is not a live `.github/workflows/` file and does not consume a retained Actions slot.
