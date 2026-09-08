# Validate a runnable panel before dispatch

The existing `run_panel.py` now validates its configuration before creating the output directory or starting its thread pool. A reversed seed range, a nonpositive converted shard size, an empty arm map or an empty opponent list returns the ordinary CLI error exit code 2. Missing or malformed required fields, unreadable JSON and unusable worker counts use the same path. No evaluator is invoked for those requests, and existing report bytes stay intact.

The valid job enumeration is unchanged. Single-seed and ragged shards, zero or negative integer seed values, the existing `int(shard_size)` conversion, nonempty arbitrary actor references, duplicate opponent entries, empty arm labels and additional configuration fields remain supported. This change does not inspect source identities, reuse completed evidence, change concurrency or replace checkpoint handling.

## Executed validation

18 methods pass, including 35 actual malformed-configuration CLI invocations and valid-grid planning fixtures. The real CLI witnesses execute the runner in a subprocess; valid-grid controls substitute only the evaluator job callable and run the original planning and checkpoint path. These are not simulated or official games. The original f0e6fde8 source independently reproduced three empty-success cases: reversed range, negative shard size and empty arms. A completed five-method focused baseline has four assertion records across those three methods and two passing valid-grid controls, with no test errors.

The full original-source battery was interrupted at its containing tool limit; its partial logs are preserved separately and are not counted as a completed comparison. The full fixed-source battery completed successfully. Exact counts and source identities are in PANEL-CONFIG-RESULTS.json.

Run the new tests from any working directory:

```sh
python -B revenue/kaggriculture/cloud-widefield-lab/test_panel_config.py \
  --report /tmp/panel-config-results.json
```

To exercise a pinned alternative runner, pass `--runner /path/to/run_panel.py`. The source-specific report distinguishes this argument/planning coverage from TANDEM's source/result binding and TRIAD's future/checkpoint handling. Neither implementation is replaced. Canonical TITAN runtime, archives, selected policy and all existing experiment outputs remain unchanged.
