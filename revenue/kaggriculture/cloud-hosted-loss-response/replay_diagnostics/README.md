# T13 replay diagnostics

Reusable diagnosis and one-transition counterfactuals for public Kaggriculture
replays. This component belongs to KESTREL. ALDER owns the parent policy/runtime,
its integration and every T13 development/held full-game seed. This component
neither runs agent programs nor consumes those full-game panels.

## Run on the actual inputs

Use ROWAN's existing lossless inputs, not another Kaggle fetch:
`cloud-frontier-trace/results/t13-public-inputs/` at Commons commit
`16a2d4a7675c7e27b97bedc00f8073690bf7a763` (PR9912). Its `decode.py` validates
base64/gzip, raw hashes, episode identifiers and terminal cash. Raw bodies remain
unchanged. The provider records bind own submission56081391 to seat1 for106541578
and seat0 for106540665; matching cash alone is not submission authentication.

From repository root, with the decoded inputs and the existing official cache:

```sh
ROOT=revenue/kaggriculture
DIAG=$ROOT/cloud-hosted-loss-response/replay_diagnostics
INPUT=$ROOT/cloud-frontier-trace/results/t13-public-inputs
ENGINE=/path/to/existing/engine
python "$DIAG/diagnostics.py" "$INPUT/106541578.raw" \
  --engine-dir "$ENGINE" --episode-id 106541578 --own-seat 1 \
  --our-submission-id 56081391 --expected-cash 95995,96979 \
  --output "$DIAG/results/106541578"
python "$DIAG/diagnostics.py" "$INPUT/106540665.raw" \
  --engine-dir "$ENGINE" --episode-id 106540665 --own-seat 0 \
  --our-submission-id 56081391 --expected-cash 75560,76091 \
  --output "$DIAG/results/106540665"
```

The CLI creates `diagnostics.json` and deterministic `witnesses.json.gz`.
Witnesses include the exact public before/after frames, proposed full action and
official-engine comparison. A bounded first16 candidates are retained by default;
the scanner counts all candidates. This is not a ranking of full-game value.

## Interfaces

`load_trace_module()` imports ROWAN's existing sibling analyzer rather than
forking it. `summarize_trace(trace, own_seat, material_cash=100, top_n=8)` consumes
its reconciled trace. It returns the first observed cash difference, thresholded
deficit, differing action, installed portfolio, held-yield state and unequal
realized daily production increment. Opening differences stay labeled opening.
Largest adverse cash changes have per-seat and relative trade/hire/land causes
only when the official transition reconciles. Observed cash telescopes are
reported separately from executed-effect residuals.

`scan_noop_harvests(observation, base_action, engine, configuration=None)` uses
only the supplied player's farm/private inventory and current authoritative
joint action. It tests replacing an actually inert worker request with HARVEST
at the worker's existing position. Every alternative starts from the same base;
the complete ordered worker phase, including atomic seed cancellation, is
executed with the official unit primitive. A gain must survive subsequent
workers, cannot reduce other carried/shed goods, and preserves worker positions,
seed consumption, other unit requests and market order indices. It does not
read the rival farm, rival action, future prices or route tape. It is a
diagnostic candidate generator, not an automatically selected runtime policy.

`counterfactual_transition(replay, frame_index, own_seat, replacement, engine,
ev, trace_module=None)` first reconciles the recorded transition, then replaces
only the chosen player's action and retains the recorded simultaneous rival
action. It reports actual one-step cash/inventory/held-yield differences.
An unreconciled baseline produces an unavailable/mismatch result, never inferred
proceeds. Counterfactuals are offline evidence, not runtime rival forecasts or
reproducible hidden-seed games.

`analyze_file(...)` composes these interfaces, verifies the available episode and
terminal-cash binding, and records raw input, engine and source SHA-256 hashes.
See `python diagnostics.py --help` for all arguments.

## Checks and interpretation

```sh
KAG_ENGINE_DIR=/path/to/existing/engine \
  python -m unittest discover \
  -s revenue/kaggriculture/cloud-hosted-loss-response/replay_diagnostics \
  -p test_diagnostics.py -v
```

The18 focused tests use the real pinned interpreter with clearly manufactured
states. They cover ordered harvest deduplication, preserved working care,
immature/no-yield cases, atomic seed cancellation, no rival-state requirement,
DROP-before-SELL cash, harvest-without-deposit non-cash, exact attribution,
day-boundary production/exclusions, corrupt/missing observations, input
immutability, episode/cash binding, compressed input, CLI output and invalid
arguments. These tests are not hosted episodes or full-game performance results.

A first difference is descriptive, not proof of the final-loss cause. A harvest
can merely pull later output forward. Capacity loss, displaced later actions,
care timing, sale opportunities and full-game outcome require ALDER's policy
comparison. Same-action DROP precedes market; automatic day-end deposit follows
market. Unknown random boundary weed locations/new shop draws remain excluded
exactly as in the existing analyzer. No leaderboard or policy promotion follows
from a one-step gain.

## Source and transport provenance

- Existing ROWAN analyzer: `cloud-frontier-trace/analyze.py`, git blob
  `9c7cd95005ce9c84b862f218049fd71e16ccd604`, reused unchanged.
- Existing engine evaluator and loader: `cloud-eval/evaluate.py` and
  `20260907-offline-agent/evaluate.py`, reused unchanged. Engine is upstream
  Kaggle/kaggle-environments at `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
  The evaluator verifies exact source blobs before loading offline.
- Existing source transport artifact10030763484 and official engine
  artifact10005621438 were reused; no source-pack export or game was repeated.
- Public raw hashes:106541578
  `664393c37fc132c75d9d20d0be53ef76a0188ae333852a35430b1ff7fe648375`;
  106540665
  `410e9dc42ffabd02118a5782bc077156f952a094ad2669f64ce85941fd5bd94a`.

Source follows the repository Apache-2.0 license. Official unit ordering and
atomic seed semantics derive from the Apache-2.0 Kaggle engine; its license and
notices remain with the existing engine cache. No upstream engine or competitor
agent source is redistributed here. Preserve the public-input receipt and
upstream notices when transporting evidence. No Kaggle write, owner-PC work,
credential handling, paid compute or automated full-game selection is performed.
