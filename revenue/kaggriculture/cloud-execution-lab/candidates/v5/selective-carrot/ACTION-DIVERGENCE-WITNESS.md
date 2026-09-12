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
are compared step by step. The report publishes all per-step hashes but only a
bounded full-action window around the first action divergence.

A candidate action is labeled the first observed divergence only when its action
changes before the opponent's and both candidate/opponent observation streams
are still identical at that step. This is intentionally stricter than simply
finding a different terminal trace hash.

## Source contract

From this directory:

```bash
python -B -m py_compile action_divergence_witness.py test_action_divergence_witness.py
python -B -m unittest -v test_action_divergence_witness.py
python -O -B -m unittest -v test_action_divergence_witness.py
```

The authored source passes 9/9 tests in both normal and optimized mode. Tests
cover candidate-first, opponent-first, same-step observation divergence,
identical traces, bounded witness windows, topology rejection, seat parsing and
SHA validation.

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
```

This tool is evidence-only. A witness does not authorize a gameplay change,
CURRENT/release movement, or Kaggle submission. If both seats identify the same
candidate-first divergence and the retained terminal scores reproduce exactly,
use that bounded action/observation window to propose one minimal repair inside
the existing production-v3 family rather than spawning another policy tree.
