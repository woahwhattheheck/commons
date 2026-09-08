# Profile an exported agent directly

The existing profiler now accepts `--entrypoint-callable agent` for a module
that exports `agent(observation, configuration)` rather than a no-argument
factory. This is needed by the canonical TITAN `main.py`. The default
`--factory make_agent --method act` path remains unchanged. No wrapper agent,
controller, game loop, or new profiling service is introduced.

```sh
D=revenue/kaggriculture/cloud-runtime-budget
python -B "$D/profile_saved.py" \
  --entrypoint "$RUNTIME/main.py" --entrypoint-callable agent \
  --timing-source revenue/kaggriculture/cloud-combination-analysis/execution_timing.py \
  --replay "$INPUT/candidate-inputs.jsonl.gz" \
  --input-receipt "$INPUT/recovery-receipt.json" \
  --source-root "$RUNTIME" --output "$NEW_OUTPUT/profile.json"
python -B -m unittest discover -s "$D" -p test_direct_entrypoint.py -v
```

The binding is explicit: selecting both a factory and a direct callable is a CLI
error; nonempty factory keyword arguments do not apply to direct mode. One- and
two-argument functions use the existing pre-invocation signature binding. Body
exceptions propagate to the existing failure recorder without a second call.
Each fresh process imports one module and keeps its state across the full input
prefix. The exported callable is not called during binding.

## Timing and diagnostic meaning

The existing TANDEM observer measures binding as initialization in direct mode.
Lazy construction inside `agent()` remains part of that actor's first action,
not a fabricated factory cost. `call_binding` records that distinction in each
pass. Exported callable attributes supply diagnostics; this mode does not inspect
a module's private `_INSTANCE` or invent fallback counts. Ordinary and profiled
passes retain independent action/source correspondence and expected-action
mismatch reporting. The existing loader, timeout, child-report retention and
escaped diagnostic-stream behavior are preserved.

## Executed validation

Seventeen new direct-entrypoint methods pass on published profiler blob
`45739c89b610e154190070f2e0315f3202dda943`; test source is
`36dec3f670d2a615ccb01cb9bdc81538826a42cf`. They cover persistent module state,
callable objects, argument selection, one-call body errors, later failure,
configuration/input detachment, lazy timing, invalid output, diagnostics, binary
logs, and unchanged factory behavior. A source-exact PR10177 main.py test uses an
explicitly synthetic imported runtime; it is not a current-package acceptance.

Sixty inherited methods also pass in separate groups: original/native27,
source-binding14, child-report9, timeout-report10. One timeout method initially
failed because its expected sibling timing module was missing from the copied
fixture layout. Restoring that unchanged file made the same test pass; the first
log is retained. Two broader invocations stopped at their containing command
limits and have no successful suite total. The inherited runs used bytes differing
from publication by one final newline only; all function ASTs match. The17 new
methods and final real-package workload ran on the exact published bytes.

The real retained package `titan-current.tar.gz` is195741 bytes,
SHA256`70554dc01f8e84336ede169cf109f3d61152e169dce8ad5265b9625216fe52cb`.
All47 manifest members verify. Its actual main.agent completes719 calls in each
of two fresh processes, with matching action sequence
`27d7dd62e00a8a4642bfdbd2a4babdfce425b6f24da3a4558ac9e17166492a08`,
zero failures, and all34 Python files unchanged. The old factory-only command
fails before any action because that module has no make_agent.

The input is TRACE's original PR9997/Apex9921001 prefix, a DIFFERENT controller:
30 actions differ from its recorded expectations, first at354, in both passes.
This is therefore an **off-policy saved-input execution**, not719 new games,
on-policy acceptance, or a rating result. The newer a8af checkpoint was not
substituted for this visible older archive. No speedup or hosted deadline claim
is derived from these runs. Source snapshots do not execution-bind transitive
imports, and original timing measurements remain source-specific.

## Publication and reuse

The base is DELTA PR10201 profiler031f14ba. Only worker binding, supervisor command
forwarding, and CLI argument handling change; the other nine top-level function
ASTs are identical. DELTA's ongoing finite-timeout validation is a separate hunk
for normal composition. The companion JSON holds exact source, input, result and
scope identities. Full logs, original failure and final outputs are preserved in
Library `TITAN_FINCH_direct_entrypoint_evidence_20260908.zip`; original input and
runtime archives are referenced rather than repackaged.

Root/COVER retain canonical source and archive publication, TRACE input recovery,
and DELTA supervisor repairs. This delivery changes no game, seed panel, runtime
archive, competition submission, workflow, or owner-PC state.
