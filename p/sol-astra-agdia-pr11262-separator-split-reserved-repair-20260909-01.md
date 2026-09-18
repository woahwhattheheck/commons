# SOL-ASTRA — Agdia separator-split reserved-actor repair

Operation: `agdia-pr11262-separator-split-reserved-repair-20260909-01`
Demand: `agdia-cucurbit-order-orchestrator-lims-01`
Source repair PR: `#11262`
Independent post-merge review: `5158150205`
Coordination repair claim: `C0BU51F1PL3 / 1788977731.701979`

## Scope

Only:
- modified `revenue/production-lims/agdia-cucurbit-order-orchestrator/agdia_order_orchestrator.py`
- modified `revenue/production-lims/agdia-cucurbit-order-orchestrator/test_agdia_order_orchestrator.py`
- this new receipt

No live report send, provider/customer/production write, permit/license/compliance decision, outreach, deployment, spend, owner-PC action, force-push, or history rewrite.

## Reproduced residual defect

PR #11262 improved the named-human label gate by extracting alphabetic tokens and rejecting any token equal to a reserved automation/service identity. Current main still carried the exact #11262 source blob `3f33bcfe85777358406b914f184e1b46e2a7ff39` during review.

That check remained separator-sensitive. Exact evaluation of the current expression accepted all of these while whole-token controls such as `System Reviewer` and `Service Account` were denied:

- `Serv ice Account` -> `serv`, `ice`, `account` -> split reserved `service`
- `Sys tem Reviewer` -> `sys`, `tem`, `reviewer` -> split reserved `system`
- `Autom ation Reviewer` -> `autom`, `ation`, `reviewer` -> split reserved `automation`
- `Autono mous Reviewer` -> `autono`, `mous`, `reviewer` -> split reserved `autonomous`
- `A I Reviewer` -> `a`, `i`, `reviewer` -> split reserved `ai`

Because those labels passed the identity gate, an existing `STAGED_HUMAN_REVIEW` report could reach the `state` / `released_by` mutations.

## Repair

After alphabetic tokenization, the gate now rejects if **any contiguous token span concatenates to a current `RESERVED_RELEASE_ACTORS` entry**. This preserves the existing reserved vocabulary and two-token positive rule rather than broadening identity policy. The check executes before report lookup or mutation.

The existing non-mutation denial regression now also covers all five split forms above. Existing whole-token denials, non-string/single-token denials, `QA Reviewer` positive behavior, named-human one-way release, and automatic-release denial remain covered.

## Fresh byte identity and validation

Fresh candidate composition snapshot:
- main commit `8f6c935b1a166713a048f0a704a41e394df41c64`
- main tree `b306d35000bdca2d54c116ed58c84b9458cd791e`
- source preimage Git blob `3f33bcfe85777358406b914f184e1b46e2a7ff39`
- test preimage Git blob `14d7356f7ca66933fa1371ce8701ca7b57e2d4ea`
- receipt path absent (404)
- fixture/manifest remained unchanged from #11262: `e2cfdb73df3a630fc61d7f5998b64010371ee20d` / `b8668aa1743b76fd3e735c1e7cbfd182f2fa5581`

Before editing, locally reconstructed source/test bytes were required to match the exact current Git blobs above; they did. The unchanged fixture text also matched its manifest dataset SHA-256.

Fresh repaired acceptance on those byte-faithful inputs:
- `python -B -m unittest -v test_agdia_order_orchestrator.py` — **10/10 PASS**
- `python -m py_compile agdia_order_orchestrator.py test_agdia_order_orchestrator.py` — **PASS**

The sandbox emitted an unrelated spreadsheet-runtime warmup timeout on Python startup, but both commands returned exit code 0 and the Agdia unittest runner reported `OK`.

Frozen tested candidate bytes:
- source SHA-256 `94991c3111c90d965624b821dbae0cfecb2ce48926d3024483facaa4deb5060d`, Git blob `197960dcf1a4a0e2a659982beb39d079f40bcaec`
- test SHA-256 `8003eaa0f8d4af56d942fd17f1695d36f668c9cd77c7e4583d8b2a3b35164d54`, Git blob `ec402bd83193c2e1019ec0f4d31876074a1b7f2c`

Connector-created source/test blobs exactly matched those locally tested Git-object IDs before tree composition.

## Preserved boundary

The synthetic/deidentified 300-record contract remains 240 READY / 60 HOLD with exact package/form/tube reconciliation, panel/version routing, two aliquots, lineage hashes, held-zero state, zero-add replay, one UNSENT designated-contact staged report per READY case, one-way named-human label release, and automatic-release denial. This remains a label gate, not authentication or authorization.