# TITAN V5 source-contract sentinel

This is an **advisory, default-OFF source audit**, not a gameplay policy and not
an evaluator replacement. It turns recurrent V5 regression families into
deterministic review hints before they become another production carrier.

The sentinel currently reports four boundary idioms:

- `RAW_OPCODE_INDEX`: `order[0]`-style reads that deserve a list/nonempty/parser check.
- `EXACT_ROW_LEN3`: exact three-field mini-grammars that can diverge from a pinned
  parser which accepts trailing metadata.
- `PUBLIC_OBS_COERCION`: `int(...)`/`float(...)` coercion of public
  `step/day/hour/player`, a common way to accept booleans, strings, stale clocks,
  or fractional aliases.
- `TRUTHY_CONFIG_COERCION`: `bool(...)` conversion of config/feature state before
  an exact declared-type boundary.

Findings are **not bug verdicts**. A reviewed use can be suppressed on the
finding line or immediately above it:

```python
# contract-sentinel: ignore=RAW_OPCODE_INDEX
opcode = order[0]
```

Use a comma-separated list or `ignore=*` for a reviewed intentional boundary.

## Run

From this directory:

```bash
python -B test_sentinel.py
python -O -B test_sentinel.py
python -B sentinel.py --json
```

The default scan is intentionally limited to current high-value V5 runtime and
reference surfaces. Arbitrary files/directories can be supplied explicitly:

```bash
python -B sentinel.py ../../.. --json
python -B sentinel.py path/to/module.py --fail-on PUBLIC_OBS_COERCION
```

By default the command exits zero even when it reports findings. `--fail-on` is
opt-in so this research tool cannot silently turn a heuristic into a merge gate.
It may be repeated for rules a carrier has explicitly adopted.

## Contract

- deterministic ordering and JSON;
- Python AST only (no execution/import of scanned source);
- no network, private state, evaluator mutation, or gameplay activation;
- syntax errors are reported as `SYNTAX_ERROR`;
- no claim that absence of findings proves engine parity.

The intended swarm workflow is: run the sentinel when opening a broad V5
correctness lane, inspect the receipt, fix source-proven mismatches under the
existing semantic owner, and suppress only reviewed intentional idioms.
