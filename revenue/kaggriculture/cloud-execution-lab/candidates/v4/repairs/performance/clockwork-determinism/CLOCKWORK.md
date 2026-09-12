# CLOCKWORK — current-native contention determinism boundary

CLOCKWORK is an additive V4 runtime-integration package. It does **not** create a second controller, change gameplay policy, raise the one-second budget, disable deadline cancellation, or flip any default. It binds the current deadline seam, stages the already-landed WEAVE parity-preserving optimizer stack into a fresh runtime copy, and provides an action/state-level quiet-vs-loaded admission gate.

## Source-proved failure mode

The current `TitanAgent.act` intentionally uses a hard wall-clock deadline. That safety boundary must remain. The nondeterminism comes from *where* the deadline can fire:

1. `production.act(obs)` returns an authored parent action.
2. Runtime saves it as `selected_checkpoint` and immediately makes it the deadline `fallback`.
3. Runtime enters stage `selected_transform` and calls `FrozenSelected.transform(...)`.
4. `FrozenSelected.transform` performs deterministic but comparatively expensive seller simulation/optimization before returning the transformed action.
5. If the deadline fires during that transform, recovery returns the parent-selected fallback. If it does not fire, the transformed action is returned.

Therefore identical observation + process state can produce different returned actions solely because CPU contention changes whether the wall interrupt lands before or after the transform. Recovery is state-safe, but the cutover is semantically visible.

`CLOCKWORK-PINS.json` authenticates the exact current `main.py`, `titan_runtime.py`, `selected_sell_core.py`, WEAVE composer, and its four source transforms. `clockwork_source_audit.py` also requires the live deadline/cutpoint markers, so a moved seam fails closed rather than being silently certified.

## Remedy boundary

The first remedy is deliberately non-semantic: consume WEAVE's already-tested optimizer stack. WEAVE transforms the exact current `selected_sell_core.py` predecessor and has existing component/full-game action-state parity evidence while materially reducing optimizer latency. `stage_clockwork_runtime.py` materializes those exact bytes into a **fresh** runtime copy, authenticates the expected WEAVE postimage, and proves every runtime member except `selected_sell_core.py` is byte-identical. In particular `main.py` and `titan_runtime.py` — the hard deadline boundary — are unchanged.

This staging step is a candidate, not activation permission. Performance equivalence does not itself prove contention invariance on the composed current runtime.

## Admission gate

`clockwork_runtime_gate.py` consumes JSONL callback receipts from the same candidate under quiet and controlled-loaded execution. Required identity is explicit: candidate SHA256, runtime SHA256, engine SHA256, opponent id, seed, seat, and step. Each callback also supplies the exact returned-action SHA256, post-state SHA256, completion/fallback status, fallback stage, and optional wall/CPU telemetry.

Authoritative admission requires:

- identical coordinates and source identities;
- zero duplicate/missing cells;
- exact action hashes quiet vs loaded;
- exact post-state hashes quiet vs loaded;
- identical completion/fallback classifications and stages; and
- **zero deadline fallbacks in either arm**.

A diagnostic mode may compare symmetric fallbacks, but marks itself non-authoritative. Loaded-only `selected_transform` fallbacks are the exact causal witness CLOCKWORK is intended to eliminate.

This is complementary to QUIETBOX: QUIETBOX decides whether score evidence is trustworthy under contention; CLOCKWORK binds the runtime-level causal mechanism and refuses candidate activation before score analysis if actions/states/fallback paths themselves are load-sensitive.

## Commands

From the canonical `cloud-execution-lab` source root:

```bash
python candidates/v4/repairs/performance/clockwork-determinism/clockwork_source_audit.py \
  --source-root . --json /tmp/clockwork-source.json

python candidates/v4/repairs/performance/clockwork-determinism/stage_clockwork_runtime.py \
  --source-root . \
  --input-runtime /path/to/current-runtime \
  --output-runtime /tmp/current-runtime-clockwork \
  --json /tmp/clockwork-stage.json

python candidates/v4/repairs/performance/clockwork-determinism/clockwork_runtime_gate.py \
  --quiet /tmp/clockwork-quiet.jsonl \
  --loaded /tmp/clockwork-loaded.jsonl \
  --json /tmp/clockwork-gate.json
```

The runner that generates quiet/loaded callback rows remains owned by the existing current-native/gauntlet orchestration. CLOCKWORK does not fork it. Its only contract is the strict JSONL schema enforced by the gate.

## Non-claims

This package does not claim that WEAVE alone mathematically eliminates every timeout under arbitrary host starvation. It does not claim new gameplay strength, hosted Kaggle improvement, or promotion readiness. If current-runtime quiet/load receipts still show any fallback or action/state drift after the parity-preserving speed stack, the next CLOCKWORK step is to bound or deterministically admit the specific remaining transform — not to weaken the safety timer or hide the drift behind score averaging.
