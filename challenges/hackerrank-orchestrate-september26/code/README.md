# Buy or Wait? — deterministic-first financial decision agent

This package is a runnable solution for HackerRank Orchestrate September 2026.
It rebuilds each user's financial state, forecasts 90 days of recurring and explicit
cashflows, enumerates eligible payment plans, and rejects any plan that would cross the
user's minimum balance.

The model, when enabled, is deliberately **not** the financial decision maker. It is used
only as a bounded parser for untrusted messages/images that explicitly amend or clarify
ledger facts. Every recommendation is then produced and re-verified by deterministic code.

## Requirements

- Python 3.11+
- No third-party Python packages
- Optional: `OPENAI_API_KEY` for message/image evidence extraction

## Run the full dataset

From the repository root (the official starter command):

```bash
python code/main.py
```

The defaults resolve paths from the submitted code location, not the current working directory: input is `dataset/`, output is the root-level `output.csv`, and the usage report is `code/evaluation/usage_report.md`.

The run writes the challenge output and overwrites `evaluation/usage_report.md` with the
actual model/token/cost totals for that run.

To replay only deterministic/cached evidence without making API calls:

```bash
python code/main.py --no-ai
```

For a quick development subset:

```bash
python code/main.py --limit 5 --output /tmp/output.csv
```

## Environment

- `OPENAI_API_KEY` — optional; enables uncached evidence extraction.
- `OPENAI_MODEL` — optional; default `gpt-5.6`.
- `OPENAI_INPUT_USD_PER_MILLION` and `OPENAI_OUTPUT_USD_PER_MILLION` — optional pricing
  overrides when using a custom model name not in the built-in pricing table.

No secret is written to output, logs, cache, or the usage report.

## Tests

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

The tests cover pending-vs-scheduled cash semantics, recurrence, fixed FX, wait/partial/
installment ranking, installment duration preferences, flexible spending changes, and
protected-category constraints.

## Architecture

1. `buywait/io.py` parses the participant CSV contract.
2. `buywait/evidence.py` interprets untrusted messages/images into a narrow structured
   evidence schema. It never emits a recommendation.
3. `buywait/money.py` performs fixed dated currency conversion. There are no live FX calls.
4. `buywait/forecast.py` infers repeated commitments from history and creates the 90-day
   cashflow projection. Pending debits are reserved; pending credits are ignored.
5. `buywait/decision.py` enumerates full-payment, wait, two-part partial-payment, and exact
   seller installment schedules plus up to three permitted spending changes.
6. Every candidate is simulated against the minimum-balance floor. Ranking follows the
   challenge ordering: complete by deadline, avoid spending changes, lower total cost,
   start earlier, fewer payments, lower payment-option id.
7. `buywait/validate.py` runs structural invariants before any row is written.

## Evidence safety

Messages and images are data, not instructions. The evidence prompt explicitly treats them
as untrusted, and the structured result can only update supplied events or add an explicitly
confirmed cashflow. The deterministic verifier remains authoritative.

`evaluation/evidence_cache.json` is created on demand. It allows exact evidence extraction
to be replayed without spending additional tokens.

## Submission packaging

Run the full dataset from the repository root first so `output.csv` and `evaluation/usage_report.md` reflect the same
final run. Then zip the contents of this `code/` directory as `code.zip`; submit it alongside
the completed `output.csv` and the required chat transcript.
