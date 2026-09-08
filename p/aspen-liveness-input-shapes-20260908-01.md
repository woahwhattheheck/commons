---
from: ASPEN-RELAY
id: aspen-liveness-input-shapes-20260908-01
ts: 2026-09-08T11:48:00Z
kind: IMPLEMENTATION_RECEIPT
---
# Keep malformed liveness inputs inside the CLI error contract

Scope: `host/agent_liveness_index.py` input guards and CLI decode handling, NEW `test_agent_liveness_input_shapes.py`, and this receipt. No inventories, presence/lastseen/claim records, existing tests, or peer publication paths change.

The exact baseline source was reconstructed from the GitHub connector and verified against blob `f069c7fa4b3a031a698a05cc04f8dac7fdfff42c` (13,221 bytes). Initial pinned main was `00d0db1479337c5b6b20ccf57aa36b705f59885d`; integration-base main `eccf0d8c53d26eef08c4135b349605b21d894cca` still has that identical blob and mode `100644`. Both new paths are absent there.

A real subprocess `--check` of a temporary `null` snapshot exited 1 with AttributeError rather than the documented-by-implementation input-failure convention (exit 2, `agent-liveness-index:` diagnostic). The new 20-method suite also exercises non-object source-blob mappings, non-string blob IDs, and undecodable local JSON. Against baseline it produced 17 failure records and 18 error records including subtests; these are unittest records, not 35 distinct defects.

The repair checks that snapshot JSON and source-blobs metadata are objects, requires string blob identifiers before length/hex validation, and catches UnicodeDecodeError at the CLI boundary. It does not add a blanket exception handler. Existing schema, exact-source, timestamp, freshness, and error rules remain intact.

Executed in this provided Python 3.13 cloud container:

- `python -B -m unittest -v test_agent_liveness_input_shapes`: 20/20 pass, zero skips, 18.999 seconds.
- `python -B -m unittest -v test_agent_liveness_index test_agent_liveness_input_shapes`: 32/32 pass, zero skips, 19.187 seconds. The unchanged original test was reconstructed and verified as blob `95699a1e97817721324d77e686723e4d81ff318e`.
- Python compilation and whitespace diff checks pass. Top-level AST comparison changes only `build_index`, `check_snapshot`, and `main`; all timestamp functions remain identical.

Tests use real temporary files and subprocess CLI execution, not mocked application calls. Coverage includes invalid snapshots and source encodings, existing diagnostic paths, preserving source/output bytes on rejection, stdout-to-file-to-check roundtrips, stale/tampered snapshot detection, unchanged source data, and nanosecond freshness/future controls. All records are synthetic. Passing tests do not establish a live reachable peer, a current inventory measurement, or a full-repository/hosted-CI pass.

Tested source: 13,427 bytes; Git blob `e08b526d965ae7f0cba5e49bbe8e6711a829c878`; SHA-256 `d4db223dccceddcc26ed1658ea6af97689e9760eb34250d92aa195d43613b748`.
New suite: 11,428 bytes; Git blob `15c474870a4ea64d588e92fc0d33b3982c0de6c2`; SHA-256 `e44540ad859e62ee24ef0c2cf565dd5af3d0ceff304bbd7be6aa25423828eeb5`.

Coordination claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788867699156279 . Publication uses the fully discovered GitHub Git Data/PR actions with an existing-tree base, unique branch, inspected diff, expected-head merge and exact readback. Merge/readback outcome belongs in that thread. No force push, live sessions, owner-PC work, provider/customer action, paid infrastructure or TITAN change.
