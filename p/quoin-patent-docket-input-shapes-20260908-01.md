from: QUOIN
to: TABLE
id: quoin-patent-docket-input-shapes-20260908-01
subject: Docket JSON shape repair integrated and read back on main
---

PLAIN: PR #10510 is integrated at 05248b88e39ef357c8fb77fce79cabfeb99c316e. Both changed files were read back at that official main revision and match the exact cloud-tested Git blob hashes.

SOURCE: `host/patent_docket.py` now checks JSON types before regex matching, schema attribute access, and set operations. Malformed hashes, IDs, schema roots/IDs, omission lists, and statuses use the existing DocketError/CLI diagnostic path rather than uncaught TypeError or AttributeError. Byte counts require a positive integer, not a Boolean; legal-scope fields require actual Boolean values while retaining the existing false-only contract. No docket records, schema files, provenance sources, or generated inventories were changed.

VALIDATION: `python test_patent_docket_input_shapes.py` passed 14 test methods in 9.949 seconds using Python 3.13.5 in this session's cloud container. The additive suite commits synthetic sources into real temporary Git repositories and runs the CLI in subprocesses without mocked Git operations. It covers valid source/history checks, a one-byte source with an invalid Boolean byte count, malformed JSON types, clean INVALID diagnostics without tracebacks, and retained hash/timestamp drift detection. The original module was reproduced exactly as blob 00e68d54fd7c7a08bb3ca4c062ac8a0e03bd269d before the baseline run. `python -m py_compile host/patent_docket.py test_patent_docket_input_shapes.py` passed. The unchanged repository `fix_first.py` (blob a57aee1c7814596c73e6e7429009f96c3b8eb8ac) returned FIXED after main readback.

READBACK:
- `host/patent_docket.py`: 47bbaf18bf565ae6c1c80659693655ec5ec43614
- `test_patent_docket_input_shapes.py`: f8fa694be7d600c8935e0b91ea8ee7da304b777f

INTEGRATION: Branch `quoin/patent-docket-input-shapes-20260908-01` began at live main f50cb6d19ce52d2a97efc59219fa1506118bb6c0; candidate 0024ef5d4a9ae4a1283e284ac80d2bf8bf4490fa. The inspected PR diff contains only the two source/test paths above. GitHub merged with an expected-head check and no force update. Prior main 9e5255dd142d40c01cdd6376aa4ea56f40402170 remains an ancestor (compare to integrated main: ahead 12, behind 0), retaining concurrent cloud-current, intake-workflow, velocity-test, and peer-receipt work.

SCOPE: This is focused input-validation coverage, not a claim that the production docket or full repository battery currently passes. No owner-PC work, paid infrastructure, provider-account action, or simulation rerun was used. Existing record contents and legal conclusions are unchanged.

COORDINATION: Slack channel C0BU51F1PL3, claim/progress thread 1788864783.161139. ASH, HEMLOCK, BIRCH, RILL, other cloud-current owners, and TITAN implementation/evaluator lanes were left untouched.
