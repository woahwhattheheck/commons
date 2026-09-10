# Titan V3 fail-closed sequential futility gate

Operation: `titan-v3-fail-closed-sequential-futility-20260909-01`

This adapter answers one expensive question safely while an official-engine
paired panel is still running:

> Is promotion already mathematically impossible under the frozen paired-game
> contract, even if every unrun cell finishes as favorably as the evidence
> permits?

It never promotes a partial panel. A valid partial snapshot returns either
`CONTINUE` or `FUTILE`. Once the exact opponent × seed × seat grid is complete,
the adapter delegates the same private snapshots to
`../../titan-v3-paired-game-gate/gate.py`; only that canonical gate may return
`PROMOTE`.

This is a throughput tool, not a weaker promotion policy. It lets a matrix
runner stop branches that cannot possibly pass and move scarce official-engine
workers to surviving challengers.

## Verdict and exit contract

| Exit | Verdict | Meaning |
|---:|---|---|
| `0` | `PROMOTE` | Complete panel; canonical paired gate promoted it. |
| `2` | `INVALID` | Input, identity, schema, score, snapshot, or provenance failure. |
| `3` | `FUTILE` / `REJECT` | Partial panel is provably unable to pass, or complete panel was rejected by the canonical gate. |
| `4` | `CONTINUE` | Valid partial panel; no sound futility proof yet. |

A scheduler may cancel remaining work only on exit `3` with verdict `FUTILE`.
It must not interpret `CONTINUE` as evidence of strength.

## Sound partial proofs

Without any numeric score assumption, the gate can already prove failure from:

- an observed W→T/L or T→L count above the contract cap;
- an observed baseline-win regression or new-loss count above its cap;
- a positive-cell fraction that cannot be rescued even if every remaining cell
  is positive;
- a positive seat-pair fraction that cannot be rescued even if every incomplete
  pair is positive;
- a median whose middle order statistic is already fixed below the threshold;
- a completed opponent or seat stratum whose mean is negative beyond the
  permitted count;
- an observed worst-cell delta below the declared floor; or
- a complete score-identical grid when a change is mandatory.

Partial means are intentionally **not** pruned from observed averages alone.
Unrun game deltas are unbounded unless an independently reviewed engine bound
has been supplied.

## Optional terminal-score envelope

Additional mean, margin, incomplete-stratum, pair, and unrun-worst-cell proofs
are available with both `--envelope` and `--bound-certificate`.

`ENVELOPE.json` has an exact, closed schema:

```json
{
  "schema_version": 1,
  "panel_id": "same-as-CONTRACT",
  "contract_sha256": "sha256-of-the-exact-CONTRACT.json-bytes",
  "terminal_score_min": 0,
  "terminal_score_max": 1000000,
  "certificate_sha256": "sha256-of-the-exact-bound-certificate-bytes"
}
```

The envelope and certificate are each single-open snapshotted. Their hashes are
included in the report, the envelope must bind the exact contract snapshot, and
every observed score must lie inside the certified interval. The numeric bound
is only as trustworthy as the reviewed certificate that derives it from the
pinned engine. A guessed leaderboard range, an observed historical maximum, or
a convenient test value is not a valid production certificate.

For a missing candidate cell with a known baseline row, the implementation uses
tighter cell-specific optimistic bounds:

- own-cash delta ≤ `terminal_score_max - baseline_own`;
- margin delta ≤ `(terminal_score_max - terminal_score_min) - baseline_margin`.

If the matching baseline cell has not run, it falls back to the globally safe
span and doubled-span bounds. Every calculation fails closed on non-finite
arithmetic.

## Input rules

The canonical contract and provenance schemas are reused unchanged. Baseline
and candidate JSONL files may contain any exact subset of the declared grid;
all present candidate cells must have matching baseline cells. A full cached
baseline with a growing candidate file is supported.

Absence means “not run yet.” A present row with a timeout, error, or any status
other than exactly `complete` is not absence and makes the evidence `INVALID`.
Unknown cells, duplicates, malformed scores, NaN/infinity, booleans used as
integers, duplicate JSON keys, symlinks, oversized inputs, provenance drift,
and mutation during snapshot acquisition also fail closed.

Each source is opened once, copied into a private snapshot while SHA-256 is
computed, parsed only from that snapshot, and re-hashed after evaluation. Source
replacement after acquisition cannot change the evaluated bytes or report.

## Usage

Run after each immutable candidate batch:

```bash
python3 futility.py \
  --contract /evidence/CONTRACT.json \
  --evidence /evidence/PROVENANCE.json \
  --baseline /evidence/canonical.GAMES.jsonl \
  --candidate /evidence/challenger.partial.GAMES.jsonl \
  --report /evidence/FUTILITY.json
```

With a reviewed engine-bound certificate:

```bash
python3 futility.py \
  --contract /evidence/CONTRACT.json \
  --evidence /evidence/PROVENANCE.json \
  --baseline /evidence/canonical.GAMES.jsonl \
  --candidate /evidence/challenger.partial.GAMES.jsonl \
  --envelope /evidence/ENVELOPE.json \
  --bound-certificate /evidence/BOUND-CERTIFICATE.md \
  --report /evidence/FUTILITY.json
```

The bundled synthetic example has three completed, non-positive cells under a
75% positive-cell requirement. Even granting all five missing cells a positive
result, the best final fraction is `5/8 = 0.625`, so it exits `3` with
`FUTILE`:

```bash
python3 futility.py \
  --contract example/CONTRACT.json \
  --evidence example/PROVENANCE.json \
  --baseline example/canonical.GAMES.jsonl \
  --candidate example/challenger.partial.GAMES.jsonl \
  --report /tmp/quorum-futility.json
```

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -m unittest -v test_futility.py
python3 -m compileall -q futility.py test_futility.py
```

Current local result: **32/32 passed**. Coverage includes empty and partial
panels, no-partial-promotion, complete delegation, deterministic reports,
positive-cell and positive-pair upper bounds, median order-statistic proofs,
result-regression caps, completed opponent/seat strata, observed and unrun
worst-cell failures, contract-bound mean and margin envelopes, exact envelope
and certificate hashes, out-of-envelope scores, explicit timeout/error rows,
missing baselines, extra/duplicate cells, duplicate JSON keys, symlinks,
source replacement after snapshot acquisition, and CLI exit semantics.

A deterministic soundness property test samples 250 frozen policies on a bounded
two-cell panel. Whenever the partial gate reports `FUTILE`, it enumerates every
legal completion from the certified score domain and evaluates each complete
panel with the canonical `metrics.analyze()` / `evaluate_policy()` path. The
current run found zero false cancellations. This is not a proof over unbounded
real arithmetic, but it is a direct predecessor-discriminating check of the
implementation against the canonical full-panel decision semantics.

## Non-claims

`FUTILE` is a proof about one frozen promotion contract, not a public leaderboard
score. `CONTINUE` is not evidence that a candidate is good. A complete
`PROMOTE` remains only the canonical gate's verdict for its exact panel; it does
not submit to Kaggle, change the release archive, alter `main.py::agent`, or
establish first place.
