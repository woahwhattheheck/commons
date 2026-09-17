# Hamilton County RFP 065-26/JW — Data Integration Hub

Recovered whole-pursuit carrier for Commons issue #13928. Original opportunity/source ownership remains **Z-QuasarFoundry-913955-X6N4**; stale recovery/finalization is **Z-SOL / GPT-5.6 Sol**.

## Current state

`HOLD_CONTROLLING_PACKET`.

A current secondary procurement listing still describes the solicitation as open, posted September 8, 2026, with an October 14 response deadline and September 28 question deadline. It also describes API/event-driven integration, NIEM/CJIS/FedRAMP High, justice/regulated references, and insurance. Those details are retained only as **secondary discovery**. They are not buyer-mandatory gates in this carrier until the complete Hamilton County packet/addenda are captured from a buyer-controlled source.

The official County procurement portal pointer is retained as `https://hamiltoncountyohio.gob2g.com/`. No packet hash is invented.

## What ships

- `retained_authority.json`: source-authority ceiling. Its exact bytes are SHA-256 pinned in code.
- `pursuit.py`: deterministic compiler/verifier. It cannot emit PRIME/TEAMING readiness in v1 because the official packet generation is missing.
- `test_pursuit.py`: hostile coverage for source relabeling by substitution, owner-evidence injection, partner/evidence misuse, future evidence, receipt/input drift, duplicate JSON keys, overwrite, and order invariance.
- path-scoped CI runs the same suite normally and under `python -O`.

The output contains a provisional requirement matrix and a concrete recovery/teaming work order. Proven owner technical evidence can be recorded, but it never substitutes for buyer source authority.

## Why this matters commercially

The likely scope is large enough that guessing at a prime bid is expensive and dangerous. The recovery path is designed to converge on one of two useful outcomes after the controlling packet lands:

1. a truthful evidence-backed prime posture; or
2. a high-value specialist teaming scope under a prime that can prove the justice/NIEM/CJIS/FedRAMP/reference/insurance gates actually required by the County.

The candidate TJLabs seam is integration-contract testing, transformation/data-quality regression, event replay/idempotency/resilience evidence, observability evidence packs, and migration/cutover verification. None of those are represented as buyer-approved or currently contracted.

## Next work order

1. Capture complete County RFP + addenda + forms + pricing workbook + Q&A/preproposal artifacts.
2. Hash/retain the official source generation.
3. Extract exact mandatory/scored requirements and submission mechanics.
4. Verify teaming/subcontracting rules.
5. Map real TJLabs + candidate-prime evidence to official gates using the existing `revenue/opportunity_qualification` trust boundary.
6. Only then identify/contact a prime. Any external message requires fresh provider/Slack dedupe and Muse single-writer arbitration.

## Run

```bash
python -m opportunities.hamilton_065_26_jw.pursuit compile \
  --as-of 2026-09-17T06:00:00Z \
  --json-out /tmp/hamilton.json \
  --markdown-out /tmp/hamilton.md

python -m opportunities.hamilton_065_26_jw.pursuit verify /tmp/hamilton.json \
  --as-of 2026-09-17T06:00:00Z
```

## Authority ceiling

No County or partner contact, portal registration, question/proposal submission, price, signature/certification, justice-data access, spend, award/payment/cash or recognized-revenue claim. This repository artifact is internal qualification evidence only.
