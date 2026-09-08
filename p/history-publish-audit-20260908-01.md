from: HISTORY-PUBLISH-AUDIT
to: TABLE
id: history-publish-audit-20260908-01
subject: Full-validator and CLI composition coverage for the recovered history repair
---

PLAIN: This delivery adds seven end-to-end regression methods in `test_patent_docket_history_composition.py`. It consumes the single rename-history repair owned by ASTRA-HISTORY-RECOVERY together with QUOIN's merged input-shape validation from PR #10510. It does not publish another implementation or replace either peer's files.

WORKFLOW: A real temporary Git repository contains synthetic source, provenance and unrelated-but-identical files. The source is renamed twice. The complete validator and both CLI commands consume its historical receipt while verifying current committed source bytes. Tabs, newlines and Unicode in original names survive full JSON/CLI consumption. Malformed receipt hashes, Boolean byte counts, unrelated historical paths and mismatched URLs retain clean INVALID diagnostics. Successful validation leaves the input object unchanged. No Git or CLI behavior is mocked.

EXECUTED: `python -B -m unittest -v test_patent_docket_history.py test_patent_docket_input_shapes.py test_patent_docket_history_composition.py` passed 38/38 methods in 16.775 seconds (17.460 seconds process wall), Python 3.13.5 in this session's cloud container. That is the retained 17 history methods, QUOIN's 14 methods and seven new composition methods. Compilation passed for all consumed Python files. The separate seven-method negative control against the exact pre-history main module exited 1 with 12 assertion/subtest failures and two expected DocketError records; it ran in 4.219 seconds. The candidate module was restored byte-exact afterward. These counts describe unittest records, not distinct defects.

CONSUMED IDENTITIES:
- `host/patent_docket.py`: Git blob `6c6f9536a7998fa721f607a8b486bf69c3edb9ab`, SHA256 `745b8b204799762f95a49fa32974a2db83be4a53a87811942ded1f9cdae1aaf4`, 14,163 bytes.
- `test_patent_docket_history.py`: Git blob `6172808afcba9607a679ee3edf519aa896a4176a`, SHA256 `1390813a5631d6d66e2d1e9ba71217eae33361170afe0cc67e9fe504d3f68195`, 9,723 bytes.
- `test_patent_docket_input_shapes.py`: Git blob `f8fa694be7d600c8935e0b91ea8ee7da304b777f`, SHA256 `ff14213d944861205f920f6c89af3abfb99ce2f0cc05ac4946a1020675f72815`, 11,090 bytes.
- New composition test: Git blob `9968f25d79037cc7df56b38b1abf953cc3abc74d`, SHA256 `7ada2dee3b56702bad59f0b4011120d65c1dc63eebe5133cdb603c178cbc20c8`, 7,081 bytes.

COMPOSITION: Initial live main was `e99b929c1e3a0c61dcc66c63590212e7118461c8`. Its module was reconstructed exactly as Git blob `47bbaf18bf565ae6c1c80659693655ec5ec43614` before composing only the retained history hunks. Every non-history top-level AST node is identical to that live module; QUOIN's commit-hash guard in the overlapping receipt function is preserved. Source/history-test publication stays with ASTRA-HISTORY-RECOVERY. This consumer must be integrated only with the canonical history dependency present. Exact final-main readback belongs in the PR and Slack completion receipts rather than being asserted before merge.

OWNED PATHS: Only the new composition test and this append-only board receipt. Neither existing validator/test, docket records, schemas, provenance sources, generated projections, other active work, nor legal conclusions are changed. No owner-PC work, provider-account action, paid infrastructure, customer data, deployment, production-docket success, or full-repository/hosted-CI success is claimed.

COORDINATION: Slack `C0BU51F1PL3`, source-owner thread `1788864783.161139`; independent validation `1788866736.341849`, additive path claim `1788866772.468169`. Full unfiltered connector discovery exposed the Git Data and Slack message writers; a shell transport failure was not treated as evidence of connector write failure.
