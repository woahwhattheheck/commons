# SOL-RATCHET — Titan v3 proven-snapshot restoration

Status: implementation complete; additive review branch shipped.

## Finding

The repository's strongest directly measured policy is the frozen
`finite-horizon-v3` callable from September 7. It recorded 12W/0T/0L development
and 8W/0T/0L held-out local official-interpreter results. Its entrypoint is
`candidate.py::agent`, a direct alias to `scheduler.agent`.

Current canonical execution goes through `main.py -> TitanAgent` and enables
multiple later transforms. The release record explicitly withholds full-game
strength claims for several of those increments. The frozen source archive is
therefore the correct clean control, but it lacks the canonical
`main.py::agent` submission entrypoint.

## Delivery

`restore.py` verifies the exact immutable source archive and all three evidence
layers (`ARTIFACTS.json`, `FILES.json`, `SOURCE-FREEZE.json`), rejects unsafe or
nonclosed packages, and deterministically adds only a thin `main.py` alias. The
result is a runnable candidate whose policy bytes are identical to the measured
source. A JSON receipt binds every member and final output hash.

## Acceptance

```bash
python -m compileall -q \
  revenue/kaggriculture/cloud-execution-lab/titan-v3/proven-snapshot
python -m unittest discover \
  -s revenue/kaggriculture/cloud-execution-lab/titan-v3/proven-snapshot \
  -p 'test_*.py' -v
```

Promotion remains contingent on a complete identical-cell, both-seat official
panel against current canonical and the LAND candidate. No upload or score claim
is authorized by this receipt.
