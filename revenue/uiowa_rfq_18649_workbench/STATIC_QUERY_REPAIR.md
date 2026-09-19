# Static-query launch repair

Operation: `zz-copper-workbench-static-query-20260919`.
Builder/reviewer: ZZ-COPPER / GPT-6 Astra Pro. Date: 2026-09-19.

## Behavior

The UI supports `?demo=1`, but the server previously used the entire HTTP request target as a static-file key. Both `/?demo=1` and `/index.html?demo=1` therefore returned 404 before JavaScript loaded. The change removes the query portion only for static GET/HEAD lookup. It does not URL-decode paths, alter the asset inventory, serve arbitrary files, change inspection POST routing, or change response headers or compiler behavior.

The new regression suite creates synthetic static files in a temporary directory and runs the actual loopback HTTP server with a recording adapter. It verifies plain/query route byte equality, content types and response headers, root and explicit-index demo entry, an empty query, HEAD metadata without a body, unknown-path diagnosis, unchanged POST routing, and successful existing inspection routing. The root-level unittest wrapper makes this suite discoverable by the existing repository test workflow and preserves optimized-interpreter execution.

## Executed evidence

Starting main revision: `43e27f87bcbede7840a7646fc49d55f626650e28`.
The source read immediately before publication matches retained baseline server blob `42ab51cd91e2c196909c69c4f056a2552c158001`.

Python 3.13.5, isolated cloud container, no real University data:

| Run | Result |
| --- | --- |
| Original server, nine HTTP tests | FAIL: 8 failing assertions/subtests, reproducing query-route 404 |
| Patched server, normal Python | PASS: 9 tests |
| Patched server, optimized Python | PASS: 9 tests |
| Root discovery wrapper, normal Python | PASS: 1 wrapper executing the 9 HTTP tests |
| Root discovery wrapper, optimized Python | PASS: 1 wrapper executing the 9 HTTP tests |

Run from repository root:

```sh
python -B -m unittest -v test_uiowa_workbench_static_queries.py
python -O -B -m unittest -v test_uiowa_workbench_static_queries.py
```

Or from this directory:

```sh
python -B -m unittest -v test_static_queries.py
python -O -B -m unittest -v test_static_queries.py
```

Exact authored blobs:

- `server.py`: `076c15c5102067eb2610e00d4608f62b9abb0088`
- `test_static_queries.py`: `be1a18d9dd19e865f7f51ec55201a872d68bb47c`
- root `test_uiowa_workbench_static_queries.py`: `7278b9d2aabab580d276b43203e8b3863423ba91`

This is HTTP/component execution, not Chromium, real-compiler, hosted-CI, or production proof. It does not grant evidence-review, submission, commercial, or scheduling authority. Provider execution and merge state must be read from the PR rather than inferred from these local results.

## Composition

The combined Keystone/Trellis restore and Markdown carrier is PR #16145. This change leaves its UI contract and validator untouched. When composing, retain that carrier's added static assets and change only the static lookup expression. The regression iterates over the actual asset inventory, so added assets are exercised without copying an outdated list. Do not replace a newer `server.py` wholesale with this revision.
