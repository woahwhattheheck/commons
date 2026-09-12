# V3.1 ↔ V4 whole-entrypoint deadline ablation

This directory isolates one submitted-V4-only execution boundary for causal measurement. It is **evidence infrastructure**, not a proposal to remove deadline containment from production TITAN.

## Question

Submitted V3.1 and V4 differ in several downstream layers even though their active Arlene producer bytes are identical. One independent delta is the whole-entrypoint deadline boundary in `main.py`:

- submitted V3.1 source `a90d888f03987ef0b35cfd20ec3519c6144db08a`, `main.py` Git blob `b9db6c3ec9c64cb52ade0c26b23edf22710d77c9`, directly calls `TitanAgent.act(...)`;
- submitted V4 source `4af1113154e78c662780e6658cd920daac7902e3`, `main.py` Git blob `a015fef88d855d6d9c50f9d36e2551abd8829996`, wraps construction/runtime/finalization in the outer deadline/fallback boundary;
- parent `784194262d1f448e5012c16503e8c2811e551c97`, `main.py` Git blob `06d7d7d3508403ce5e0eb53e673dede74055eae3`, already has `FinalPressureAgent` but still directly calls `.act()`;
- commit `4be7772ab850e50f42d0eb0fe715fecadb19ee10` explicitly introduces the whole-entrypoint containment on top of that parent.

That history lets us ask whether the outer containment changes scored behavior without conflating it with FinalPressureAgent.

## Treatment

`entrypoint_deadline_ablation.py` accepts only the exact submitted-V4 `main.py`. It preserves every byte before the outer guard starts, including V4 instance construction policy, `FinalPressureAgent`, configuration loading, town-procurement observation, producer/seller/runtime imports and step normalization. It replaces only the executed outer-containment suffix with direct instance construction (when required) followed by `instance.act(...)`.

The removed suffix intentionally includes the single whole-entrypoint containment feature as implemented by V4: outer budget validation, prior-selected clearing for immediate cancellation safety, fallback preparation, prelude exhaustion handling, `_DeadlineTimer`, interruption/finalization fallback and post-interruption instance invalidation. The helper definitions remain in the treatment as dead bytes; they are not called. This makes the execution delta explicit while minimizing unrelated textual churn.

The materializer fail-closes on exact Git blob identities, unique splice anchors and output overwrite. Its receipt binds the input/output blobs and hashes of the preserved prefix, removed guard and replacement direct-call tail. It never changes the repository runtime, `TITAN-CONFIG.json`, current archive pointer, release transaction or Kaggle submission.

## Evidence bar

Source correctness is necessary but not evidence of a better policy. After exact-head CI is green, a mounted runner may materialize the treatment and test it with the same authenticated official engine, opponent, seed and seat as exact V4/V3.1 controls.

First establish **natural engagement**: at least one returned action, fallback/diagnostic boundary, or terminal score must differ because of the outer containment. If treatment is byte-behavior identical under native timing, record the lane as cold and stop. If it engages, compare treatment vs exact V4 and exact V3.1 on the same cells and inspect action divergence before proposing any physically correct V5 repair. A raw rollback is diagnostic only and is never itself release-authorizing.

The one-V5 rule remains: any useful causal finding must be repaired or composed into the single V5 candidate and must pass the existing champion/economics release authority. No second runtime tree is created here.
