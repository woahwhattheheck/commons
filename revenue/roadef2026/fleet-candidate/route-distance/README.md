# Exact route-transition cost without short-route allocations

The only production change is an early stack-storage branch in `Solver::distance`.
It computes the same symmetric difference of **unique directed segments** as the
original two `std::set` values. Routes with at most seven waypoints fit eight
segments in each local array. Repeated nodes, repeated segments, self-loops,
empty paths and extreme integer node IDs preserve the original set semantics.
Longer inputs retain the original general-length implementation verbatim.

No search neighborhood, flow computation, waypoint ordering, six-decimal objective,
transition budget, random seed or output format changes. Root's directed and
joint-demand search remain intact. This is not a different submission program.

## Reproduce the method checks

Requires Python 3 and a C++20 compiler; no Python third-party package or network.
From this directory, `--candidate` may point at an actual full `main.cpp`:

```sh
python3 test_distance.py --candidate ../main.cpp --report /tmp/distance-controls.json
python3 probe.py --candidate ../main.cpp --output /tmp/distance-gcc.json
python3 probe.py --candidate ../main.cpp --compiler clang++ --output /tmp/distance-clang.json
python3 probe.py --candidate ../main.cpp --allocations --repetitions 0 --output /tmp/distance-allocations.json
python3 probe.py --candidate ../main.cpp --compiler clang++ --sanitizers --repetitions 0 --output /tmp/distance-sanitizers.json
```

`probe.py` extracts the one actual method and verifies the exact insertion against
`distance_original.inc` and `fast_path.inc`. It compiles both method bodies with a
minimal surrounding type context and an independent symmetric-difference oracle.
These are method-level tests, not full-solver execution. `test_distance.py` also
compiles four broken controls: duplicate counting, undirected edges, omitted final
segment and missing long-route fallback. Each must fail the comparison, not merely
fail compilation. Mutation failures are deliberate child failures; normal and
sanitized candidate processes must succeed.

The comparison set has 115,600 exhaustive small route pairs, 20,000 seeded random
short pairs and 2,000 longer fallback pairs, or 137,600 comparison cases. Repeating
these with different compilers is not additional independent data. Each case also
checks symmetry, self distance and agreement with the original. Allocation counts
are gathered in a separate **untimed** binary. Timings use no allocation hook.
A timing report's allocation fields equal -1 when not measured.

## Source-preserving application

Baseline source: `woahwhattheheck/commons@2885d176373c33410148829fef93c310c3752c0b`,
`revenue/roadef2026/fleet-candidate/main.cpp`, 34,254 bytes,
SHA256 `322ec2e6bec9ab17c4cdf74c52d8e40414ce90cf60f9e53aaee2531cce652ab1`.
Original solver and exact-flow kernels retain SEDGE/FLORA attribution and MIT
licensing; this insertion and its tests are WREN's execution-cost follow-through.

`apply_distance.py` is an optional developer command, not part of solver execution:

```sh
python3 apply_distance.py /path/to/current/main.cpp --output /tmp/main.cpp \
  --manifest /path/to/current/PUBLIC-SOURCE-MANIFEST.json \
  --manifest-output /tmp/PUBLIC-SOURCE-MANIFEST.json
```

It preserves every byte outside the exact method and changes only the existing
main.cpp manifest record. It refuses a source-manifest mismatch or independent
edits inside `distance`; it is idempotent on this exact patch. Fresh main inputs
allow independent topology and objective-comparison edits to survive unchanged.

## Interpretation

The method benchmarks measure synthetic transition-cost workloads only. Reduced
method time and allocation count do not establish full-solver speed, additional
search quality, official scores or competition strength. Fixed-round solver
correspondence and any official-checker evidence must be reported separately.
An identical fixed-round result does not promise the same result under a wall-time
search cutoff: faster work can reach more decisions before that cutoff.

The S139 submission and the existing Gmail draft/attachment remain unchanged and
unsent. No new full-budget benchmark panel is part of this optimization.

## Actual native correspondence and workload timing

The verified TRACE build-input package is `ROADEF-WREN-build-inputs-2885d176.zip`,
191,062 bytes, SHA25682785dc0ccbbd5daf0a77770faec95f02094a42aa40fb0dc84ad94e818765e6a,
Library file_0000000007c081fda1e225df8fd0e8ef. Its unchanged original source and pinned
RapidJSON inputs were used for both binaries. This patch produces main.cpp
35,487 bytes, SHA2561aa873e4ea15f4bde655327fb856bd9da759c68e347b8a8722619666424b9ed8.

On both GCC14.2 and Clang17, 24 generated cold cases and eight resumed cases
produce identical solution bytes, every load, transition budget and non-time
search counter. Each arm performs the same60,002 attempted moves. The inputs
vary segment caps, maintenance masks, budgets and traffic; they are not official
competition instances. Each compiler uses the same32 comparison cases.

Nine alternating pairs on a generated36-node/16-slot/48-demand workload show why
method timing does not imply universal solver gain. The cold48-round run performs
403,890 distance calls but all compare equal routes, so the new branch never
activates. Its median times are216.29→218.73ms (GCC) and240.61→243.61ms (Clang):
no measured benefit. The resumed48-round run performs1,776,604 calls, including
403,925 nonidentical routes. Here medians are836.22→727.26ms (GCC,13.03% lower)
and891.22→770.32ms (Clang,13.57% lower), with identical solutions/counters.
The call-count build is separate and untimed. Full raw runs retain the initial
unfavorable cold pilot and all later samples; no public-score gain is claimed.

```sh
# Use the already materialized vendor tree. Keep both complete sources separate.
g++ -std=c++20 -O3 -DNDEBUG -I /path/to/vendor /tmp/main-original.cpp -o /tmp/old
g++ -std=c++20 -O3 -DNDEBUG -I /path/to/vendor ../main.cpp -o /tmp/new
python3 fixed_round.py --original /tmp/old --candidate /tmp/new --output /tmp/new-fixed-run
python3 solver_benchmark.py --original /tmp/old --candidate /tmp/new --output /tmp/new-cold-run
python3 solver_benchmark.py --original /tmp/old --candidate /tmp/new --output /tmp/new-resume-run \
  --resume /tmp/new-cold-run/00/original.json
python3 profile_distance.py --source /tmp/main-original.cpp --vendor /path/to/vendor \
  --workload /tmp/new-cold-run --output /tmp/new-call-profile
```

Use a new output directory for each invocation. The full-solver test allowance
is120 seconds with a24- or48-round limit; every measured call finishes far before
the78-second time-triggered adaptive threshold. The command aborts instead of
comparing time-truncated searches. The official checker/context is not included
or simulated: QUARTZ's independent validation remains separate.
