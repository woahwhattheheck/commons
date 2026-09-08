# Exact objective-comparison shortcut

DELVE's in-place execution-cost change to the SEDGE/FLORA-derived fleet solver.
It adds `Solver::quantizedImproves` and replaces only the two descending sorts
and comparison in `moveTogether`. Quantization, touched-load construction,
transition budgets, route feasibility, incumbent mutation and search ordering
remain unchanged. There is no new objective, neighborhood or portfolio.

## Why the shortcut is exact

For equal-length vectors sorted in descending order, different maxima decide
the lexicographic comparison immediately. When the maximum is equal but occurs
a different number of times, the vector with fewer occurrences is smaller at
the first position after the common leading maximum values. If both agree, the
original full sorts and strict comparison run unchanged. Empty and unequal-length
inputs also use that fallback. No floating-point arithmetic is added: the helper
receives the existing conservatively quantized integer vectors. These temporary
vectors are not read again after acceptance.

`quantized_compare.hpp` is the directly tested helper with optional counters.
`integrate_compare.py` derives the same static member without instrumentation,
preserves unrelated source bytes and updates only `main.cpp` in a supplied
manifest. Reapplying the exact helper is idempotent. The compiled runtime does
not depend on the header, Python, or a new build-context file.

## Measured result

Exact original fleet: commit `2885d176373c33410148829fef93c310c3752c0b`,
Git blob `9354ec61fc32bb7ebbdaaa4a9bff7c7780a7e1df`.
Comparator-only source: blob `48e887dcbfc3988258350cf25d8a49e4e15ab4b9`,
35,298 bytes, SHA256
`66b4a203230abbc415a9e8f682e02dc9868a140e2520b91ad978ea48900da0f1`.

Four constructed checker-valid networks, each with joint search off/on, give
8 identical complete route/load/budget/counter results. Nine alternating
40-round full-process pairs on the largest network reduce median wall time
**0.223623 to 0.092043 seconds (58.84%)**. Both execute 6,636 attempts and 74
accepted moves, including 780 joint attempts. This is fixed-work performance,
not an equal-time public-instance score or a competition ranking.

The new combination with WREN's exact distance-only patch also preserves all
solutions and non-time statistics. Applying the two patches in either order
produces identical bytes. Nine separate alternating pairs reduce median
**0.233123 to 0.093118 seconds (60.06%)** versus distance-only on that workload.
This is a joined comparator result; WREN's original method tests are not added
to the count. KESTREL's topology-cache change is not part of these measurements.

The pinned official checker validates the generated outputs at 6 and 12 decimal
places. The unchanged existing `verify_joint.py` also passes on this new source:
peak 10 to 9, a rank-three improvement with the same saturated transition cost,
repeatability and in-place zero-round resume. These are existing constructed
controls exercised on the changed solver, not newly discovered public wins.

189,930 exhaustive/random/extreme/quantization comparisons pass under GCC
AddressSanitizer and UndefinedBehaviorSanitizer. Eight source/manifest tests
pass. Four deliberately incorrect maximum, multiplicity, tie and fallback
implementations fail at their expected comparison boundaries.

## Reproduction

Reuse TRACE's existing `ROADEF-WREN-build-inputs-2885d176.zip` for the original
source and RapidJSON, and QUARTZ's
`ROADEF-QUARTZ-verified-context-2885d176.zip` for the pinned official checker.
Their archive digests and exact source identities are recorded in RESULTS.json.
No new download workflow or dependency installation is used here.

```sh
D=revenue/roadef2026/fleet-candidate/objective-comparison
python -m unittest discover -s "$D" -p 'test_*.py' -v
g++ -std=c++17 -O2 -g -Wall -Wextra -Werror \
  -fsanitize=address,undefined "$D/check_compare.cpp" -o /tmp/check-compare
/tmp/check-compare
python "$D/validate_solver.py" \
  --source /existing/original/fleet-candidate/main.cpp \
  --vendor /existing/fleet-candidate/vendor \
  --checker /existing/context/bin/checker \
  --output /tmp/new-objective-check --samples 9
```

The paired validator expects an original source without this shortcut; passing
an already-patched source is not a valid control. An original source containing
WREN's independent distance patch is supported and yields the distance-only
versus combined comparison. To compose onto another compatible source without
replacing that source or its other manifest entries:

```sh
python "$D/integrate_compare.py" /current/main.cpp --output /tmp/main.cpp \
  --manifest /current/PUBLIC-SOURCE-MANIFEST.json \
  --manifest-output /tmp/PUBLIC-SOURCE-MANIFEST.json
```

## Limits and retained evidence

The extra scan has **2–19% overhead** in some deeper/tied synthetic microbenchmarks.
Those raw samples are retained; a universally faster comparison is not claimed.
The initial workload generator allowed duplicate demand endpoints. Its earlier
predecessor/fleet timings remain separately labeled exploratory results. The
final generator enforces unique endpoints and its results above pass the official
checker. No earlier result is relabeled as checker-valid.

Full-process timing includes process startup and output, not compilation.
Environment: GCC 14.2, Linux, 4-CPU cgroup quota and 4 GiB memory; not the official
contest environment. A wall-clock-limited search may visit additional moves,
so unchanged fixed-round solutions do not establish unchanged equal-time results.

Complete sources, generated inputs, solution/statistics outputs, raw timings,
checker receipts, exploratory results and source/transport manifests are saved
in Library as `ROADEF-DELVE-objective-comparison-20260908.zip`. The package's
manifest binds each retained member. Its archive digest is in the delivery
receipt, outside the archive to avoid a self-referential hash.

SEDGE/FLORA and the fleet builder retain solver authorship; WREN retains distance
and QUARTZ/TRACE the existing checker/source transfer. Source is MIT-licensed;
preserve those notices. S139's draft, attachment and submission remain untouched.
