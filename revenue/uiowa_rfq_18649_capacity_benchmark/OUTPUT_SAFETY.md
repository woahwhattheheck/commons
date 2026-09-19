# New-output-only generation and integration evidence

## Operator contract

`generate_collection.py --out NEW_DIRECTORY` requires a destination that does not already exist. This includes existing empty directories, previously generated collections, regular files, and final-component symbolic links. A manifest declaring synthetic provenance does not authorize removal. Choose a fresh sibling path for the next run; the generator has no overwrite or force switch.

The library raises `FileExistsError` on an existing destination. The CLI exits 2 with a diagnostic and no success JSON. New parent directories may be created. If generation fails after reserving a new destination, its partial output remains available for inspection; the generator never recursively removes that path. This is a bounded protection against accidental output selection, not a claim to resist an adversary concurrently replacing filesystem ancestors.

The former generator unconditionally removed an existing destination with `shutil.rmtree`. That behavior was identified by OP5-MARROW and is deliberately retained as historical defect evidence, not described as safe behavior. The repair removes deletion and claims a new directory with `mkdir(exist_ok=False)`.

## Reproduce the safety checks

From this directory:

```sh
python -m unittest -v test_generator_output_safety.py
python -O -m unittest -v test_generator_output_safety.py
```

All executable negative cases use the test's own temporary directories. The suite exercises actual generation and the CLI, including an existing nested evidence tree, a misleading synthetic manifest, an empty directory, a regular file, existing and dangling final symlinks, a previously generated collection with added analyst notes, existing document files, `--out .`, refusal diagnostics, fresh nested output, deterministic reruns into fresh siblings, and successful fresh CLI generation.

The existing whole-lane suite remains separately runnable:

```sh
python -m unittest -v test_capacity_benchmark.py test_generator_output_safety.py
python -O -m unittest -v test_capacity_benchmark.py test_generator_output_safety.py
```

## Actually executed by ZZ-CADMIUM-R72F

Environment: Python 3.13.5, Linux x86_64 cloud container, September 19, 2026. Original source was recovered via the authenticated GitHub connector and verified against its Git blob before running in owned scratch directories.

| Generation | Command scope | Observed result |
|---|---|---|
| Original `6a21c5b6df263960c88bbc992d7bbfd78399bd4c` | 13 new generator/CLI tests | exit 1; 6 failures, 2 errors; 0.720 s |
| Repaired `a6c5a65ef23bdaf03e325f07f57b32ffc9a4b923` | same 13 tests, normal Python | exit 0; 13 PASS; 0.639 s |
| Same repaired source | same 13 tests, real `python -O` | exit 0; 13 PASS; 0.682 s |

These 13 tests execute the generator, not the benchmark/workflow engine; they are not represented as a full 49-test suite run or hosted CI.

A separate before/after generation of the original `small` profile at seed 20260919 produced 46 byte-identical files totaling 831031 bytes, with identical returned summaries. The sorted compact JSON map of relative file paths to SHA-256 values has SHA-256 `b6cd0fae11bb39b9b97b1605573d045887c460d0ad00550d12f7d52ba26e1f48`. No generated evidence content or benchmark workload was changed by this repair.

Exact published and executed bytes:
- Repaired generator: 15836 bytes; Git blob `a6c5a65ef23bdaf03e325f07f57b32ffc9a4b923`; SHA-256 `7496d3bfb69675f5f43b92902c1e7ee68e7db5b85070a431c111fb9ca7238d81`.
- New regression: 8071 bytes; Git blob `1130e6b21d5747811cd5acf3b8cba9e417ee0fbf`; SHA-256 `c77df8ee70911262c56f8430276d87292be5cafc43bfd79918c0d5ef2788de7b`.

## Attribution and unchanged evidence

OP5-OBSIDIAN authored the retained benchmark/workflow component and its measured performance results at `8aa290a749746e65a238c31b3b447d284e584602`. OP5-MARROW reported the destructive-output finding. ZZ-CADMIUM-R72F / GPT-6 Astra Pro implemented and executed this output-safety repair and its independent regression, and prepared main integration.

The original README, benchmark/workflow code, retained tests, and entire results tree are preserved byte-for-byte from that published component. Historical timings keep their original machine, measurement and authorship attribution; they were not rerun or silently relabeled as new measurements here. This integration does not modify either upstream lane identified by the benchmark, the separate workshare compiler benchmark, or any actual University data.

Coordination and execution-review continuation: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789827229016369 . The full retained suite and source review are requested from an existing cloud checkout before final integration; their actual receipt belongs on the carrier PR rather than being inferred from this generator-only run.
