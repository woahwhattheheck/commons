# Frozen three-kernel × statistics-output compatibility

This directory carries the already-landed fleet-candidate output-preservation change onto the **exact frozen three-kernel source** as an optional, source-bound composition. It does not edit the frozen calibration branch, rerun set A or set B, change solver parameters, or modify the S139 qualification archive, draft, or submission state.

## What composes

The input is the source produced by applying `cloud-kernel-composition/combined.patch` (Git blob `0ff8d2ee7c4df1022c50484a89e7424329cce0ec`) with zero fuzz to the original fleet candidate at commit `2885d176373c33410148829fef93c310c3752c0b`:

- original source: 34,254 bytes, SHA-256 `322ec2e6bec9ab17c4cdf74c52d8e40414ce90cf60f9e53aaee2531cce652ab1`
- frozen three-kernel source: 37,251 bytes, SHA-256 `758977095f8f34263bbcd9ed043ac4ab7943f04f65fae530c78ee64787c34f8f`

`frozen-three-kernel-statistics.patch` is a 3,406-byte, SHA-256 `232ff8744ef8cc5179165906ad4894053c5fe0482d9f61e660539d8b8e180d92` diff from that frozen source to the composed source. It adds only:

1. pre-work validation that problem inputs, solution output, statistics output, and their staging paths do not alias;
2. checked same-directory statistics staging and replacement; and
3. the validation call at the program entrypoint.

The result is 39,435 bytes, SHA-256 `79f07a25ecd745d25a6e0a03030e709ec8f3ec54cdebe1d250baaf5ac07a802a`.

The behavior was first landed for the current fleet candidate in [PR #10397](https://github.com/woahwhattheheck/commons/pull/10397), merge `e1f7a7ec6fec94c27738beee97c7b35d5a46fc3a`. This directory does not replace that main source or the frozen source; it supplies an exact optional composition after calibration.

## Apply without modifying the input

```sh
python3 compose_statistics.py \
  --source /path/to/frozen-75897709/main.cpp \
  --output /fresh/path/main.cpp \
  --report /fresh/path/composition.json
```

The applier rejects a wrong source, wrong patch, existing output, source/output alias, or patch/output alias. It invokes `patch --fuzz=0`, checks the exact output identity, fsyncs a sibling temporary file, and atomically replaces only the requested new output. The input source remains unchanged.

## Reproduce the validation

The full validator consumes existing local source/checker dependencies rather than downloading or rebuilding a submission package:

```sh
python3 validate_composition.py \
  --frozen-source /path/to/frozen-75897709/main.cpp \
  --rapidjson-vendor /path/to/vendor-containing-rapidjson \
  --regression-script /path/to/statistics-output-checks/test_statistics_output.py \
  --fixtures /path/to/fleet-candidate-fixtures \
  --checker-binary /path/to/official-checker \
  --joint-verifier /path/to/verify_joint.py \
  --output /fresh/path/validation.json
```

`VALIDATION.json` is the exact output from that command in the retained QUARTZ native context. It records:

- GCC 14.2 and Clang 17 compilation;
- 24/24 output-preservation methods passing with each compiler;
- the exact frozen source producing 25 failure records across 18 methods and zero execution errors with each compiler;
- identical source hashes for ten algorithm bodies: `dag`, `segment`, `routeFlow`, `distance`, `quantizedImproves`, `moveTogether`, `waypointCandidates`, `eject`, `run`, and the constructor;
- official Orange checker acceptance for the existing `joint` and `joint-budget` discriminators; and
- byte-identical disabled, enabled, and repeat solution files before and after composition, including unchanged rank-1/rank-3 improvements, costs, repeatability, and same-path resume behavior.

The two joint cases are manufactured discriminators, not public-instance scores. No set-A/set-B solver run, benchmark selection, qualification upload, organizer contact, or Gmail action was performed for this compatibility result.

## Consumer boundary

Use this composition only after selecting the exact frozen source it names. A later solver source needs a separately measured composition or the already-landed main implementation. The patch is not a solver-strength mechanism: it preserves solution/statistics ownership and failure reporting while leaving the optimization algorithms and parameters intact.

Coordination: [ROADEF S139 work thread](https://tokenjunkielabs.slack.com/archives/C0BUY3EKMSB/p1788851484014469?thread_ts=1788750090.535979&cid=C0BUY3EKMSB).
