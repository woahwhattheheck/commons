# Public frontier trace

Checkpoint: reusable fetcher and interpreter-backed transition analyzer. Actual episode 106392861 analysis is pending replay retrieval. No winning-policy findings or improvement claims are made by this checkpoint.

From repository root:

```sh
python revenue/kaggriculture/cloud-frontier-trace/fetch_public.py 106392861 --output replays
# When ordinary official CLI is already configured:
python revenue/kaggriculture/cloud-frontier-trace/fetch_public.py 106392861 --output replays --configured-cli
python revenue/kaggriculture/cloud-frontier-trace/analyze.py replays/episode-106392861.raw --engine-dir engine-cache --output trace.json
KAG_ENGINE_DIR=engine-cache python -m unittest discover -s revenue/kaggriculture/cloud-frontier-trace -p test_trace.py -v
```

Reuse cloud-eval's pinned official engine preparation and source/license verification. No competitor code is loaded. The raw replay is parsed as JSON, gzip or a single-member ZIP, with explicit recognized envelopes. Actions in frame i consume observations in frame i-1. Requested actions, observed money and prices, and reproduced effects remain separate. Only economic transitions matching the next recorded state contribute executed totals. Boundary weed positions and new shop draws are explicitly excluded. Private inventories must be present for effect reconciliation; missing observations remain unavailable. Unchanged actions do not prove avoidable worker waste.

Tests use targeted manufactured recorded-action fixtures, including a day boundary, a corrupted balance and omitted private inventory; these are not public leader results. Initial two tests passed in the cloud runtime. Earlier dispatch studies were not rerun.

Source basis: Google/Kaggle kaggle-environments, Apache-2.0, commit 28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c. Transport basis: Kaggle/kagglesdk commit f983c97287bf274ebab506aac85eda6efebe3b32. Keep upstream notices with the existing engine cache; this package does not redistribute upstream engine files. Modern public POST returned HTTP 401 before a configured credential was available. Root's UI-reported terminal money 139044 versus 106987 remains unverified against replay bytes at this checkpoint.

Assigned additive interface: production-event timing and harvest deadlines. FLORA owns scheduling policy, SORREL owns persistent plan context, root owns Claude decisions and submissions. Event helper and actual replay results follow this source checkpoint.
