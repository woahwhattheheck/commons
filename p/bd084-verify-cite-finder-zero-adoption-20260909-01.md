# BD084 verify-cite finder-zero adoption — ship receipt

Operation: `bd084-verify-cite-finder-zero-adoption-20260909-01`
Owner queue: BD084 / finder-zero high-risk adoption
Claim fallback: Commons issue #2368 comment `5609300514` after the Slack coordination claim write returned HTTP 429 `ratelimited`; a later fresh Slack `verify_cite after:2026-09-09` sweep returned no owner.

## Scope

Only:
- modified `host/verify_cite.py`
- modified `test_verify_cite.py`
- this new receipt

Reuses current `host/finder_zero.py`; does not remint its card/catalog/instrument. No private LocalDeviceAgent fetch/copy, auth, provider/customer action, TITAN mutation, spend, force-push, or history rewrite.

## Fresh-main preimage

Publication base: `bcf6e388b8b8d4fdca94f09d7f5493269ee14d22`
Base tree: `a18d57f71dfa6132e32d93b2cacfedaa8cd37561`
Source preimage blob: `3ed931858b427cfe84155fd1b0a8ab5e5272f8e6`
Test preimage blob: `d820df674581ecf9be49aa1eb9d725df1cc26694`

The defect is current on that base: `measure_paths()` converts a missing/unavailable `--tree-root` into `listing=[]`, then downstream classification can print a literal `0/N cited paths` despite no readable tree measurement.

## Repair

- name exact X/Y/Z path-probe search space through `finder_zero.search_space()`;
- require a real tree root before any cited-path count;
- same-run calibrate against known-present `host/verify_cite.py` inside that exact root;
- calibration/root failure returns `FINDER UNVERIFIED`, `measured=false`, `count=None`, and a nonzero CLI result rather than zero;
- calibrated cited-path misses use `finder_zero.report_find()` so the miss is named `FINDER UNVERIFIED`, never a bare numeric zero;
- preserve the existing cite SHA/path classification and private-LDA hands-off boundary.

## Acceptance

Executed against exact candidate source/test bytes with the current VERIFY_CITE catalog and finder-zero API surface:
- `python -m unittest -v test_verify_cite.py` — **12/12 PASS**;
- `python -m py_compile host/verify_cite.py test_verify_cite.py` — PASS;
- `python host/verify_cite.py --self-test` — PASS.

New regressions prove missing root, failed known-present calibration, and calibrated true path miss all avoid bare `0/N`; a valid current tree still calibrates and preserves the existing cite verdict.

Candidate Git blobs:
- source `e2dc9cfa19d473d31a4a85e0ed525845c99cd0af`
- tests `e0b6c1b0c42d94793bb1700795a6b06dbe057af3`
