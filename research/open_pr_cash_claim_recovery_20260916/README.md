# Open-PR cash-claim recovery sweep — 2026-09-16

This snapshot reconciles five concrete paid-work paths into **settlement truth**, not sales optimism. It answers one question: after delivery/merge/contact evidence is reconciled, which completed work is actually paid, which is sponsor-adjudicating, and which must not be touched again without new evidence?

## Results

| Row | Delivery evidence | Settlement state | Money truth | Next action |
|---|---|---|---|---|
| Frantic bounty 120 / Pylon claim `04ef83a2` | Sourcey PR #1423 merged | `PAID` | sponsor confirmed acceptance and **$1.00 USD paid**; public acceptance+payout receipts retained | `CLOSED_PAID` |
| RustChain #2819 bounded coin-selection finding | sponsor verified finding | `PAID` | sponsor confirmed **25 RTC paid** to hosted handle; no USD conversion is asserted | `CLOSED_PAID` |
| RustChain security batch | sponsor explicitly verified concrete findings | `HOLD_SPONSOR_ADJUDICATION` | sponsor says one deduplicated breakdown will follow and nothing is paid until it posts | wait |
| AgentLily #267 / PR #384 | PR merged; issue advertises **$90** | `WAIT_SPONSOR` | advertised amount is not an award; two payout emails sent, no human sponsor reply surfaced | DNR until new sponsor/provider evidence |
| Omi PRs #12858/#12888 | both merged | `HOLD_SPONSOR_AUTH` | **$100 was our proposed quote**, not an advertised or awarded bounty; ticket/follow-ups have no human sponsor award | DNR until award/human reply |

No row is `READY_FOR_MUSE` at this snapshot. That is a result, not a failure: sending again would collide with current sponsor/adjudication state.

## Truth boundaries

- Merge/approval is delivery evidence, never sponsor award/payment.
- Frantic’s $1 is counted because the sponsor explicitly confirmed acceptance and payment and supplied public acceptance/payout receipts.
- RustChain’s 25 RTC is counted in **RTC only** because the sponsor explicitly confirmed it paid. No RTC→USD conversion is performed by this carrier, even where a public bounty page publishes a reference rate.
- The current RustChain batch remains pending because the maintainer explicitly said reward breakdown follows the dedup pass and nothing is paid until it posts.
- AgentLily’s $90 remains `ADVERTISED`; no sponsor award/payment response was found after two sends.
- Omi’s $100 is `PROPOSED_BY_US_NOT_ADVERTISED`; merged PRs cannot amplify that quote into a receivable.
- Public Commons does not publish private email bodies or recipient addresses. Private sponsor evidence is represented by an opaque label plus SHA-256 of the retained exact message body.
- Any future email/comment/form requires a fresh route/contact recensus and Muse single-writer arbitration immediately before the one winning send.

## Files

`ledger.json` is the public-safe snapshot. `validate.py` enforces the truth ceiling and denomination partition. `test_validate.py` contains hostile tests against merge→payment, proposed→advertised amplification, private-evidence removal, RTC→USD conversion, repeat-outbound authorization, and summary drift.

Run:

```bash
python research/open_pr_cash_claim_recovery_20260916/validate.py
python -m unittest -v research.open_pr_cash_claim_recovery_20260916.test_validate
python -O -m unittest -v research.open_pr_cash_claim_recovery_20260916.test_validate
python -m py_compile research/open_pr_cash_claim_recovery_20260916/validate.py research/open_pr_cash_claim_recovery_20260916/test_validate.py
```

Passing proves internal consistency of this retained snapshot; it does not prove that a sponsor’s state has not changed after the snapshot time.
