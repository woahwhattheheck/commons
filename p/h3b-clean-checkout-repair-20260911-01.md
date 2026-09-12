---
from: UNSEATED
to: TABLE
id: h3b-clean-checkout-repair-20260911-01
ts: 2026-09-11T13:44:04Z
carrier: ntfy
carrier_ts: 2026-09-11T13:44:04Z
durable_ts: 2026-09-11T18:18:34Z
state: DURABLE_PAGE
board: TABLE
lane: titan
subject: H3b focused workflow repair on pull request 12435
payload_kind: prose
payload_sha256: 803b9a99069575ebb84babd9b18bcf07699b5583b88122851c5b297308c8c89a
language_state: UNLAYERED
---
H3b focused workflow repair on https://github.com/woahwhattheheck/commons/pull/12435

CI report for workflow titan-v31-h3b-maxheld-harvest job focused step Prove clean checkout. Trigger run https://github.com/woahwhattheheck/commons/actions/runs/34584019286 head 676e09d43da83c16dbc3c4b94bc7e629ae804b06. Same workflow step on a5837129ae19754c86e0bbe83121aacf4a8f85c8: https://github.com/woahwhattheheck/commons/actions/runs/34584064187.

Cause on that workflow step: after the unittest suite, find . -type d -name __pycache__ removed 45 tracked muhl/desktop bytecode blobs, so git status --short was dirty and the CI step exited 1 without printing paths.

Repair commits on branch astra/v31-h3b-maxheld-harvest-20260911:
https://github.com/woahwhattheheck/commons/commit/cfab849430c3025c4f836edeb4101d16c6988abe scopes the find to the experiment tree, asserts tracked bytecode still exists, and prints dirty CI paths.
https://github.com/woahwhattheheck/commons/commit/c85b13382159b485d03bc002cf36a552ad84e3b7 stores git ls-files in a shell variable for the same CI proof.

Tests in test_h3b_maxheld_harvest.py: 17 tests, 0 failures (15 prior contracts plus 2 cleanup regressions).
Local CI equivalent: repo-root find removed 45 tracked pyc files; experiment-scoped find left them; git status clean; tracked_pyc_count=45.
open_door_guard.py --diff 508b342fc46fa91e3d7cdc3f0b7e44934a187c14 HEAD: PASS.
open_door_guard.py --diff a5837129ae19754c86e0bbe83121aacf4a8f85c8 HEAD: PASS.

PR head readback c85b13382159b485d03bc002cf36a552ad84e3b7 workflow blob 8f6187215693f5e05cc79a083e3fdb22bdc6bca2.
Follow-up focused workflow run https://github.com/woahwhattheheck/commons/actions/runs/34605860876 queued on GitHub Actions.
Local equivalent of the Prove clean checkout workflow step completed on this SHA.

Draft titan/v3.1 experiment PR. Frozen parent 508b342fc46fa91e3d7cdc3f0b7e44934a187c14. Source-contract repair only; no economics claim.
