# Commons path and subsystem map

`path-manifest.json` is the shared descriptive map for canonical records,
generated projections, executable source, public surfaces, commercial and
orchestration catalogs, evidence, and the large Muhlnickel corpus.

It has no participation effect. It never decides whether a post, Action Pad
request, job, or adapter invocation lands. It exists so generators, tests, CI,
builders, sparse-context workers, and future mirrors can describe the same path
with the same classification.

Run the deterministic diagnostic:

```bash
python3 host/path_manifest.py
python3 host/path_manifest.py --report /tmp/commons-path-report.json
```

The report reads `git ls-files`, applies first-match rules, inventories root and
nested tests, and extracts declared generator path lists such as
`board_ingest.py:ASSET_PATHS` through Python's AST. Paths that need a more
precise mapping stay visible as `UNMAPPED`; they do not stop existing roads.

The checked manifest is source. Reports are exact-tree observations and are not
committed as a second repository truth.
