# BD084 MCP/wake finder-zero adoption — ship receipt

Operation: `bd084-mcp-wake-finder-zero-adoption-20260909-01`
Owner queue: BD084 / finder-zero high-risk adoption
Coordination: explicit implementation RELEASE/HANDOFF in `#coordination-channel-created-today-please-use`, then SOL-ASTRA claim at Slack ts `1788992376.423649`.

## Scope

Only:
- modified `host/mcp_wake.py`
- modified `test_mcp_wake.py`
- this new receipt

Reuses current `host/finder_zero.py`; does not remint its instrument/card/catalog. No wake creation or resume, no `~/.grok` mutation, no auth/provider/customer action, no TITAN mutation, no spend, no owner-PC action, no force-push or history rewrite.

## Fresh-main preimage

Publication base: `58227a4bedec6249021b5cf41c38712f8382e591`
Base tree: `2cbaea707dcab848b9c15a10edd4fc0a34b5207a`
Source preimage blob: `c99f19d3cf438d09abbe1cf565c61d7ffd2ca22f`
Test preimage blob: `3ccf24ac93d8e3cfa8afe6067e9cdf4354c43934`
Receipt path was absent on that exact base.

The defect is current on that base: `_wake_job_census()` treats a missing `wake_jobs/` directory, an unreadable listing, or a listing with no canonical calibration canary as an ordinary empty list/count. Downstream `measure_root()` therefore emits `wake_job_json=0`, `wake=EMPTY`, and can still classify the broader MCP row `INTEGRATED` even though the filesystem finder never proved its zero.

## Repair

- name exact X/Y/Z filesystem search space through `finder_zero.search_space()` for `wake_jobs/*.json` excluding `_last_tick.json`;
- take one filtered directory snapshot and derive both finder hits and row census from it;
- same-run calibrate against known-present `wake_jobs/specter-watchdog-head-proof-20260825-01.json`;
- missing or unreadable `wake_jobs/`, `_last_tick.json`-only, or any listing missing that calibration canary fail closed with `finder_state=FINDER UNVERIFIED`, `wake_job_json=null`, `wake=FINDER UNVERIFIED`, and an overall non-INTEGRATED classification;
- preserve calibrated production semantics: canonical DONE canaries still produce `wake=VERIFIED`, while GROK_EXECUTOR queue rows remain visible without poisoning the canonical verdict;
- preserve `null` in the emitted catalog rather than coercing an unverified count to numeric zero;
- keep the existing no-secret, no-live-resume, temp-JobStore-only and TITAN hands-off boundaries unchanged.

## Candidate custody

Candidate source Git blob: `e68905828ea5d0346d76b469fbdf1daf3336f48c`
Candidate test Git blob: `3636fbac67ba5c67c7d872e1199742c9b6be35b8`

The focused regressions cover missing directory, `_last_tick.json`-only, queue-without-calibration-canary, unreadable `os.listdir`, calibrated SPECTER+executor semantics, catalog null preservation, and live-tree calibration/VERIFIED behavior.

## Acceptance boundary

Before merge, the exact candidate head must be checked by hosted repository CI and the three-path PR diff must be re-read. Intended focused commands are:
- `python -m unittest -v test_mcp_wake.py`
- `python -m py_compile host/mcp_wake.py test_mcp_wake.py`
- `python host/mcp_wake.py --self-test`

This receipt does not claim those hosted checks have passed until the exact-head run is read back. It does not authorize or perform wake execution, Grok mutation, idle resume, customer/provider action, TITAN work, spend, or unrelated integration.