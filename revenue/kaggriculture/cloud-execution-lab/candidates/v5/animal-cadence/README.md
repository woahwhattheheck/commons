# TITAN V5 animal cadence candidate

Status: **default OFF / evaluation only**. This package is additive to canonical V5 and does not change `main.py`, `titan_runtime.py`, `TITAN-CONFIG.json`, the release archive, or Kaggle submission bytes.

Promotion status: **BLOCKED pending matched current-line simulation evidence.** `certificate_builder.py` now provides one source-pinned certificate authority, but only for the narrow day-close/reset loop described below. The transform and builder remain uninstalled production candidates.

## Pinned engine theorem

The preserved engine is `reference/engine/kaggriculture.py` at source blob `3c202c7ee921da239356789e266b694635103fc4`.

The source-real behavior is:

- an animal survives one unfed end-of-day and escapes only when `consecutive_unfed >= 2`;
- scheduled base animal production is awarded even on that first unfed day;
- feeding gates consumption of a pending CARE bonus, so CARE value must not be discarded;
- every surviving animal sets `fertilizer_available = True` at every end-of-day, not every third day;
- duplicate same-tile FEED actions spend at most one WHEAT because the first successful FEED sets `fed_today`;
- end-of-day drops carried inventory into the shed, removes all hands, resets the main farmer, and replaces per-worker inventories with one empty main-farmer inventory;
- `FERTILIZE` consumes one fertilizer and extends `fertilized_until_day`; it does **not** directly increment `yield_units`.

The last point is an explicit negative predecessor for the rejected “infinite fertilizer yield” hypothesis.

## Candidate

`alternate_feed.py::apply_alternate_feed(observation, selected, next_feed_certificate=..., route_identity=..., turns_per_day=...)` is a pure selected-action transform. It replaces a selected `FEED` with `PASS` only when the animal tile is covered by a machine-checkable next-day FEED certificate, the actor actually carries WHEAT, the animal is on the exact zero-strike leg (`consecutive_unfed == 0`), no current or pending CARE value can be lost, and no same-tile selected CARE exists. Once the public state reports one unfed day, the next FEED is retained.

The certificate is bound to the exact public `observation_step`, exact positive plain-int `turns_per_day`, route id, route-source Git blob, and current route-tail SHA256, and gives an exact future FEED step for each certified animal tile. The transform derives the next calendar day's inclusive step window from `(observation_step, turns_per_day)` and rejects both later-same-day FEEDs (which would save no net WHEAT) and FEEDs after the next EOD (which are too late to prevent the second starvation refresh). The caller separately supplies the independently derived current `route_identity` and day length; all provenance must match the certificate.

Route switch, checkpoint/rejoin, reset, source drift, tail drift, clock advance, or calendar changes therefore require a newly minted certificate. Empty, malformed, stale, mismatched, same-day, or too-late evidence fails closed and leaves the selected action untouched.

The transform preserves market rows, other unit actions, action-slot topology, and both inputs. Its report distinguishes actor actions suppressed from actual WHEAT avoided: multiple FEED actions on one animal tile may all be suppressed to skip that day, but count as only one saved WHEAT because that is the pinned engine's baseline spend.

## Source-pinned day-close certificate authority

`certificate_builder.py::build_next_feed_certificate(...)` admits only the mechanically closed reset case. Its source custody pins the extracted engine mechanics, Arlene producer, landed operating-stock theorem, canonical cadence candidate, SpatialTempo, and crop-release modules by Git blob.

The authority requires the current step to be exact day close under the pinned 24-turn calendar. It first authenticates the current frozen-V5 feature profile: terminal route, fourth quadrant, spatial pathing and spatial tempo remain disabled, while operating-stock protection is installed. Current idle-fertilizer and crop-release flags must be exact booleans; their pinned source is part of the custody boundary.

That feature profile matters because the currently enabled dynamic unit producers do not overwrite a legal future FEED: idle fertilizer can patch only literal PASS space, weed continuation stops before a FEED, the generic spatial/tempo rewrite is disabled, and crop release's unit substitution is an exact PLANT-WHEAT to PLANT-CARROT replacement. A future source or feature-profile change invalidates this authority instead of inheriting the theorem implicitly.

For one deterministic current animal tile at a time, the builder:

- authenticates the live controller route id against pinned Arlene and requires its completed prefix to retain pinned-source lineage;
- hashes the exact live route tail with canonical JSON and binds that SHA256 into `route_identity`;
- rejects a next-day window crossing any pinned producer decision checkpoint;
- asks the canonical #13331 transform to produce a hypothetical current FEED-to-PASS postimage, then computes the exact completed current unit stage including aggregate PLANT atomicity;
- reuses the landed operating-stock `_feed_window` and room bounds with no future sale or requested-purchase credit;
- proves the saved carried WHEAT cannot be discarded by end-of-day capacity;
- requires the main farmer to PICKUP protected WHEAT on the **first unit stage of the next day** at shed access; and
- requires that same carried input to reach a later FEED on the exact skipped animal tile before next day close.

The first-next-day pickup is the key market-ordering boundary. Unit actions run before market processing, so once the saved EOD WHEAT is recovered into the main farmer's inventory on that first next-day unit stage, a later dynamic WHEAT sale cannot consume that carried unit. The landed feed-window theorem separately rejects uncertified transfers, uncovered feeds, intervening route WHEAT sales before protected pickup, unfunded hires, unresolved animal replacement, and route checkpoints.

This is deliberately narrower than “feed every other day.” It does not certify mid-day skips, late next-day pickups, unpinned route mutations, alternate feature profiles, or deadline/fallback execution. Those cases stay unchanged.

## Focused checks

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python -B candidates/v5/animal-cadence/test_alternate_feed.py
python -O -B candidates/v5/animal-cadence/test_alternate_feed.py
python -B candidates/v5/animal-cadence/test_certificate_builder.py
python -O -B candidates/v5/animal-cadence/test_certificate_builder.py
python -m py_compile \
  candidates/v5/animal-cadence/alternate_feed.py \
  candidates/v5/animal-cadence/certificate_builder.py \
  candidates/v5/animal-cadence/test_certificate_builder.py
```

The candidate tests call preserved engine predecessors for starvation, base production, CARE loss, duplicate-FEED spend, fertilizer refresh, and the FERTILIZE negative theorem. The authority suite adds exact source custody, route-tail binding, first-next-day pickup, checkpoint crossing, feature-profile drift, reset capacity, source-lineage drift, and canonical candidate round-trip cases.

## Evaluation handoff

The merged donor research artifact `candidates/v5/research/animal-feed-cadence/` pins the official engine and Arlene producer and emits a route census. The certificate authority converts the subset of live day-close observations satisfying the physical reset theorem into exact certificates consumable by `alternate_feed.py`.

Matched evaluation should run current canonical V5 twice on identical opponent/seed/seat cells: unchanged baseline versus baseline plus the authority and candidate wrapper. Record builder source pins, route identity/tail hash, authority engagement count, candidate engagement count, actor FEED actions suppressed, unique-tile WHEAT saved, paired own-score and margin deltas, loss flips/new losses, animal escapes, CARE-bonus divergence, and any authority decline reason. Promotion remains blocked until that matched evidence is current-line green; this package itself makes no activation claim.