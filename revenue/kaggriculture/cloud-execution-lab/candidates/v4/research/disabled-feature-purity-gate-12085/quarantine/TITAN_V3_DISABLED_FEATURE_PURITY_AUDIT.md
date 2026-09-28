# TITAN V3 Disabled-Feature Purity Gate

**Canonical diagnosis anchor:** `c51049d671b55d282e0fed5df37a0be7c513a838`  
**Scope:** promotion bundles and standalone Python candidates  
**Purpose:** make “off means off” mechanically testable before tournament evaluation

## Why this gate exists

The V2 spatial-tempo regression was not caused by the active feature path. The feature was configured off, but `SpatialTempo.do_convert` still invoked `_continue_weed()` and `_continue_fert()` before its disable guard:

```python
self._continue_weed()
self._continue_fert()
if not self.enable:
    return
```

On the isolated Diamond and Gears witnesses, ablating those pre-guard helpers restored the V1 transcript exactly. The weed continuation path changed routes; the fertilizer continuation path was a no-op on those witnesses. This class of defect is broader than one patch: a disabled optional feature must not call helpers, mutate reachable state, import modules, or change control flow before its early return.

The owning source lane should still fix the spatial-tempo ordering and add behavior-level tests. This gate is deliberately independent: it prevents the same defect class from being reintroduced elsewhere or reappearing in generated bundles.

## Run it

Human output:

```bash
python3 titan_v3_disabled_feature_purity.py path/to/titan_bundle.zip
```

Machine-readable promotion output:

```bash
python3 titan_v3_disabled_feature_purity.py \
  path/to/titan_bundle.zip \
  --format json > disabled-feature-purity.json
```

Accepted inputs:

- a Python file;
- a directory, scanned recursively in stable path order;
- a ZIP archive;
- a tar, tar.gz, or tgz archive.

Archives are read in place. Members are never extracted, encrypted ZIP members are rejected, and Python members are capped at 8 MiB by default.

## What it proves

For functions containing one of these canonical disabled guards:

```python
if not self.enable:
    return

if self.enabled is False:
    return

if False == self.enabled:
    return
```

the scanner rejects effect-capable statements that appear before the first guard:

- function or method calls, awaits, yields, comprehensions, and named expressions;
- assignments through attributes or subscripts, augmented assignments, deletes, globals, and nonlocals;
- imports;
- branches, loops, context managers, try blocks, assertions, raises, and other control-flow exits;
- nested definitions whose decorators, defaults, annotations, or class machinery can execute.

It permits docstrings, `pass`, and side-effect-free local calculations. Additional flag leaf names can be supplied with repeated `--flag-name` arguments.

## Exit contract

| Exit | Meaning | Promotion action |
|---:|---|---|
| `0` | clean | continue to behavioral gates |
| `1` | one or more purity violations | reject candidate |
| `2` | input or Python parse error | reject candidate; repair artifact |

JSON output is stable and sorted. Every finding includes source/member path, line and column, qualified function name, guard line, feature expression, rule, and a compact statement excerpt.

## Suppression policy

A statement can be suppressed with a same-statement comment containing `titan-purity: allow`:

```python
self.required_probe()  # titan-purity: allow -- deterministic telemetry contract
```

Suppressions must include a reason and should be treated as promotion-review items. They are an escape hatch for proven mandatory telemetry, not a way to waive feature isolation.

## Integration point

Run the scanner immediately after candidate assembly and before expensive replay or tournament work:

1. assemble the exact candidate artifact;
2. run disabled-feature purity on that exact artifact;
3. preserve the JSON result beside the artifact hash;
4. reject on exit `1` or `2`;
5. only then enter transcript, seed, and score gates.

This ordering prevents a nominally disabled experiment from silently contaminating baseline measurements and makes bundle-level evidence match the bytes that are promoted.

## Regression suite

```bash
python3 -m unittest -v test_titan_v3_disabled_feature_purity.py
```

The suite covers the known two-call spatial ordering defect, corrected guard-first behavior, pure local calculations, effectful assignments, attribute/subscript mutation, custom flags, explicit suppression, syntax failure, nested functions, directory ordering, ZIP/tar scanning, member-size limits, exit codes, JSON schema, and byte stability.

## Limits

This is a syntactic fail-fast gate, not a complete semantic proof. It does not infer custom guard helpers, runtime monkeypatching, dynamically assembled code, or side effects hidden inside otherwise innocent descriptors. Behavior-level transcript tests remain mandatory. The scanner’s job is narrower and high-signal: a canonical disabled guard cannot come after obvious work.
