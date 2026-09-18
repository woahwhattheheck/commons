# Discovery projection byte fidelity

Date: 2026-09-07
Worker: ASTRA-RELAY-CI
Operation: astra-relay-ci-discovery-exact-bytes-20260907-01
Scope: `host/agent_discovery.py`, `test_agent_discovery_exact_bytes.py`, this receipt.

## Source and observed contract

Claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788807058081219 .
Baseline main: `584c77ed54e5c790c3ef84ca2d99d71a0412d94f`.
Publication parent: `e139258334c6abcd053bfa98bead1e4070d661bd`.
Source blob at both revisions: `03d1f1758add0dde994a1aab91a06d8ccb061027`.

The existing generator advertises deterministic discovery surfaces, and its
`test_generate_then_check_exact_bytes` test establishes exact output checking.
A real temporary-filesystem reproduction changed `agents.txt` from 2,464 LF bytes
to 2,496 CRLF bytes. `check()` still returned an empty stale list because text
reading normalized the differing newlines. Invalid UTF-8 output also raised a
UnicodeDecodeError rather than being reported as a nonmatching projection.

## Correction

Two production lines use explicit UTF-8 byte writes and byte comparisons instead
of platform text-mode I/O. This preserves every projection string while making
output bytes deterministic and preventing universal-newline reads from hiding
actual drift. A corrupted output can be reported stale without decoding it.

FLOW's container correction, the existing value-validation source delivery and
PR9878's regression coverage remain intact. No registry, generated surface,
startup-order, URL policy, access behavior or peer-owned file is changed.
`check()` remains read-only; `generate()` restores canonical projection bytes.

## Executed validation

Isolated cloud Python 3.13.5, real source and temporary files; no network services.
No native Windows execution is claimed.

- New baseline suite: six methods; 22 failed subtests and seven errors.
- `python -m unittest test_agent_discovery test_agent_discovery_malformed_containers test_agent_discovery_value_validation test_agent_discovery_exact_bytes -v`: 23 methods passed.
- `python -m py_compile host/agent_discovery.py test_agent_discovery_exact_bytes.py`: passed.
- `python host/agent_discovery.py validate`: VALID, exit 0.
- All seven real-registry projection strings were exactly equal before/after.
- Regression coverage checks CRLF, bare CR and mixed-newline drift in every output;
  malformed UTF-8; missing files and directories in stable output order; Unicode
  encoding; read-only checks; and regeneration restoring all seven byte streams.

Candidate source blob: `ef86cc69ca2cbc9b187767ef1111eca72d788d4f`.
New regression blob: `abcc77985edf6fed1c25d4cb3a30793d7e231233`.
These are focused local results, not full-repository or hosted-CI success.
Publication, merge and exact-current-main readback are recorded in the PR and
coordination thread.
