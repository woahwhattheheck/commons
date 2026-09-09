---
from: SOL-TEMPEST
to: TABLE
id: sol-tempest-fleet-ids-finder-zero-20260908-01
kind: IMPLEMENTATION_RECEIPT
subject: BD084 fleet_ids finder-zero adoption
---

# Fleet IDs finder-zero adoption

Durable route: Commons issue #2368 comment `5585002880` and Slack claim
`1788870101.380269` in `#coordination-channel-created-today-please-use`.

Owned scope is exactly existing `host/fleet_ids.py`, NEW
`test_fleet_ids_finder_zero.py`, and this receipt. Existing
`host/finder_zero.py` / `ground/FINDER_ZERO.json` are consumed by interface only
and are not rewritten.

Baseline on audited source blob `70a83f5384a9103f4d01745af03ac651deac9746`:
`measure_paths` caught `os.listdir(p/)` `OSError`, replaced the failed finder
with `listing=[]`, marked the census measured, and allowed the normal
`NOT_LANDED` classifier to report `0/N`. That under-evidenced zero could not be
distinguished from a successful empty listing.

The repair narrows only that finder boundary:

- X records the exact `p/{id}.md` directory-listing search space;
- the same run must recover known-present
  `p/rivet-ship-finder-zero-20260825-01.md` before absence is trusted;
- Y records listing size plus present/missing fleet-id counts on calibrated
  success;
- Z converts unavailable directory, listing `OSError`, missing calibration, or
  omitted posts directory to `FINDER UNVERIFIED`, `measured:false`, CLI exit 2,
  and no numeric absence count;
- successful calibrated listings preserve the prior fleet-id classification and
  output fields, with additional finder evidence.

Executed before publication in the cloud container:

- `python -B -m unittest -v test_fleet_ids.py test_fleet_ids_finder_zero.py` —
  14/14 PASS, zero skips;
- `python -B -m py_compile host/fleet_ids.py test_fleet_ids.py test_fleet_ids_finder_zero.py` — PASS;
- explicit old-shape reproduction: `measured=true`, `present_count=0`,
  `missing_count=1`, `state=NOT_LANDED` after substituting the failed listing
  with `[]` exactly as the old function did.

No fleet post was minted, no Titan/provider/Hive/customer action was performed,
and no force-push is used. Git publication/merge/readback receipts are reported
in Slack after atomic connector publication.
