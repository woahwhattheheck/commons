# Grok automation harvest

`host/grok_automation_harvest.py` turns the durable exhaust of Grok-triggered
work into one frozen ledger. It does not need the Grok inbox, an authenticated
browser, or remaining interactive tokens.

The join is deliberately narrow:

1. `branch_truth_delta.py` supplies exact remote-head, ancestry, patch, and
   path/blob evidence at one frozen main SHA.
2. Canonical `p/*.md` blobs on that same SHA supply durable receipts.
3. An optional operator-observed automation manifest supplies names and
   trigger kinds. If it is absent, the count is `null` / `UNMEASURED`, never a
   fabricated zero.

Receipt names are discovery hints, not provenance. A `p/grok-*.md` file is
`GROK_NAMED_ONLY` until its `from`, `harness`, `model`, `surface`, or carrier
metadata explicitly identifies Grok. Explicit Gemini, Claude, Codex, Cursor,
ChatGPT, Kimi, or Flora metadata stays `EXPLICIT_OTHER_HARNESS` even when the
filename begins with `grok-`.

## Run

Fetch is intentionally outside both collectors. Freeze the refs first, then:

```text
python3 branch_truth_delta.py --repo . --remote origin --base main \
  --output /tmp/branch-truth.json

python3 host/grok_automation_harvest.py \
  --repo . \
  --base origin/main \
  --branch-truth /tmp/branch-truth.json \
  --automation-manifest /tmp/observed-automations.json \
  --output /tmp/grok-automation-harvest.json
```

Repeat `--branch-prefix` or `--receipt-prefix` to include a named downstream
lane such as ChartTrace. The output includes exact branch review rows, branch
and receipt digests, provenance/date/tag counts, and a compact recent-receipt
window. It copies no receipt bodies and performs no fetch, checkout, merge,
push, ref move, or deletion.

## Verify

```text
python3 -m unittest -v test_grok_automation_harvest.py
python3 -m unittest -v test_branch_truth_delta.py
```

The ledger says what Git proves. Grok UI state, notification delivery, prompt
bodies, token accounting, and any run that left no Git or canonical receipt
trace remain explicitly unmeasured.
