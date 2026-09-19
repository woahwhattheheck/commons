# Milestone packet completeness report

> SYNTHETIC / FICTION - not a University of Iowa record

Engagement: SYNTHETIC assessment engagement (fictional) - milestone packet fixture (ENG-SYN-18649)
As of: 2026-11-25
Contract total: $24,000.00 (2400000 cents)
Milestone amounts total: $24,000.00 (2400000 cents)

**Overall: FAIL** - 3 error(s), 2 warning(s)

| Milestone | Kind | Amount | Submitted | Acceptance | Billing | Status | Errors | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M-1 | KICKOFF | $4,800.00 | DELIVERED | ACCEPTED_RECORDED | DRAFT_NOT_ISSUED | READY_TO_SUBMIT_AS_DRAFT | 0 | 0 |
| M-2 | DRAFT_DELIVERY | $9,600.00 | DELIVERED | PENDING | DRAFT_NOT_ISSUED | READY_TO_SUBMIT_AS_DRAFT | 0 | 1 |
| M-3 | FINAL_ACCEPTANCE | $9,600.00 | NOT_SUBMITTED | NOT_REQUESTED | DRAFT_NOT_ISSUED | NOT_READY | 3 | 1 |

## Engagement-level findings

- `INFO` **I_AMOUNTS_CONFIRMED** - milestone amounts sum to $24,000.00 exactly (2400000 cents), checked in integer cents

## M-1 - Kickoff and engagement plan

- `INFO` **I_ACCEPTANCE_ON_RECORD** - acceptance recorded 2026-10-09 by Fictional client project sponsor (SYNTHETIC) (ref SYN-ACK-M1-0001)

## M-2 - Draft assessment delivery

- `WARN` **W_DEPENDENCY_OVERDUE** - DEP-M2-01: IAM deployment log export outstanding; the IAM deployment cell stays UNKNOWN until it arrives - 15 day(s) past the needed-by date (needed by 2026-11-10, as of 2026-11-25)
- `INFO` **I_ACCEPTANCE_PENDING** - delivered; no acceptance record supplied, so acceptance is PENDING. Delivery is not acceptance.

## M-3 - Final report and acceptance

- `ERROR` **E_ARTIFACT_DOES_NOT_OPEN** [IDX-M3-002] - final/appendix-evidence-v1.0.csv: UNRESOLVED_MISSING - no file at the cited path; the citation cannot be verified
- `ERROR` **E_VERSION_NOT_IDENTIFIABLE** [IDX-M3-003] - final/readout-deck-outline.md: opened (sha256 cd71874c4779...) but declared_version is UNKNOWN, so the delivered version cannot be named
- `ERROR` **E_MISSING_DISPOSITION** [IDX-M3-003] - IDX-M3-003: no disposition decision recorded. The item is not assigned a default; a person must decide retain / return / destroy / client-system.
- `WARN` **W_DEPENDENCY_UNDATED** - DEP-M3-01: Client confirmation of the accessibility review scope for the final report - open with no agreed date; it cannot be called on time or late

## What this report does and does not say

- `READY_TO_SUBMIT_AS_DRAFT` means the packet has no unverifiable citation and no unmade disposition decision. It is not an approval, an acceptance, or a billing authorization.
- An `UNKNOWN` field is reported as UNKNOWN. It is never defaulted, zeroed, or counted as satisfied.
- A cited artifact that did not open is an ERROR. It is never represented as delivered.

