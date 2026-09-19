# Paid bank-export integration pilot

**Internal commercial proposal, not an accepted order. No customer, invoice, receivable, savings, booked revenue or cash is asserted.**

## Offer

A proposed **USD 4,800 fixed-scope / seven-business-day** pilot for a treasury-software team, ERP implementer, outsourced finance operation or accounting-data integration consultancy that already receives camt.053 exports and needs a repeatable, reviewable mapping. This is a pricing hypothesis for owner review, not a live checkout or binding quote. Work starts only after scope, authorized data handling, prerequisites and acceptance ownership are agreed in writing.

The useful outcome is not another dashboard: one documented bank-export-to-target mapping, a retained-source discrepancy pack, reproducible acceptance tests, and a handoff that the buyer's own finance/integration owner can evaluate before posting anything.

## Included boundary

Up to **two documented bank export profiles**, one target JSON/CSV import contract, one legal entity, and a buyer-selected sample of at most 20 statements / 25,000 total entry rows, with each run inside the tool's documented limits. Profiles must use the supported .02/.08 namespaces. At least one normal, one duplicate/reissue or paging example, and one exception example per profile are needed. Samples may be synthetic or appropriately de-identified, but that evidence class must remain explicit.

Delivery comprises a source/profile inventory; exact version and field map; retained entry/detail/balance lineage; a deterministic read-only target adapter where supported by the agreed target contract; expected-output fixtures; a prioritized exception register; normal and optimized runtime tests; and a runbook plus a recorded operator handoff. Adapter code is **pilot work to be implemented**, not a feature already claimed for this generic package.

Proposed sequence: day 1 profile and sample qualification; days 2–3 mapping and exception semantics; days 4–5 adapter/tests and batch/reversal/page/reissue cases; day 6 buyer review and one bounded correction pass; day 7 acceptance pack and handoff. Missing bank evidence or changed target requirements pauses/re-scopes the schedule rather than forcing unsupported normalization.

## Acceptance evidence

The buyer can rerun the retained fixture corpus and obtain byte-identical normalized output. Every target row must trace to a source statement/entry, and no batch aggregate plus its children may be counted twice. Exact signed amounts/currency/status and reversal semantics must match the agreed examples. Duplicates, unsupported versions, missing balances, partial pages and ambiguous corrections must produce the agreed non-posting exception outcome. No source or target financial system is mutated by the pilot.

Acceptance is a named buyer decision tied to the agreed scope, not a boolean the tool awards itself. A clean synthetic demo is not bank certification or production acceptance.

## Exclusions and owner responsibilities

No payment initiation, credential handling, bank API connection, GL posting, account access, accounting-policy decisions, FX pricing, investment advice, regulatory filing, historical-data cleansing project, support SLA, production hosting or automated cutover. Page assembly, durable import-history/reissue handling, additional bank dialects and target posting require separately scoped work and review.

The buyer supplies authorized exports, facility documentation, the target contract, accounting interpretation and a named integration/finance reviewer. The seller supplies software/data-engineering work and truthful evidence, not a representation of bank or accounting authority. Sensitive data stays on an approved private delivery surface under agreed handling terms.

## Sales qualification, not mass outreach

A qualified opportunity has an identified integration owner, recurring manual statement ingestion or failed export mappings, access to a real bank profile and target contract, and a budget for a bounded pilot. Reject speculative recovery guarantees, requests to hide bank exceptions, or projects where no one owns accounting acceptance.

Before any external contact: recheck the exact organization/domain/recipient and offer across Slack and Gmail, obtain Muse's current single-writer adjudication, and use only the selected route once. This document authorizes no send, contract, payment, or customer-data access. Any eventual customer-facing package must be self-contained on an approved delivery surface and must not link back to internal Commons/GitHub/Slack materials.

A useful first conversation asks which bank-export version, target importer and recurring exception consume the most operator time. The commercial follow-through is a paid mapping/acceptance pilot, not unlimited free debugging or an unsupported savings claim.
