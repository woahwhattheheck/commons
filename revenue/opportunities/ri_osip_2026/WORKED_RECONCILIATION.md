# Worked reconciliation: a discrepancy remains visible

Every party, identifier, record and amount below is fictional. This is an original design example for the proposed read-only workshare. It is not OSIP data, an investment recommendation, a transaction instruction, an accounting opinion, or a finding about any institution.

The supporting solicitation anchors are Section III scope 2 and questionnaire M (printed pp.4 and 10) in the [issued RFP](https://treasury.ri.gov/media/2171/download?language=en). The reconciliation design and acceptance decisions below are proposed by this dossier; the RFP does not prescribe this algorithm.

## Inputs and conservation

For illustration, the prime supplies opening balances, a posted-event export, and closing statements for one agreed period. The file manifest would retain original filenames, byte digests, period, timezone, currency, producer, acquisition time, and schema version. These facts must come from supplied records; the example does not invent actual source digests.

All amounts are USD. Earnings are already-posted input amounts supplied by the fictional prime. This workshare does not calculate a yield or decide how earnings should be allocated.

| Input row | Event ID | Participant | Supplied event kind | Signed posted amount | Import disposition |
|---|---|---|---|---:|---|
| 1 | TX001 | DEMO-A | Contribution | 5,000.00 | Retain once |
| 2 | TX002 | DEMO-A | Withdrawal | -2,500.00 | Retain once |
| 3 | TX003 | DEMO-A | Posted earnings | 10.00 | Retain once |
| 4 | TX004 | DEMO-B | Withdrawal | -1,200.00 | Retain once |
| 5 | TX005 | DEMO-B | Posted earnings | 4.00 | Retain once |
| 6 | TX001 | DEMO-A | Contribution | 5,000.00 | Exact replay of row 1; retain in raw log and exclude second counting |

Record conservation is explicit: six raw rows equal five distinct accepted records plus one linked exact replay. Exclusion from arithmetic never deletes the supplied row. This example assumes the prime has documented the identifier's scope and replay semantics. If either is unknown, the apparent duplicate is unresolved and the batch cannot be called reconciled. A repeated ID with different content is a conflict, not a replay.

## First observation

The proposed calculation is opening balance plus the signed amounts of distinct accepted events. Use exact decimal or integer-cent arithmetic with an agreed currency precision. An omitted opening balance or incomplete period cannot be substituted with zero.

| Participant | Opening | Contributions | Withdrawals | Posted earnings | Derived closing | Supplied closing v1 | Supplied minus derived |
|---|---:|---:|---:|---:|---:|---:|---:|
| DEMO-A | 100,000.00 | 5,000.00 | -2,500.00 | 10.00 | 102,510.00 | 102,510.00 | 0.00 |
| DEMO-B | 40,000.00 | 0.00 | -1,200.00 | 4.00 | 38,804.00 | 38,805.00 | 1.00 |
| Total | 140,000.00 | 5,000.00 | -3,700.00 | 14.00 | 141,314.00 | 141,315.00 | 1.00 |

The arithmetic above was recomputed with Python Decimal during preparation: six input rows, five distinct records, one exact replay; derived closings 102510 and 38804; differences 0 and 1. This verifies the example's arithmetic only. It is not an executed production-control claim.

The first output is **UNRESOLVED_DISCREPANCY**, with a one-dollar exception for DEMO-B. Matching DEMO-A and otherwise consistent source totals do not make the whole period pass. The reviewer can see the raw row locators, the transformation version, the replay decision and the disagreeing statement version.

## Exception and correction record

| Record | Proposed contents |
|---|---|
| Exception EX-001 | DEMO-B; period identifier; source-v1 locator; supplied 38,805.00; derived 38,804.00; difference +1.00; status OPEN; assigned prime reviewer role |
| Question | Is the statement wrong, is an event missing, or do the sources cover different periods? The reconciler does not select an explanation. |
| Correction input | The prime supplies statement v2 with 38,804.00 and identifies which v1 item it supersedes. Both versions remain retained under the agreed retention policy. |
| Recalculation | Same accepted events produce 38,804.00; v2 difference is 0.00; aggregate supplied and derived closings are both 141,314.00. |
| Reviewer decision | Prime reviewer records the correction basis and closes EX-001 with references to both input versions and the rerun output. A matching number alone does not record approval. |

The revised output may say **MATCHED_FOR_SUPPLIED_PERIOD_AND_RECORDS** once the defined completeness checks and reviewer decision are present. It cannot say that all transactions were complete, authorized, current, compliant, or correct in the real world merely because these supplied records reconcile.

## Acceptance cases before real intake

| Variation | Expected observed result |
|---|---|
| Import identical batch again | Same numerical result; replay event linked to original; no duplicate counting. |
| TX001 reappears with another amount | Conflicting identity reported; no automatic precedence rule. |
| DEMO-B absent from closing statements | Missing coverage explicitly listed; no zero statement balance. |
| Source list says two files but only one arrives | Incomplete intake; comparison withheld pending the second file or an approved manifest correction. |
| One row names an unknown participant or currency | Row retained in an exception ledger; counts still reconcile to the raw input count. |
| Period end or timezone differs across sources | Scope mismatch; no silent period join. |
| Supplied corrections change only DEMO-B's statement | Only the superseded source is replaced in the active comparison; prior versions and exception history remain available. |

No result from these proposed checks can post an entry to a production ledger, instruct a bank, alter a participant account, or move funds. The acceptance artifact is an inspectable discrepancy report for the prime's review.
