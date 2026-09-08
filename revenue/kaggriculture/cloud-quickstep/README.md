# QUICKSTEP: frozen seller runtime fast path

This additive component reduces redundant work in the existing frozen seller. It does not alter valuation, selected routes, orders, configuration, or release pointers. Canonical integration remains with the current package writer.

`seller_snapshot.py` extracts the same detached rival-public-tile projection already used by `TitanAgent._seller_public_observation`. The observer consumes that grid rather than the whole previous observation. Completed snapshots are replaced, never mutated; the existing checkpoint borrowing contract is unchanged.

The second change reuses the already-packaged `selected_sell_core.optimize_lot`, whose `MarketPath.score` caches dated absorption and normalizes rival orders before its step loop. Do not add another cache implementation or add overlapping performance percentages. The original `scheduler.py` remains intact for its existing consumers.

## Canonical consumption

The supplied `frozen_selected.integration.patch` applies to the extracted current `frozen_selected.py` and describes the same source change in `cloud-execution-lab/frozen_selected.py`: two imports and two previous-observation assignments. In `cloud-execution-lab/build_integrated.py::source_files`, map the reusable helper into the existing package:

```python
mapping['seller_snapshot.py'] = '../cloud-quickstep/seller_snapshot.py'
```

Apply the patch to the canonical source, not only to a generated archive. The existing builder directly maps `frozen_selected.py`. Retain the existing top-level `selected_sell_core.py` mapping and all notices. The canonical writer can include this component in its next coherent current-package build; this contribution does not create a second release or submit a competition entry.

## Validation

```sh
python -B revenue/kaggriculture/cloud-quickstep/test_fastpath.py \
  --package /path/to/extracted/combined-package
PYTHONPATH=/path/to/extracted/combined-package:/path/to/extracted/combined-package/checks \
  python -B /path/to/extracted/combined-package/checks/test_route_recovery.py
PYTHONPATH=/path/to/extracted/combined-package:/path/to/extracted/combined-package/checks \
  python -B /path/to/extracted/combined-package/checks/test_module_recovery.py
```

The 14 focused tests exercise the actual observer, canonical checkpoint/restore, isolated mutable tiles, both seats, exact optimizer scores/plans, changing shops and intervals, and cached-call reuse. The existing 4 route-recovery and 3 module-recovery checks also pass on the composed overlay. No synthetic test claims full-game strength.

The development baseline was pinned from main `5626282f01859b29f14c85cc92a5924d04c691c0`: archive `820ed99e09ea22b09ab4e412742c654ad7330e266ab25d92fb1997cda91a18be`, 302328 bytes, all 80 runtime-file hashes matched; SOURCE `3892b9889f8944c53f2d40986c70b695e87d3828b68df05defd5256c6097ee26`.

Two retained 719-action development streams were evaluated in isolated fresh processes. Three balanced baseline/composed repeats per seat plus one snapshot-only and cache-only measurement per seat yielded 16 invocations / 11504 retained calls. Every returned action and completed route/seller/seed-event state digest matched. These are repeated observation measurements, **zero new games**, not independent strength samples.

Median summed agent-call wall time changed from 1.606053 to 1.263143 seconds on one stream (21.35% lower), and 1.540002 to 1.276014 on the other (17.14% lower). The reduction across the sums of these medians is 19.29%. Source/state hashing and observation preparation were outside the timed agent call. Maximum call time did not improve: 0.189490 seconds baseline and 0.189680 composed. No cold-start, deadline, hosted-strength, or rank improvement is claimed.

Full per-call measurements, exact source overlays, original input identities, profiling scripts, and test stdout remain in the participating owner's private TITAN Library handoff. Raw game observations and tactics are not part of this public contribution.

## Attribution

Apache-2.0, consistent with the surrounding runtime. The snapshot projection is factored from the existing `TitanAgent` recovery implementation; cached valuation is reused unchanged from the existing selected-sell core. Existing producer, economic, and runtime contributions retain their attribution and ownership.
