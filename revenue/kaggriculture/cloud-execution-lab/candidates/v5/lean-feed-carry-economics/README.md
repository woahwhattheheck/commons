# TITAN V5 lean-feed carry economics

Additive research/evaluation tooling for issue #14337. The package is default inert and does not alter a runtime policy, release pointer, archive, competition submission, or provider state.

It provides three comparison arms (`MIN_PROVABLE`, `CURRENT_POLICY`, and `PLUS_ONE`), validates complete paired evidence across both seats and multiple opponent regimes, records decision-window telemetry, and emits deterministic JSON, JSONL, CSV, Markdown, and manifest artifacts.

Candidate economics and promotion authority are intentionally separate. The base evaluator can report that a normalized document supports a research candidate, while the official CLI routes through `lean_feed_hardening.py` and refuses final promotion unless the evidence binds to an independently reviewed root retained in code. The trusted-root set is intentionally empty while the D2 source contract remains blocked.

The included examples are synthetic contract fixtures. They exercise the evidence and hardening contracts only; they are not official-engine results and cannot authorize promotion.

Pinned D2 archive identity: `3d250d7bd32bf51f26ec1f69c2c10bc3c914e7d0cf64a078ae5bac5832465bd8`.

## Local commands

```bash
python -m py_compile feed_carry_oracle.py lean_feed_hardening.py test_feed_carry_oracle.py test_promotion_gate_hardening.py test_cli_smoke.py examples/generate_synthetic_contracts.py
python -m unittest -v test_feed_carry_oracle.py test_promotion_gate_hardening.py test_cli_smoke.py
python examples/generate_synthetic_contracts.py
python feed_carry_oracle.py examples/synthetic_positive_contract.json --out /tmp/lean-feed-positive
python feed_carry_oracle.py examples/synthetic_no_redeployment.json --out /tmp/lean-feed-negative
```

Expected fixture conclusions through the official CLI:

- positive contract: candidate economics `PROMOTE_RESEARCH_CANDIDATE`, final conclusion `NO_PROMOTION`, `authority_verified=false`
- no-redeployment contract: candidate economics `NO_PROMOTION`, final conclusion `NO_PROMOTION`

Official promotion remains blocked until exact D2 source bytes and normalized evidence are authenticated, independently reviewed, and their authority root is explicitly retained by code review.
