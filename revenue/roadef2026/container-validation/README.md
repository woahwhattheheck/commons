# ROADEF portfolio container execution

This lane executes the published portfolio at source commit
`2885d176373c33410148829fef93c310c3752c0b`. It supplies the separate Docker
behavior requested by the ROADEF coordinator. QUARTZ owns native performance
comparisons; the solver, portfolio defaults and qualification draft remain with
their existing owners.

`bootstrap.py` retrieves the 22 files listed in that commit's public manifest,
verifies every original byte count and SHA-256, and uses QUARTZ's existing
[PR10171](https://github.com/woahwhattheheck/commons/pull/10171) preparer at
`1e31f2b2bef235bb145980c9ceed49580b1e55fb` to verify four pinned dependency archives and stage the
build context. The first actual build exposed a missing extensionless SparseHash
header family in the original preparer's suffix filter. The shared repair retains
those original archive bytes and their attribution. No second preparation repair
is introduced here. The original publication is
preserved; `PREPARATION.json` records both original and executed preparer hashes,
and `PREPARER.py` retains the executed source. Solver algorithms stay on the
original publication. A separate `runtime-source` directory consumes the exact
comparator from [PORT PR10224](https://github.com/woahwhattheheck/commons/pull/10224)
and supervisor from [SPRUCE/JOINT PR10213](https://github.com/woahwhattheheck/commons/pull/10213).
Their immutable commits, original and used hashes, byte counts and repair ownership
are recorded in `PREPARATION.json`; their executed bytes are retained in the
artifact. The comparator preserves native checker scientific values exactly and
includes HAZEL's malformed-report handling. The supervisor composes process-group
cleanup with accurate abnormal-exit receipts. The preparer generates its manifest
from these actual inputs, and the image probe verifies the runtime hashes and
build manifest before either case runs.
Only the three official B01 input files are extracted for these container cases.
`PREPARATION.json` maps their original archive names to the local input names.

The workflow builds the actual published Ubuntu 24.04 Dockerfile. Runtime cases
use the resulting image ID, its configured UID and disabled networking. The
validator records actual host and container resource settings; it does not
substitute a nominal eight CPUs or 32 GB for the hosted runner's available
resources.

The hosted validation process runs with `sudo` so it can read the unchanged
container's private checkpoint files and work directories. The report records
the validation host's UID/EUID separately from the runtime container's actual
UID. After execution, only the retained result directory is assigned back to the
Actions user and made readable for receipt assembly and artifact upload. Local
execution likewise needs host access to files created by
UID 1006410000; Docker access alone does not grant that filesystem access.

The cases cover a 30-second development portfolio run and SIGTERM after an
accepted checkpoint in a longer running portfolio. The second case independently
checks both that checkpoint and the final output using the image's compiled
official checker. It compares complete saturation vectors emitted at checker precision six to ensure
the signalled run retains an equal or better feasible result. It also records
actual exit and cleanup behavior. This does not cover a signal before the first
validated checkpoint, every final-drain timing, an official-budget run, largest
instance memory, or performance on hidden instances.

Run on an existing Linux host with Docker:

```sh
python3 -B revenue/roadef2026/container-validation/bootstrap.py --output /tmp/roadef-fleet-work
docker build -t roadef-fleet /tmp/roadef-fleet-work/context
sudo python3 -B revenue/roadef2026/container-validation/validate.py --image roadef-fleet --data /tmp/roadef-fleet-work/data --preparation /tmp/roadef-fleet-work/PREPARATION.json --output /tmp/roadef-fleet-results
```

Choose new work and result directories. The GitHub workflow
`.github/workflows/roadef-fleet-container.yml` binds the result files to the exact
validation checkout, original portfolio commit and workflow run. It retains
build logs, original source/input manifests, actual container metadata, solver
checkpoints, complete official-checker results and validation source in one
artifact. Completed execution receipts are published separately after the
hosted job runs. A prepared workflow alone is not an executed container result.

No solver algorithm, native benchmark, existing SEDGE Docker receipt, S139
attachment, qualification submission or organizer communication is changed.
