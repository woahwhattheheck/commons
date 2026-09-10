# TITAN V3 E13 future-sale solvency custody closure

Operation: `TITAN-V3-E13-FUTURE-SALE-SOLVENCY-CUSTODY-20260910-01`

Parent packet: draft PR #12037, commit
`304b73013e7df0e8ffb69f487c7590a9e3fa5e4a`.

## Why this child exists

The first packet correctly binds and replaces one source function, but its CLI
uses predictable `candidate.tmp` and `receipt.tmp` staging names. A pre-planted
hard link at either temporary pathname could write through to a protected file
before the final canonical readback notices the mutation. The first workflow
also does not force pull-request events to check out the exact reviewed head.

## Closure

`safe_materialize.py` authenticates the exact parent generator Git blob
`cc7dd4133a43da29294770d9b066ef550b34aaa6`, then owns every destination write:

- reject direct destination symlinks;
- reject same-inode aliases to the generator, active source, or interpreter;
- reject candidate/receipt same-inode aliasing;
- stage through `mkstemp` exclusive random files;
- atomically replace destination directory entries;
- prove generator, source, and interpreter bytes remain exact.

Eleven focused tests include two predecessor killers with pre-planted fixed
`.tmp` hard links, protected hard-link aliases, candidate/receipt aliasing,
direct symlink custody, canonical destinations, generator drift, deterministic
readback, and no temporary-file residue.

The child workflow checks out `${{ github.event.pull_request.head.sha ||
github.sha }}`, asserts that exact SHA before execution, runs every producer
under `set -euo pipefail`, retains source/candidate/receipt/provenance/log/hash
artifacts, and proves canonical inputs clean.

Disposition remains `SOURCE_REAL_ACTION_UNMEASURED`. This changes no policy,
canonical runtime, configuration, archive, pointer, provider, Kaggle, or
submission state. Returned-action activation and matched both-seat economics
remain mandatory before integration.
