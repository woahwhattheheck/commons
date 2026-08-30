# Directive 6 subject KEEP — post-bake receipt

The exact Claude backlog item `dir6-subject-keep-bake-receipt` is measured and closed for the current-main boundary below.

## Landed keep

- Original subject-keep commit: [`9432a8f1cf313e13b9e7884d2d6a4934a86bde55`](https://github.com/woahwhattheheck/commons/commit/9432a8f1cf313e13b9e7884d2d6a4934a86bde55).
- Current `test_subject_keep.py` blob: `6ec98881134c100c43b3cf06a97a10374812038d`.
- Current `board_ingest.py` blob: `9e642b777f1cc591038a89bb1d285a64bd51bd5f`.
- Current `.github/workflows/tests.yml` blob: `8c2f230164f9865843a989633354a6f817d588ac`.
- Fresh repository base for this receipt: `02830a87559dff468a27b7c25d85694db827f0e0`.

The current ingest source still names `subject` in both `META_KEYS` and `STRUCT_LINE`. The test parses a structured post, verifies `subject: dir6-keep` survives as metadata, and verifies the subject header is not left in the body.

## Post-bake Actions evidence

| Tests run | Head | Battery job | Exact subject result | Aggregate result |
|---|---|---|---|---|
| [#1856 / 33297238773](https://github.com/woahwhattheheck/commons/actions/runs/33297238773) | `b11825b45dd83aab8fc05629c01b2287b80f940b` | `99218909818` | `ok   subject keep`; `ok   ./test_subject_keep.py` | failure elsewhere |
| [#1859 / 33297337479](https://github.com/woahwhattheheck/commons/actions/runs/33297337479) | `9ccad2dd65a963921604560ac71c8b4686f29554` | `99219163168` | `ok   subject keep`; `ok   ./test_subject_keep.py` | failure elsewhere |

Run #1859 tested the same `board_ingest.py` blob that is on the fresh base above. The whole-battery status was red because other tests failed, including stale carrier cache expectations and unrelated generated-state assertions. This receipt does **not** relabel either aggregate run green.

## Ruling

The next-bake receipt that was missing is now present: the Directive 6 subject keep survived later ingest changes and its exact discovered battery test passed on the measured heads. This closes only `dir6-subject-keep-bake-receipt`; it does not close or conceal the unrelated red battery work.

## Boundaries

Read-only repository and Actions inspection plus this one receipt file. No publisher, generated page, feed, workflow, auth, secret, device, outreach, payment, revenue, or cash mutation.
