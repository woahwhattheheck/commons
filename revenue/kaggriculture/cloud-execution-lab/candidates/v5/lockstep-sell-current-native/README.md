# V5 lockstep_sell current-native intake

This directory is the fail-closed convergence boundary for the Whitepill `lockstep_sell` handoff after the reviewed native ReturnBridge composer was rebound to V5 by #13288.

It does **not** recreate Whitepill policy from a Slack description, enable `lockstep_join`, change root TITAN config/defaults, replace the current archive, or submit anything to Kaggle. The only accepted donor is the exact already-evaluated artifact whose coordination witness is SHA-256 `6355999beb5c3f3948bbce9dcbd69380b773b5ebf084226c39f41a07db4bd20e`.

## Why this exists

The composition handoff reported a strong paired result (`n=128`, mean delta `+69.22`) and named the exact agent digest, but only exposed `/workspace/v5-flip-lockstep-sell-apex/COMPOSITION-READY.json` by path. A different VM cannot authenticate or reproduce that workspace-local path. The prior composition handoff therefore remains incomplete until the exact card and evaluated agent bytes are published or attached.

`intake_lockstep_sell.py` turns those exact bytes into a deterministic evidence receipt. It requires all three inputs to agree:

- the card must be strict UTF-8 JSON with a top-level `agent_sha256` equal to the declared Whitepill witness; duplicate object keys and JSON `NaN`/`Infinity` are rejected at any nesting depth;
- the evaluated agent file itself must hash to that same SHA-256, so prose or a lookalike source file cannot substitute for the measured artifact;
- the ReturnBridge composer must have Git blob `7b10ad42dea18827d061046b79cc72ab209bf3f9`, the reviewed V5-rebound composer landed by #13288. Composer drift fails closed rather than silently changing the integration contract.

A successful receipt is explicitly marked `AUTHENTICATED_EVIDENCE_ONLY` and `DEFAULT_OFF_NO_ROOT_MUTATION`. It is an intake gate, not a promotion decision.

## Use after the donor is published

From `cloud-execution-lab`:

```bash
python -B candidates/v5/lockstep-sell-current-native/intake_lockstep_sell.py \
  --card /path/to/COMPOSITION-READY.json \
  --agent /path/to/exact-evaluated-agent.py \
  --composer candidates/v4/repairs/gameplay/lockstep-join/compose_native_return_bridge.py \
  --output /path/to/LOCKSTEP-SELL-INTAKE.json
```

The output path is write-once; the tool refuses to overwrite an existing receipt.

## Focused controls

The focused test exercises deterministic successful receipt creation plus predecessor-killing failures for duplicate JSON witnesses, non-finite JSON, wrong card identity, mutated agent bytes, composer drift, and empty artifacts. Run both normal and optimized Python so no correctness boundary depends on assertions:

```bash
python -B -m unittest -v candidates/v5/lockstep-sell-current-native/test_intake_lockstep_sell.py
python -O -B -m unittest -v candidates/v5/lockstep-sell-current-native/test_intake_lockstep_sell.py
```

The exact donor card/agent are intentionally **not** reconstructed or checked in by this carrier. Once their owner publishes the original bytes, this gate can authenticate them before any current-V5 materialization or known-loss/gauntlet evaluation consumes them.
