# Historical battery result — evidence-level reconciliation

Analyst: ZZ-KESTREL-EXEC-31 / GPT-6 Astra Pro. Read and computed on 2026-09-19. The recorded execution occurred on **2026-09-17**, not during this review.

## Exact retained source

GitHub Actions run [35269752571](https://github.com/woahwhattheheck/commons/actions/runs/35269752571), attempt 1, workflow `tests`, job `battery` (job ID 105365790530). Downloaded artifact ID **10524332401**, named `battery-results-35269752571-1`, from the authenticated GitHub artifact endpoint. The downloaded ZIP's SHA-256 matched the provider-declared digest:

```text
4fd9b78db026a305ee0bb4978a4f032487e7d8df6fba02b29ccf68f6e10924cb
```

The ZIP contains one member, `commons-battery-report.json`, 1,045,863 uncompressed bytes. Its SHA-256 is:

```text
9e6471faa5ecb908d4578e43538d61ad4dafe0566f1fa36821f0042583a2a187
```

The archive was read in place; no archive paths were extracted or executed. These are retained provider records, not a rerun or proof of current repository state.

## Recorded identity and totals

The JSON identifies schema `commons-battery-report-v1`, repository `woahwhattheheck/commons`, event `pull_request`, workflow outcome `failure`, complete `true`, and conclusion `FAILED`. Its workflow ref is `woahwhattheheck/commons/.github/workflows/tests.yml@refs/pull/15631/merge`.

All three recorded identities agree:

```text
workflow_sha = 249f047855afc5aa2af1634b39a0cb5d58ac2ce2
event_sha    = 249f047855afc5aa2af1634b39a0cb5d58ac2ce2
checkout_sha = 249f047855afc5aa2af1634b39a0cb5d58ac2ce2
```

This is the historical synthetic merge of donor `db0e8838d61cd6133154bf2008aefb5b94fc5acd` into historical base `d1da58441f5cbbc067fbe77abc23d923532f1049`, not either September 19 replacement head.

The 3,381 result rows were parsed and reconciled against the declared counts:

| Recorded outcome | Files |
|---|---:|
| Completed | 3381 |
| Exit 0 | 3081 |
| Nonzero exit | 300 |
| Unresolved source files | 0 |

Every nonzero row reports exit code **1**. All **300 failing paths are repository-root files**, not files beneath `competitions/arc-agi-3-2026/`. The `problems` array is empty; that is a statement about this artifact's metadata validation, not about the failing tests.

## Important coverage distinction

**This artifact enumerates zero result paths under `competitions/arc-agi-3-2026/` — passing or failing.** It must not be used to claim that the ARC tests passed inside the monolithic battery. The retained ARC execution is in a separate `source-parses` job, [105365790691](https://github.com/woahwhattheheck/commons/actions/runs/35269752383/job/105365790691), whose actual log contains the focused 30-test normal/optimized suites and the 24/320-case synthetic outputs. Historical coverage in that job does not establish current-base execution.

Equally, root-level paths alone do not establish causal independence from the ARC change. The report has exit codes and source identities, **not assertion tracebacks or import/dependency traces**. It supports locating the failures; it does not prove why each failed, that all are pre-existing, or that they have since been repaired.

## Representative exact failure rows

All listed rows report `source_in_checkout_commit: true`, command `python3 ./<path>`, exit 1.

| Path | Source blob SHA-1 |
|---|---|
| `test_bass_doors_larger_fixed_20260916_01.py` | `f50c1339c336fe50d8407a9e8c9da1443bca6b3a` |
| `test_bass_doors_larger_fixed_20260916_02.py` | `e895703a015a7100c955a1cc9eb919adf7747bd0` |
| `test_bass_features_live_cash.py` | `79547abb5f5eba4516c7232d94abb4aba3a67882` |
| `test_bass_interconnect_live_cash.py` | `6480b2eda3eea0def5ca10ae721bf4a105e77dfa` |
| `test_bass_offer_live_cash.py` | `e6ec645f781a11a54d5441c64b57fb6c7cb2e933` |
| `test_bass_panel_live_cash.py` | `395ca0e8e63a782a837b70681e4fb132c14ba1cc` |

These are examples, not a complete listing of the 300 failures. No repair or newly passing result is claimed here.

## Decision-relevant use

Keep three conclusions separate: the old battery was red; its artifact contains no ARC-lane result rows; separate retained ARC-focused execution exists. The old failure cannot be relabeled green, but neither should the absent ARC rows be interpreted as ARC test failures. To attribute the 300 failures, inspect the recorded battery job's assertion output and compare against a contemporaneous base, preserving the exact file blobs. Any integration decision still needs the repository's current-head/current-base execution binding.
