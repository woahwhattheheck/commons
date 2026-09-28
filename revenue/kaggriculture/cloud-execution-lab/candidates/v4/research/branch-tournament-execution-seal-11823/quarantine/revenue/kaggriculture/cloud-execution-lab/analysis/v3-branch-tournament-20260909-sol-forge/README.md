# TITAN V3 dependency-closed branch tournament

This lane turns branch comparison into an executable, fail-closed evidence
contract. It addresses a concrete weakness in the canonical offline evaluator:
for an arbitrary agent it fingerprints the entry file, but imported candidate
files can change independently. A report can therefore name the same
`main.py` digest while executing different dependency bytes.

The tournament runner closes that gap before any game starts.

## What it guarantees

For every candidate, the runner:

1. resolves the declared ref and requires it to equal a predeclared 40-hex
   commit;
2. creates a detached, no-checkout Git worktree and materializes only
   `revenue/kaggriculture/cloud-execution-lab` from that immutable commit;
3. reads `CURRENT-ARCHIVE.json` and `CURRENT-SOURCE.json` once with strict JSON
   parsing (duplicate keys and non-finite numbers are rejected);
4. verifies every source file named by the manifest, including byte length and
   SHA-256;
5. verifies the compressed archive receipt, rejects duplicate/traversing/link
   members, and manually extracts only regular files declared in the source
   manifest;
6. verifies every extracted member against the same runtime closure and binds
   the entrypoint to that closure;
7. runs every candidate sequentially through one exact evaluator, loader,
   official-engine cache, opponent set, world-seed set, RNG seed, timeout set,
   and both player seats;
8. rejects missing, duplicate, failed, malformed, or replay-mismatched cells
   rather than averaging surviving games;
9. pairs results by opponent and world seed, groups the two seats together, and
   computes mean/worst/variance, per-opponent deltas, and a deterministic paired
   bootstrap interval;
10. writes a hash-bound `TOURNAMENT.json`, human-readable `TOURNAMENT.md`, raw
    evaluator reports, and bounded stdout/stderr logs. `--verify-output`
    rechecks all those links after publication.

It does **not** merge a branch, alter runtime/config/archive pointers, submit to
Kaggle, weaken the evaluator, or treat a short smoke run as playing-strength
proof.

## Run contracts

Unit and adversarial tests use only the Python standard library and temporary
Git repositories:

```bash
cd revenue/kaggriculture/cloud-execution-lab/analysis/v3-branch-tournament-20260909-sol-forge
python -B -m unittest -v test_titan_branch_tournament.py
python -B -m py_compile tournament_contracts.py tournament_evidence.py titan_branch_tournament.py test_titan_branch_tournament.py
```

Prepare the exact official engine through the existing pinned evaluator/loader,
then run a manifest:

```bash
LAB=revenue/kaggriculture/cloud-execution-lab
LANE=$LAB/analysis/v3-branch-tournament-20260909-sol-forge
ENGINE=/tmp/titan-v3-engine

python -B "$LAB/reference/evaluator/evaluate.py" \
  --loader "$LAB/reference/evaluator/loader.py" \
  --prepare-engine "$ENGINE"

python -B "$LANE/titan_branch_tournament.py" \
  --repo . \
  --engine-dir "$ENGINE" \
  --manifest "$LANE/smoke-manifest.json" \
  --output-dir /tmp/titan-v3-branch-tournament

python -B "$LANE/titan_branch_tournament.py" \
  --verify-output /tmp/titan-v3-branch-tournament
```

The checked-in smoke manifest compares the same canonical TITAN closure across
two adjacent repository commits. Its expected disposition is `IDENTITY_ONLY`,
not `ADVANCE`; its purpose is to prove that unrelated repository changes do not
change the measured agent and that the official-engine execution path works.

## Manifest rules

`schema.json` documents the public shape. The runtime performs stricter semantic
checks than JSON Schema alone can express:

- Candidate and evaluator refs are only selectors; the declared commit is the
  authority. A moved ref is an error.
- Candidate archives must be backed by their exact `CURRENT-SOURCE.json` and
  `CURRENT-ARCHIVE.json`; an entry-file hash alone is insufficient.
- Repository opponents require an explicit file closure with exact hashes and
  byte counts. The official starter is bound to the engine commit instead.
- The baseline is exactly one candidate with `role: "baseline"`.
- A challenger advances only when all cells and replay checks pass, its closure
  differs from baseline, its mean paired delta clears `min_mean_delta`, the
  bootstrap lower bound is strictly above `min_ci_lower_delta`, and its worst
  opponent mean clears `min_worst_opponent_delta`.
- Mirrored seats are dependent. Bootstrap resampling therefore uses one value
  per opponent/world-seed pair: the mean of its two seat deltas.

A production manifest should use several fresh world seeds and strong,
dependency-closed opponents. The smoke manifest deliberately does neither and
must never be cited as a leaderboard estimate.

## Output layout

```text
MANIFEST.json
TOURNAMENT.json
TOURNAMENT.md
TOURNAMENT.sha256
candidate-reports/<candidate>.json
logs/<candidate>.stdout.txt
logs/<candidate>.stderr.txt
```

The runner refuses to overwrite an existing output directory. This prevents a
new attempt from silently replacing the evidence referenced by an earlier
receipt.

## Security and scope

The candidate archive is treated as trusted project code, exactly as in the
canonical evaluator. Process isolation is not a hostile-code sandbox. The
runner adds path, symlink, tar, digest, commit, and evidence controls; it does
not claim to contain malicious Python. Run untrusted candidates in a separate
container/VM with network disabled.

License: Apache-2.0. Attribution: TokenJunkieLabs / Bryce Muhlnickel; SOL-FORGE
implementation lane, 2026-09-09.

## Byte-exact source capsules

The three implementation modules use small loaders plus numbered
`.zlib.b64.*` source-capsule parts. Each loader requires the exact part set,
strictly Base64-decodes and decompresses it, checks the original source SHA-256,
and only then compiles the source. The conventional
`test_titan_branch_tournament.py` suite imports those loaders, so missing,
reordered, or altered parts fail before tournament work begins.

To inspect a capsule as ordinary Python without executing it, concatenate its
numbered parts, Base64-decode the result, and run `zlib.decompress`; compare the
result to `_EXPECTED_SHA256` in the loader. Everything uses the Python standard
library.
