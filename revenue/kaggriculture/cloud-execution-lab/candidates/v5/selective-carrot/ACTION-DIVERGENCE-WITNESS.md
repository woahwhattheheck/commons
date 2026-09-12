# Production-v3 action divergence witness

This additive diagnostic closes the observability gap in `native-9901/` without
changing the shared evaluator or any gameplay package. The retained one-seed
Apex sample shows production-v3 and submitted V3.1 at identical candidate bank
through day 10, production-v3 at +2 through day 15, then -108 by day 16 and
-237 at terminal while its margin improves by +258. The unchanged evaluator
retained only a daily bank series plus an aggregate trace digest, so those
reports cannot identify the first causal action difference.

`action_divergence_witness.py` imports the exact evaluator supplied on the
command line, verifies its SHA256 plus the loader and both candidate archives,
and temporarily subclasses that evaluator's `Actor`. The subclass records the
same action response that the evaluator passes to the official interpreter;
there is no second policy call and no evaluator source edit. Two exact runs are
made for each requested seat. Candidate and opponent observation/action hashes
are compared step by step. The report retains four complete compact hash vectors
(left/right candidate and left/right opponent), binds each complete trace with
the historical trace digest, and publishes a bounded per-step hash/full-action
window around the first action divergence.

A candidate action is labeled the first observed divergence only when its action
changes before the opponent's and both candidate/opponent observation streams
are still identical at that step. This is intentionally stricter than simply
finding a different terminal trace hash.

`validate_native_9901_action_witness.py` is the fail-closed admission gate for
the exact retained Apex experiment. The recorder deliberately remains reusable,
but a native-9901 report is inadmissible until the validator proves that the
executed entry blobs, archives, evaluator, loader, engine members, seeds,
timeouts, seat topology, 719-step completion, and retained terminal scores all
match the immutable native-9901 authority. This closes the gap where an exact
archive could be named in the report while an unrelated extracted entry path
was actually executed.

Custody PASS and causal-positive are intentionally separate. The validator does
not trust the report's first-divergence primitives or causal summary. It requires
all four 719-row compact hash vectors, verifies exact contiguous topology and
SHA256 shape, reconstructs and verifies the recorder's aggregate trace digests,
recomputes candidate/opponent action and observation first-diff locations from
the vectors themselves, and only then derives `first_any_action_divergence_step`,
`all_actions_identical`, and the candidate-first predicate. Reported summaries
must agree with those independently derived values. An opponent-first witness
can therefore PASS exact experiment custody while remaining explicitly
causal-false; validator PASS alone never authorizes a repair.

The complete vectors are part of the admission proof, but they are not by
themselves a tamper-proof attestation because they and their digests live inside
the same JSON report. A coordinated editor could otherwise rewrite complete
vectors, recompute all trace digests and summaries, and refresh `report_sha256`.
For that reason validation also requires an **out-of-band frozen report
commitment**. The trusted repo-mounted executor must publish the recorder-emitted
`report_sha256` to the existing `#build-demand` thread immediately after the run
and before interpretation or editing. That published value is then supplied to
the validator with `--expected-report-sha256`.

The expected report SHA must come from that earlier external publication; it
must not be copied from the report being validated at validation time. This
boundary prevents post-publication report re-signing. It intentionally does not
claim to prove that a malicious trusted executor could not fabricate its own
run—the executor is the trust boundary.

Older summary-only witness reports are inadmissible and cannot be upgraded by
re-signing or by running only the newer validator: a fresh witness run with the
current recorder is required.

## Source contract

From this directory:

```bash
python -B -m py_compile \
  action_divergence_witness.py test_action_divergence_witness.py \
  validate_native_9901_action_witness.py test_validate_native_9901_action_witness.py
python -B -m unittest -v \
  test_action_divergence_witness.py test_validate_native_9901_action_witness.py
python -O -B -m unittest -v \
  test_action_divergence_witness.py test_validate_native_9901_action_witness.py
```

