# GitHub Content-Write Pacemaker

This package coordinates a large cooperative fleet without holding a provider
token or performing network I/O. Callers enqueue exact GitHub mutation intents,
claim one connector-ready envelope at a time, invoke an already-connected
GitHub action, and record the observed provider result.

The state machine provides FIFO pacing, semantic replay collapse, provider
cooldowns, durable pre-dispatch state, and fail-visible reconciliation after an
ambiguous outcome. A timeout or lost response blocks later claims until an
external provider readback is recorded.

It is not caller admission, permission, approval, or distributed consensus.
Raw GitHub writers remain open and can bypass the queue. Cooperating callers
must share one SQLite generation; one database per worker is split brain.

## Example

```bash
python -m tools.github_content_write_pacemaker.cli --db /private/pacer.db init
python -m tools.github_content_write_pacemaker.cli --db /private/pacer.db enqueue --intent intent.json
python -m tools.github_content_write_pacemaker.cli --db /private/pacer.db claim-next
# invoke the connected GitHub action once
python -m tools.github_content_write_pacemaker.cli --db /private/pacer.db record-result \
  --key example-operation-v2 --attempt 1 --classification committed \
  --provider-status 201 --reason 'connector returned success'
```

Receipts omit raw body and description text, retaining only exact SHA-256
commitments and state. Intents are read through one bounded no-follow regular
file descriptor. SQLite integrity and all semantic digests are rechecked by
`verify`.

## Verification

```bash
python -m py_compile tools/github_content_write_pacemaker/*.py
python -m unittest -q \
  tools.github_content_write_pacemaker.test_queue \
  tools.github_content_write_pacemaker.test_integrity
python -O -m unittest -q \
  tools.github_content_write_pacemaker.test_queue \
  tools.github_content_write_pacemaker.test_integrity
```

The package deliberately contains no direct HTTP client, token discovery,
credential transport, provider login, or hidden retry loop. The caller must
read back uncertain mutations and explicitly reconcile them before another
claim can be issued.
