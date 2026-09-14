# TITAN V5 lean-feed carry economics

Additive research/evaluation tooling for issue #14337. The package is default inert and does not alter a runtime policy, release pointer, archive, competition submission, or provider state.

It provides three comparison arms (`MIN_PROVABLE`, `CURRENT_POLICY`, and `PLUS_ONE`), validates complete paired evidence across both seats and multiple opponent regimes, records decision-window telemetry, and emits deterministic JSON, JSONL, CSV, Markdown, and manifest artifacts.

The included examples are synthetic contract fixtures. They demonstrate the positive promotion contract and the no-redeployment falsifier, but they are not official-engine results.

Pinned D2 archive identity: `3d250d7bd32bf51f26ec1f69c2c10bc3c914e7d0cf64a078ae5bac5832465bd8`.

## Local commands

```bash
python -m py_compile feed_carry_oracle.py test_feed_carry_oracle.py
python -m unittest -v test_feed_carry_oracle.py
python feed_carry_oracle.py examples/synthetic_positive_contract.json --out /tmp/lean-feed-positive
python feed_carry_oracle.py examples/synthetic_no_redeployment.json --out /tmp/lean-feed-negative
```

Expected fixture conclusions:

- positive contract: `PROMOTE_RESEARCH_CANDIDATE`
- no-redeployment contract: `NO_PROMOTION`

Official promotion remains blocked until a normalized evidence document is produced from the pinned D2 archive, engine, and harness.