The recorder suite has 10 tests and the exact-target authority validator has 18.
Together they cover candidate-first, opponent-first, same-step observation
divergence, identical traces, bounded witness windows, complete compact vector
publication, topology rejection, seat parsing, SHA validation, executed-entry
drift, engine drift, terminal-score drift, duplicate seats, timeout drift,
report tampering, a claimed run with no actual action divergence, a missing
causal label, old summary-only evidence, vector/trace-digest tampering, a
re-signed forged causal summary, a re-signed inconsistent first-action summary,
a coordinated re-signed forgery of all four primitive divergence summaries
while the vectors remain opponent-first, a full-history forgery that rewrites
vectors plus all four digests plus every summary and self-hash while a frozen
external commitment remains unchanged, external-commitment mismatch, and the
Python bool/int trace-step alias.

## Exact native-9901 target

For the retained Apex world use seed `1209129901`, RNG `20260912`, both seats,
action/startup/game limits `1.25/10/900`, exact submitted V3.1 archive
`5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`, and
production-v3 archive
`20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`.
To reproduce the retained evaluator identity exactly, use the native-9901
runtime source identified by the report (`e8966a9afcd7fcd07a114ad178fb23c958f591ac`)
and require evaluator SHA256
`e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c`
and loader SHA256
`61093af280494f95d0f3e5137f716c980ebaf7a2bb53fb333b03566810808e6e`.

The executed adapter blobs are also fixed by the retained reports:

- V3.1 entry: `87df8bf2088b0650042350590d9486b6541b6ac2cd7ac1cb51fc1eaf43e8b7d0`
- production-v3 entry: `e40be452f16050f8ad1a67e0124b2df6983b93869b679d82860ca11c1bec34b3`
- Apex v7 entry: `e7b78d4b9e2fc7a68528e45f876a68b50d364103ebd5bf5f2dbbf68770bf54f5`

Example after unpacking/building the two exact candidate adapters and the exact
Apex adapter:

```bash
python -B action_divergence_witness.py \
  --evaluator "$OLD/revenue/kaggriculture/cloud-execution-lab/reference/evaluator/evaluate.py" \
  --expected-evaluator-sha256 e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c \
  --loader "$OLD/revenue/kaggriculture/20260907-offline-agent/evaluate.py" \
  --expected-loader-sha256 61093af280494f95d0f3e5137f716c980ebaf7a2bb53fb333b03566810808e6e \
  --engine-dir "$ENGINE" \
  --left-candidate "$RUN/v31-adapter.py::agent" \
  --right-candidate "$RUN/production-v3-adapter.py::agent" \
  --opponent "$RUN/opponents/apex_v7/adapter.py::agent" \
  --left-label submitted-v31 --right-label production-v3 --opponent-label apex_v7 \
  --left-archive "$ASSETS/titan-v3.1-56172377-5db3921f.tar.gz" \
  --left-archive-sha256 5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361 \
  --right-archive "$RUN/production-v3.tar.gz" \
  --right-archive-sha256 20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239 \
  --seed 1209129901 --rng-seed 20260912 --seats 0,1 \
  --action-timeout 1.25 --startup-timeout 10 --game-timeout 900 \
  --window-radius 2 --output "$RUN/action-divergence-witness.json"

# Immediately publish the recorder-emitted report_sha256 to the existing
# #build-demand thread before inspecting or modifying the report. Then use that
# earlier published value here, rather than deriving it from the report now.
python -B validate_native_9901_action_witness.py \
  "$RUN/action-divergence-witness.json" \
  --expected-report-sha256 "$PUBLISHED_REPORT_SHA256"
```

The validator requires the retained terminals exactly before returning PASS:
V3.1 seat 0 `[74143, 64333]`, production-v3 seat 0 `[73906, 63838]`, and the
same scores reversed for seat 1. It also requires 719 completed actions per arm,
four complete 719-row trace vectors whose reconstructed digests match the
recorder receipt, a matching external report commitment, and at least one real
action divergence in each seat. A PASS receipt sets
`external_report_commitment_verified=true`. A repair may be proposed only if
`causal_candidate_first_both_seats` is also true; otherwise the report is exact
custody/evidence but not a candidate-first causal witness.

This tool is evidence-only. A witness does not authorize a gameplay change,
CURRENT/release movement, or Kaggle submission. If both seats identify the same
candidate-first divergence and the retained terminal scores reproduce exactly,
use that bounded action/observation window to propose one minimal repair inside
the existing production-v3 family rather than spawning another policy tree.