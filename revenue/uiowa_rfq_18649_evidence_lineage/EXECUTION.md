# UIOWA-033 recovery execution record

Builder and executor: ZZ-KESTREL-X6J4, GPT-6 Astra Pro. Original comparator, demo and 36 tests: ZZ-ORBIT-47. Execution took place in an ephemeral cloud container with Python 3.13.5 and the standard library; no live institution records, external requests, paid runner, owner-PC execution or GitHub Actions success are asserted.

## Exact exercised source

The native GitHub reads of immutable commit `507a490240cd8ccaad2a9503ec78911159c8f62b` match these Git blob identities. The complete record also includes SHA-256 and byte length per source file.

| Source | Git blob |
| --- | --- |
| lineage.py | ab271d4d160c49a8c1b9787e58039aa0ad8f13c6 |
| demo.py, unchanged | ff4f14370df5fc4a737d96887df1e23612dd694f |
| test_lineage.py, unchanged | 1ed79f7d9d1a4417fe40b69a5fea68ba89bfa7d9 |
| walkthrough.py | eaa597e63bd3daa21889095a1546b5cd80c12fc0 |
| test_lineage_recovery.py | 7349f13a2be0fd4b453d1607053f887c6e0af232 |
| root test_uiowa_evidence_lineage_recovery.py | 073812e997b740108429c91679bd6aef42ebaa33 |

## Executed results

The fresh normal run executed 61 methods in 7.257 seconds; optimized execution ran the same 61 in 7.108 seconds. Both passed with zero skips. Full command wall times, including interpreter startup and capture, were 8.148 and 8.005 seconds respectively. The source-isolation check ran all 61 methods with warnings treated as errors in 7.101 seconds, with 7.890 seconds total captured wall time, and restored five pre-existing module objects plus `sys.path` after loading and running the suite.

The tests comprise 36 unchanged original methods and 25 added methods. The independent oracle covers 4,096 DAG/export/citation combinations within one method. The long-chain method covers 1,200 records. Repeated execution modes are not additional unique tests.

Three retained missing-terminal regressions fail on original runtime blob `30125c5e4cbc6ad8d59a5281fe023ecf3f82d6cc` and pass on the repaired source: retained-original, retained-intermediate and one-omitted-branch cases. Literal failure text and the earlier original 36/36 normal and optimized logs are retained, not rewritten into a green baseline.

The real original and repaired demo commands produced byte-identical JSON and Markdown. JSON SHA-256: `6701086e87b116ac23c0f063bae3151f362cd3f99c85c0f41df7577c9d6ee25b`. Markdown matches the original checked-in `EXAMPLE_REVIEW.md` blob `4318b167ebfbbfdcf53f9830858f99c038a44b22`.

The seven-case generator created 68 files. Every file matched between normal and optimized execution. Reusing the destination returned exit 2, emitted no successful receipt, and preserved the full previous file inventory and hashes. Each case includes real fictional source text and both manifests, rather than only manually written expected outcomes.

## Retained literal records

[EXECUTION.json.xz](EXECUTION.json.xz) is an XZ-compressed JSON record, not executable code. It retains the Python version, exact six-source inventory, complete commands and arguments, working-directory roles, return codes, wall times, full standard output/error, 68 output hashes, original-demo equality and the five earlier literal logs including the red baseline.

Compressed bytes: 6,668. SHA-256: `95f51124716013506febc87a5d86fe412b7380b4d9856def65c6f3f67fcb2ffa`.

Decoded JSON bytes: 75,742. SHA-256: `707b6951c8a6b811d7c6663250f57f1a8ec74e175e0694a4c9e91ac1f70b71fc`.

Read the record without replacing a file:

```sh
python -c 'import json,lzma,pathlib; p=pathlib.Path("EXECUTION.json.xz"); r=json.loads(lzma.decompress(p.read_bytes())); print(json.dumps(r,indent=2))'
```

The primary replay commands are in [RECOVERY.md](RECOVERY.md). The record's absolute paths identify this isolated execution environment; they are not paths on Bryce's computer or assumptions about another checkout. The source-isolation command is retained in full in the record and can be run from repository root.

## Integration is a separate claim

Native first-head provider reads returned five queued workflows: source-parses run 35453675640, tests run 35453675697, muhlnickel-spec-guard run 35453675725, open-door-guard run 35453675727 and path-manifest run 35453675741. None is recorded as successful execution. The repository's current review/execution contract remains applicable; this local evidence does not manufacture a provider job, reducer READY, or main merge. Later provider and integration changes belong in the PR's exact-head receipts, not a retrospective rewrite of these observations.
