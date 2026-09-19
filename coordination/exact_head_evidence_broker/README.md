# Exact-head evidence broker

This is an **offline diagnostic compiler**, not a merge bot. It turns a retained repository/PR provider snapshot into one deterministic receipt that makes the swarm's finalization evidence explicit.

A packet binds the repository and PR, desired candidate head, provider-current PR head, construction base, literal current-main SHA, PR paths, main-since-base paths, required workflow runs, reviews, mergeability, critical Git blob identities, and snapshot validity window.

`READY_FOR_HUMAN_FINALIZATION_REVIEW` requires all of the following in the supplied snapshot: candidate head still equals provider-current head; snapshot current; every declared critical blob unchanged; no PR/main path overlap; every required exact-head workflow present exactly once and `completed/success`; at least one packet row that *claims* a distinct exact-head GREEN reviewer and no exact-head STOP row; and literal provider mergeability `true`. This is retained-packet self-consistency only. It is not a claim that the owner identity, reviewer identity, review verdict, or provider census was authenticated. Ancestor-head review rows are counted as stale diagnostics and never satisfy the current-head claimed-review requirement. Queued/pending/in-progress/missing CI is UNKNOWN, not success.

`current_main_sha` is inside the packet digest, so a main move creates a new evidence generation. A receipt for the old main cannot verify against a refreshed packet even when paths remain disjoint.

The compiler validates and reasons over the **retained snapshot it is given**. It does not contact GitHub/Slack, authenticate that a collector fetched every provider fact, authenticate the packet's owner/reviewer identities or review verdicts, or infer facts absent from the packet. Every receipt therefore carries four source-literal false provenance facts: `provider_snapshot_complete=false`, `owner_identity_authenticated_here=false`, `reviewer_identity_authenticated_here=false`, and `review_verdict_authenticated_here=false`. Packet string inequality is reported only as a *claimed distinct reviewer*, never authenticated independence. `READY_FOR_HUMAN_FINALIZATION_REVIEW` means only “this unauthenticated retained packet satisfies the declared diagnostic consistency gates and now needs a human/provider-authenticated finalization review.” Collectors/finalizers remain responsible for obtaining a complete fresh provider snapshot and authenticating review provenance.

Every receipt hard-codes false authority for merge/ref/source/provider mutation, workflow rerun/cancel, review submission, outbound/Muse, contracts, invoicing, payment/funds movement, cash/revenue, and tax/accounting conclusions.

## CLI

```bash
python -m coordination.exact_head_evidence_broker compile snapshot.json --out receipt.json
python -m coordination.exact_head_evidence_broker verify-integrity snapshot.json receipt.json
python -m coordination.exact_head_evidence_broker verify-current snapshot.json receipt.json
```

Compile output is create-exclusive.
