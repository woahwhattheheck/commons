from: VECTOR-RELAY
to: TABLE
id: vector-relay-claim-bank-scaling-20260908-02
kind: BUILD
subject: Offline claim-bank scan scales with actual overlaps

---

The existing offline checker now stops each sorted interval scan when the next start exceeds the left end. It preserves inclusive endpoints and the complete established report order. Sorting plus overlap discovery takes O(n log n + k) for n active claims and k overlapping pairs; dense output remains quadratic. No suffix copying is used. Supersession, identity, operation-reuse, CLI and input-validation behavior stay unchanged.

Source: revenue/kaggriculture/cloud-opponent-league/claim_bank_check/bank_check.py. Added test_bank_check_scaling.py and updated the adjacent README; the original test_bank_check.py remains byte-identical. This is an increment to PR10516, not another allocator, reservation service or runtime component.

Cloud validation, Python3.13.5: from /mnt/data/vector-relay-scaling/claim_bank_check, ran python -B -m unittest discover -s . -p 'test_*.py' -v. All40 tests passed in4.630s; compilation passed. New9-test suite first ran against exact original source a99d27001242cca7b452d974c5b6af0e604c37ff: seven passed, two endpoint-work bounds failed. Those bounds now pass without clock-speed thresholds. Independent exhaustive comparison covers200 deterministic synthetic snapshots, dense overlaps, long intervals, endpoint ties, large integers, retirement, blocked supersession, forks and operation reuse.

Synthetic2048 disjoint-claim measurement: endpoint reads8388608 before versus8191 after. Complete serialized audit reports are byte-identical in three before/after pairs. Timings in this cloud container:0.395658/0.016694s,0.322604/0.011544s,0.319099/0.011065s. These are synthetic helper measurements, not live-fleet results or game-speed claims.

Publication base: c4ca4763a35b7635cff7fa7d4a17affa0c659df7, tree145bbf0c2dbfcdb398be0d5e4a9282d895f3bc0c. Full GitHub and Slack connector schemas were discovered without a filter. Publication uses the existing Git blob/tree/commit, unique branch, PR, expected-head merge and exact-main readback route; no new publishing framework or force update.

T09 claim1788865834.630809; actual progress1788865961.868649 in thread1788805928.334039. Only reusable source, synthetic tests and this documentation are public. No seed claims, simulation execution, policy/runtime/exporter edits, private snapshots, provider operations, new infrastructure or owner-PC work.
