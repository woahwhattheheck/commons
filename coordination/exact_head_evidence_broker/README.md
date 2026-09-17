# Exact-head evidence broker

This is an **offline diagnostic compiler**, not a merge bot. It turns a retained repository/PR provider snapshot into one deterministic receipt that makes the swarm's finalization evidence explicit.

A packet binds the repository and PR, desired candidate head, provider-current PR head, construction base, literal current-main SHA, PR paths, main-since-base paths, required workflow runs, reviews, mergeability, critical Git blob identities, and snapshot validity window.

A diagnostic GREEN requires all of the following in the supplied snapshot: candidate head still equals provider-current head; snapshot current; every declared critical blob unchanged; no PR/main path overlap; every required exact-head workflow present exactly once and `completed/success`; at least one independent exact-head GREEN and no exact-head STOP; and literal provider mergeability `true`. Ancestor-head GREENs are counted as stale diagnostics and never satisfy the current-head review requirement. Queued/pending/in-progress/missing CI is UNKNOWN, not success.

`current_main_sha` is inside the packet digest, so a main move creates a new evidence generation. A receipt for the old main cannot verify against a refreshed packet even when paths remain disjoint.

The compiler validates and reasons over the **retained snapshot it is given**. It does not contact GitHub/Slack, authenticate that a collector fetched every provider fact, or infer facts absent from the packet. A GREEN receipt therefore means only “this retained packet satisfies the declared diagnostic contract,” never “merge is authorized.” Collectors/finalizers remain responsible for obtaining a complete fresh provider snapshot.

Every receipt hard-codes false authority for merge/ref/source/provider mutation, workflow rerun/cancel, review submission, outbound/Muse, contracts, invoicing, payment/funds movement, cash/revenue, and tax/accounting conclusions.

## CLI

```bash
python -m coordination.exact_head_evidence_broker compile snapshot.json --out receipt.json
python -m coordination.exact_head_evidence_broker verify-integrity snapshot.json receipt.json
python -m coordination.exact_head_evidence_broker verify-current snapshot.json receipt.json
```

Compile output is create-exclusive.
