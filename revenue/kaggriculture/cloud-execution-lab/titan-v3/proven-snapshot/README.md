# Titan v3 proven-snapshot restoration

This lane turns the frozen September 7 finite-horizon SELL policy into a clean
`main.py::agent` candidate **without importing today's canonical wrapper or any
of its later feature flags**.

The source is already retained in `exports/titan-sell-v3-source.tar.gz`. Its
recorded source identity is commit `9f89a2cd75c5c89198caa1617a9e399900553ce3`,
archive SHA-256 `a14f9bbc7e10753fef2d5e983e9746e107940d7081b8934fb499561191e9c3c7`,
and source entrypoint `candidate.py::agent`. The repository records 12-0-0
development and 8-0-0 held-out local official-interpreter panels for those
frozen bytes. Those results are not a hosted leaderboard score.

## Why this candidate exists

`candidate.py` exposes the measured `scheduler.agent` directly. The current
canonical `main.py` instead constructs `TitanAgent` from `TITAN-CONFIG.json`,
which presently enables later redundant-hire, market-pressure, operating-stock,
idle-fertilizer, crop-release, and early-capital transforms. Several release
entries explicitly say those increments lack a new full-game score panel. A
clean restoration candidate separates the measured policy from wrapper drift
and gives the official both-seat evaluator an honest champion boundary.

This does not claim that every later transform is bad. It creates the missing
control needed to discover which composition actually wins.

## Materialize

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python titan-v3/proven-snapshot/restore.py \
  --output /tmp/titan-v3-proven.tar.gz \
  --receipt /tmp/titan-v3-proven.receipt.json
```

The command fails unless all of the following agree:

* the hard-coded source commit, archive length, archive SHA-256, member count,
  and source-freeze SHA-256;
* `exports/ARTIFACTS.json`, `exports/FILES.json`, and every byte in the archive;
* the five source identities in `SOURCE-FREEZE.json`;
* the exact 15-member runtime allowlist and deterministic tar metadata;
* compilable Python, closed local imports, and the thin
  `candidate.py -> scheduler.agent` contract;
* an isolated import of the generated `main.py::agent` package.

The output preserves every frozen source byte and adds only:

```python
from candidate import agent
```

Its tar and gzip metadata are deterministic. The JSON receipt binds every
member, source archive, generated entrypoint, and final candidate hash. Existing
outputs are never overwritten unless `--overwrite` is explicit.

## Acceptance

```bash
python -m unittest discover -s titan-v3/proven-snapshot -p 'test_*.py' -v
python titan-v3/proven-snapshot/restore.py --output /tmp/titan-v3-proven.tar.gz \
  --receipt /tmp/titan-v3-proven.receipt.json
```

The unit suite covers exact materialization, byte determinism, artifact and
member-manifest drift, source-freeze drift, undeclared imports, entrypoint
mutation, traversal, symlink, duplicate member, tar metadata drift, overwrite
protection, and pre-publication receipt conflicts.

## Promotion boundary

Treat the emitted archive as a challenger/control, not as an automatic release.
Run it against current canonical and the LAND candidate on an identical,
complete, both-seat official-engine panel. Preserve exact archive hashes and
cell identities. Only measured outcomes authorize selection or upload.
