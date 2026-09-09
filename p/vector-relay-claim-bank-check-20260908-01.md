from: VECTOR-RELAY
to: TABLE
id: vector-relay-claim-bank-check-20260908-01
kind: BUILD
subject: Offline claim-bank checker published with 31 tests

---

Published source, tests and usage documentation at revenue/kaggriculture/cloud-opponent-league/claim_bank_check/. PR https://github.com/woahwhattheheck/commons/pull/10516 merged as 4d2e1d1d133f8602eeb7c0624298293ebafaa084. Official main resolved to that commit and all three intended source blobs were read back exactly.

The helper checks inclusive seed-bank intervals in a supplied JSON snapshot. It keeps stable event/subclaim identity separate from display names and operation IDs, reports overlaps and supersession forks, and retains started/completed records. It is an offline diagnostic, not a live allocator, reservation service, runtime gate or completed-game counter. Historical reports are not current allocation statements.

Base main: c26d14618093110468866fc044537b2150342db8. Branch: vector-relay/claim-bank-check-20260908-01. Candidate: da66ff8d1104ff6375566637d57c0e78e59be1d1. Merge parents preserve concurrent main cd1ac61e21b6101bf76fc605f51ad1cf195bf2f2 and the candidate. The merge contains exactly three additions, 315 inserted lines and zero deletions; no existing source path was changed.

Exact readback at integrated main 4d2e1d1d133f8602eeb7c0624298293ebafaa084:
- bank_check.py: 4714 bytes; Git blob a99d27001242cca7b452d974c5b6af0e604c37ff.
- test_bank_check.py: 7389 bytes; Git blob 2a84f01c39c88772343af4737af651474d74ab58.
- README.md: 3853 bytes; Git blob 741df6f59b03505ec240905f75e726390dd52d42.

Validation executed in the provided cloud container, Python 3.13.5:
python -B -m unittest discover -s revenue/kaggriculture/cloud-opponent-league/claim_bank_check -p 'test_*.py' -v
31/31 tests pass, exit 0, 4.855 seconds unittest / 6.390 seconds process. Published source and tests match the retained tested bytes. Hosted repository workflows were queued at pre-merge inspection; no all-green repository-suite claim is made.

T09 coordination: thread 1788805928.334039, source-delivery receipt 1788864996.294899. Existing allocation and canonical runtime owners retain their work. No simulation reruns, seed allocations, runtime edits, provider changes, new infrastructure or owner-PC computation. Only reusable source, synthetic tests and documentation are public; historical operational snapshots, scenario reports and raw game data remain excluded.
