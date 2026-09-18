# Retained recovery logs

`execution-logs.json.gz` is a gzip-compressed UTF-8 JSON object mapping eight filenames to their exact original log text. It contains the original compile/normal/optimized stdout and stderr, and the independent normal/optimized combined logs. Empty stdout streams are retained as empty strings. No log text was rewritten.

Archive: 1,419 bytes; SHA-256 `35dfc807c5ebfdc963d822734fb5077de30bdc2632b9a95896ad16b7c25553bc`; Git blob `8e513b5c5b949ebbc809dfdc3ea9f62724711c05`.

Read without extracting paths or requiring another package:

```sh
python -c 'import gzip,json; d=json.load(gzip.open("execution-logs.json.gz","rt")); print(d["normal.stderr.log"],end="")'
python -c 'import gzip,json; d=json.load(gzip.open("execution-logs.json.gz","rt")); print(d["optimized.stderr.log"],end="")'
python -c 'import gzip,json; d=json.load(gzip.open("execution-logs.json.gz","rt")); print(d["independent-normal.log"],end="")'
python -c 'import gzip,json; d=json.load(gzip.open("execution-logs.json.gz","rt")); print(d["independent-optimized.log"],end="")'
```

The normal/optimized original logs hash to the stderr hashes in `execution_receipt.json`. Counts are 34 and 34 for the original suite and 15 and 15 for the independent suite, all PASS. Captured timings are environment observations, not promised performance.

`check_report_render.py` is the recovered optional browser check; it is not required for the standard-library proof commands. It expects Playwright and `/usr/bin/chromium` already installed, generates screenshots locally to the selected proof directory, and makes no live deployment claim. It intentionally uses `set_content` rather than `file://` navigation. To reproduce in an existing compatible cloud browser environment:

```sh
python build_demo_report.py --output lacsd-proof/synthetic-demonstration-v3
python check_report_render.py
```

Do not buy or install a paid service solely for this optional render replay. Historic screenshots were not added to repository storage; the executable render recipe and deterministic HTML builder are retained instead.
