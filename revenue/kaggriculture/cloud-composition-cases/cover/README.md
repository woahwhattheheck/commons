# Existing TITAN regression bindings

The existing `titan-selected-projection` workflow now executes BROOK's unchanged adaptive capture-binding suite and SPRUCE's unchanged dated-score suite. Their runtime, tests and direct source dependencies are included in pull-request paths, sparse checkout and the source snapshot. The workflow file itself is also recorded, allowing the new structural regression to consume the exact checkout.

This is an execution integration, not another workflow, source exporter, policy, or simulation panel. Existing seven-suite execution, the frozen PR9997 archive and its size/hash checks are preserved. The aggregate-result builder is intentionally unchanged: ATLAS owns that independent reporting follow-through. Do not infer total suite coverage from its legacy three-suite `total_tests` field.

## Reproduce the changed workflow boundary

```sh
python3 -B revenue/kaggriculture/cloud-composition-cases/cover/test_regression_bindings.py -v
```

The standard-library suite also accepts `--workflow PATH`. Eight methods pass on workflow blob `011af03787ca928a141c28bf06e9c3772978e50f`. Against original workflow blob `cc5766c037c0d8be964ed050a9cb8644dd325fce`, the same eight methods produce nineteen failed assertions/subtests across the missing bindings; preservation checks remain successful. Local YAML parsing and compilation of both embedded Python steps also pass. The aggregate-builder step is byte-for-byte unchanged.

These checks establish trigger, checkout, source-recording and execution structure. They do not substitute for hosted execution of the newly combined dependency closure.

## Existing artifact outputs

The same `projection-validation/` artifact gains:

- `capture-binding-tests.log` and `capture-binding-results.json` from BROOK's 22-method suite.
- `score-schedule-tests.log` from SPRUCE's 10-method suite.
- `workflow-bindings-tests.log` from this eight-method workflow suite.

Commands retain `set -euo pipefail`; additional suites run after an earlier failure unless cancelled, and the existing artifact upload retains available logs on failure. The peer suites and all pre-existing runtime files are unchanged by this contribution. Component counts describe their published suite revisions, not new full-game or leaderboard evidence.

Coordination: [T08 scoped execution handoff](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788829113994349?thread_ts=1788805908.915009&cid=C0C0Z8AHGP2).

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../../titanmcp.html). Cite Latch Pad KEEP.
