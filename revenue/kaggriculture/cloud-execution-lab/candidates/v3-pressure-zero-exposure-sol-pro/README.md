# TITAN V3 bounded zero-exposure certificate

This packet repairs the semantic hole in the proposed strict-pressure SELL
partition without taking ownership of its builder, panels, integration, or
promotion lane.

## Exact parent boundary

- parent branch head: `dfef8e57289b59c68bd45eb8f3fdd8ec610e0892`
- `pressure_priority.py` Git blob: `7261674962d10fc8bc6af5ff73ff9212c40f61ad`
- pinned observable mechanics Git blob: `044a4f9c0a4a44dde10ada57563238bcaf82075d`
- canonical TITAN runtime/config/archive/pointers: unchanged

The original proposal treated a same-sized proxy pressure of zero as a class
that exposed lots could cross. Rounded public prices make that unsafe. At public
inventory 9,999, the pinned curve is:

```text
TOMATO: 60, 60, 57 at inventory 9999, 10000, 10001
MILK:  169,160,158 at inventory 9999, 10000, 10001
```

For parent orders `SELL TOMATO 1`, then `SELL MILK 1`, a one-unit proxy reports
TOMATO pressure 0 and MILK pressure 9, so the proposed partition moves MILK
first. Against a two-unit rival TOMATO sale in slot 0, official lockstep prices
produce:

```text
parent:    own 229, rival 117, margin 112
proxy arm: own 226, rival 120, margin 106
change:    own  -3, rival  +3, margin  -6
```

The local plateau is therefore not a zero-exposure theorem.

## Repair theorem

For own lot quantity `n`, public inventory `I`, and the exact pinned quote curve
`p[k] = quote(I + k)`, its receipt after `q` rival units is

```text
R(q) = sum(p[q : q+n])
R(q+1) - R(q) = p[q+n] - p[q]
```

After verifying the public curve is finite, at or above the market floor,
consistent with the visible quote, and nonincreasing, bounded receipt invariance
is equivalent to:

```text
p[q] == p[q+n] for every q in [0, rival_bound)
```

That needs exactly `n + rival_bound` quote calls. The implementation returns one
of three dispositions:

- `CERTIFIED_ZERO`: own receipt is invariant for every delay through the bound;
- `EXPOSED`: at least one bounded delay strictly lowers own receipt;
- `BARRIER`: malformed, drifting, nonfinite, non-monotone, or otherwise
  unverifiable evidence.

The stable partition moves only `CERTIFIED_ZERO` lots behind `EXPOSED` lots.
Both classes preserve parent-relative order. `BARRIER` rows split blocks and
never move.

The bound is custody-bearing evidence, not a tuning parameter. A caller must
supply an externally justified upper bound on executable same-slot rival units.
Do not silently substitute `shedCapacity` unless the official-engine adapter
proves that it bounds the relevant rival flow in the tested state.

## Files

- `pressure_zero_exposure.py` — pure bounded certificate and stable partition.
- `materialize_pressure_certificate.py` — exact-parent, exact-mechanics,
  default-off postimage materializer with atomic output, compile/readback checks,
  strict receipt, and symlink/hard-link alias defenses.
- `official_plateau_witness.py` — exact pinned-curve and lockstep economic
  predecessor witness.
- `test_*.py` — 22 focused contracts, including 385 exhaustive small
  nonincreasing curves and generated-postimage execution.

## Validation

From this directory:

```bash
python -B -m py_compile *.py
python -B -m unittest -v
```

Local result on the authored bytes:

```text
Ran 22 tests in 0.038s
OK
```

The suite proves:

- the one-point TOMATO proxy-zero case is classified `EXPOSED` at delay 2;
- the rejected proxy postimage reorders MILK first while the bounded-certificate
  postimage preserves TOMATO first;
- the exact lockstep witness retains own `-3`, rival `+3`, margin `-6`;
- exposed, certified, duplicate, and barrier order stability;
- exact agreement with a brute-force oracle over 385 complete nonincreasing
  quote curves;
- `O(n + bound)` quote calls;
- malformed, nonfinite, below-floor, non-monotone, visible-mismatch, oversized,
  and derived-overflow inputs fail closed;
- exact source/mechanics blob drift, duplicate/missing patch anchors, and
  source/output hard-link aliases reject before publication;
- the detached postimage compiles, imports, executes the predecessor, preserves
  default behavior when certificate mode is absent, and leaves its inputs
  unchanged.

## Exact materialization

Place the helper beside the generated module, then run:

```bash
python materialize_pressure_certificate.py \
  --source /exact/parent/pressure_priority.py \
  --helper pressure_zero_exposure.py \
  --mechanics /exact/pinned/mechanics.py \
  --output /detached/pressure_priority.py \
  --receipt /detached/PRESSURE_ZERO_EXPOSURE_RECEIPT.json
```

The CLI accepts only the parent and mechanics blobs listed above. It patches four
single-count anchors, compiles the result, writes output and receipt atomically,
reads both back, and verifies all three inputs remained byte-identical.

The materialized transform adds only the default-off keyword
`zero_exposure_bound`. With it omitted, the inherited proxy ranking remains
byte-semantically active. With it supplied, the stable certificate partition
replaces proxy magnitude ordering for the eligible block.

## Swarm handoff

The strict-pressure builder owner should consume this semantic postimage only
after its separate indentation/compile transport repair is green. The game
executor should then run a matched three-arm current-package panel:

1. incumbent pressure behavior,
2. proxy strict partition,
3. bounded-certificate partition.

Retain tested-seat actions, first changed public world, own/rival/margin,
W/T/L, lost wins/new losses, and opponent-by-seat strata. A strong historical
proxy panel does not override the exact negative predecessor. Promotion remains
closed until the certificate arm is action-active, kills this witness, and
retains nonnegative paired economic gates on fresh sealed evidence.
