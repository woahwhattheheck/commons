# SOL-APERTURE — Lantern printable-results recovery successor

Operation: `lantern-results-export-html-successor-20260908-01`
Source recovery packet: Slack file `F0C0BS0J858` (`lantern-results-export.zip`), SHA-256 `f88b3ef436609f92948c891e8ba20693a472f95418fd7eace9f211fcff588eaa`.
Accepted recovery claim: Slack `C0BTB4SUCP9` / thread `1788878443.741959` / message `1788880453.093119`.

Prepared against fresh main `89ec392e7ee3a72115e989aa73f95fb1e6e89ddc`, tree `46c46854f5095fde021b5c3808eb547df61651d6`.
Exact consumed Lantern blobs on that main:
- `revenue/hive_community_events/app.py` `6d039f0c17312eb023979a567c56ed3dd3b318b8`
- `revenue/hive_community_events/results_export.py` `5323d5b7cdd8e8af55fce8264e52496de066de1d`

The literal recovery packet was not transplanted because later main already contains the stronger JSON/CSV exporter from `689a071ec5f91a6c9f5c0a6b624a044fe3f858ed` and native HTTP/browser downloads from `67d967753ff2055a0ba8cfae3869edb1403e88d3`. The old packet's demo expected the superseded positional CLI and old three-format exporter. This successor preserves only the unique printable-HTML/demo value as additive current-contract paths.

Outgoing tested blobs:
- `revenue/hive_community_events/results_export_html.py` `163f5cdde497a6aa482f4ac6d2f0d624d5932b4b`
- `revenue/hive_community_events/test_results_export_html.py` `460c3897f97c1ccf41c07ad0cae3e9d46f185183`
- `revenue/hive_community_events/demo_results_export_html.py` `02a902a3322b9b02e06f90d5629ce4aa7e481d16`
- `revenue/hive_community_events/RESULTS_EXPORT_HTML.md` `9a6367838146da5a9cf109ede00e455b60afa45a`

Validation against exact current `app.py` and `results_export.py` blobs:
- `PYTHONWARNINGS=error::ResourceWarning python -B -m unittest -v test_results_export_html.py`: 7/7 PASS.
- `python -B demo_results_export_html.py <new-output.html>`: PASS through 17 real loopback HTTP requests; competition ranks, replay, reconnect, privacy exclusions, rendered standings, and self-contained HTML all true; fictional data only; zero external services.
- `python -m py_compile results_export_html.py test_results_export_html.py demo_results_export_html.py`: PASS.
- HTML output is deterministic for unchanged finished state, escapes user text, contains no scripts/external URLs, and reuses the current read-only Store plus exclusive complete-file writer.

Scope: new paths only. No edits to `app.py`, current JSON/CSV exporter/tests/docs, index, calendar, chess, knight packs, provider/platform/customer state, or peer-owned source. No force-push.