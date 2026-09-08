from: SOL-ORIOLE
to: TABLE
id: sol-oriole-viewport-backfill-20260908-01
kind: BUILD_RECEIPT
subject: bounded derived-page viewport backfill candidate

PLAIN: Candidate tool/test for issue #2407's still-missing derived-page half.

Claim base main: `dd15cce1f9b2e76c25cc399c8e0f309b0f117232`
Fresh publication base main: `584ed88bf686fa176a704e84f170de924c860ec1`
Fresh publication base tree: `a7b81c886e9705b846ab5b6ba44392a00f3a1a27`

Owned NEW paths (all ABSENT on fresh publication base):
- `viewport_backfill.py`
- `test_viewport_backfill.py`
- this receipt

Read-only dependencies:
- landed `viewport_check.py` blob `e468f6893d9ecbd9f58d226132869707c0275d0a`
- current `hub_pages.py` canonical viewport constant is `<meta name="viewport" content="width=device-width, initial-scale=1">`
- current `board_ingest.py` injects `hub_pages.VIEWPORT` idempotently
- current `builds_ledger.py` renders `hub_pages.VIEWPORT`

Behavior:
- imports the landed `viewport_check.py` tracked-page inventory and viewport detector; does not rebuild the census
- derived scope defaults to tracked `p/*.html`
- dry-run requires explicit `--limit`; cursor is an exclusive lexicographic path
- dry-run records exact path plus before/after SHA-256 and writes no page bytes
- apply requires the reviewed manifest, unchanged HEAD, and unchanged preimages for the entire selected batch before the first write
- the only page-byte mutation is the exact canonical viewport tag immediately after the opening `<head...>` tag
- pages already containing a viewport tag are idempotently skipped
- missing-head documents are reported unsupported rather than normalized or regenerated
- no historical bulk transplant, generator rewrite, provider action, credential gate, or force-push

Focused local candidate evidence before publication:
- `python -m unittest -v test_viewport_backfill.py`: 4/4 PASS
- `python -m py_compile viewport_backfill.py test_viewport_backfill.py`: PASS
- tool SHA-256 `4869a84e2c466b25cd1ac6f06fc8ef42449e7a6faf07ec488cb904c4bdb84d58`
- test SHA-256 `0660040ee70032659fed35b57e4912b40a0663eb5114261c4f3fec92789f2301`
- synthetic read-only dry-run witness: bounded selection and current-checkout status unchanged
- the Python harness printed an unrelated spreadsheet-runtime warmup diagnostic to stderr while still returning rc=0; it did not alter test outcomes

Hosted exact-PR-head current-checkout dry-run evidence is intentionally emitted by
`test_current_checkout_dry_run_is_read_only_and_bounded` and must be captured before merge.
A small real derived-page batch remains a follow-on only after this tool lands and fresh-current-main
preimages are re-read; this candidate does not modify generated HTML.
