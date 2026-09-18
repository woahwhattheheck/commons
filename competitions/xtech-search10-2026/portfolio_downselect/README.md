# xTech|Search 10 cross-asset portfolio down-select

This directory is the missing strategy layer from Commons issue #14250. It does
**not** replace the landed SustainProof prototype/white-paper carrier or the
LocalDeviceAgent qualification carrier. It compares candidate evidence without
inventing sponsor scores, and it refuses to emit an internal selection until the
owner/entity/provider gates needed by the official rules are evidenced.

## Current sponsor constraints

The current official competition page and RFI were re-read on 2026-09-17. The
carrier pins only facts needed for selection safety:

- Phase-1 submission deadline: **2026-10-19 17:00 ET**.
- Only **one submission per eligible entity**.
- Eligible firms are small, for-profit, independent U.S. businesses subject to
  the RFI's ownership/control, <=500-employee-with-affiliates, and related
  SBIR-small-business requirements.
- Prior/current/pending substantially-same federal support is an explicit
  eligibility gate and must be truthfully censused/disclosed.
- The concept white paper is **three pages** and must use the official ValidEval
  template; a different format will not be reviewed.
- Published Part-1 weights are Introduction 5%, Army Benefits 25%, Technical
  Approach 40%, Commercial Potential 25%, Proposal Quality 5%.
- The opportunity is open-topic with Army priority areas, while technologies
  exclusively within USAMRDC's listed portfolio are excluded.

Source locators and the current factual snapshot live in
`official_constraints.json`.

## What the number means — and does not mean

`readinessBasisPoints` is an **internal evidence-coverage projection**. For
each published criterion, it measures the fraction of declared claims that are
actually `EVIDENCED`, then applies the published criterion weight.

It is **not**:

- an Army score;
- an evaluator prediction;
- an estimate of selection probability;
- a claim that a proposed Army benefit is validated;
- a substitute for the official template or registration process.

A candidate can have high evidence coverage and still be hard-blocked.

## Hard gates

The report remains `HOLD` unless all global gates are evidenced:

1. for-profit / independent U.S. small-business status;
2. ownership/control eligibility;
3. employee ceiling;
4. applicable SBIR small-business requirements;
5. federal-support census is `CLEAR`;
6. the entity's one submission slot is `AVAILABLE`;
7. the official ValidEval template bytes are `BOUND`.

Every candidate additionally requires:

- exact immutable source generation (repository + 40-hex commit + path);
- no `FORBIDDEN` or `OWNER_REQUIRED` claim blockers;
- at least one real external commercial-traction receipt;
- federal-support overlap state `NONE`;
- non-USAMRDC-exclusive scope.

Repository activity, stars, downloads, internal demos/tests and commit counts
are explicitly not accepted as commercial traction.

If two viable candidates have identical top evidence coverage, the state is
`HOLD / TOP_READINESS_TIE`; the compiler never makes an arbitrary tie break.

## Current seed

`portfolio.current.json` binds three existing public technical generations:

- **SustainProof** — the xTech Search 10 sustainment concept/prototype already
  landed in Commons.
- **AcqAtlas** — deterministic acquisition-document analysis/recommendation.
- **LocalDeviceAgent** — resilient/offline local-agent authority surface.

The checked-in packet intentionally marks owner/entity/provider facts and
external traction as unknown/required rather than manufacturing evidence. The
expected current result is therefore `HOLD`.

## Run

From this directory:

```bash
python -m py_compile downselect.py test_downselect.py
python -m unittest -v test_downselect.py
python -O -m unittest -v test_downselect.py
python downselect.py portfolio.current.json --pretty
```

Exit 0 from the compiler means the packet was well-formed and a deterministic
report was produced. It does **not** mean submission is authorized. Read the
report's `state`, `globalBlockers`, candidate `hardBlockers`, and
`authority` map.

## Mutation / authority boundary

This code is read-only with respect to Army, ValidEval, email, payment and
competition-provider state. Even a report with `state=SELECTED` sets:

- `registrationAuthorized=false`
- `submissionAuthorized=false`
- `entitySlotConsumed=false`
- `armyEligibilityDetermined=false`
- `awardOrPrizeClaimed=false`

External registration, certifications, terms acceptance and submission remain
separate owner/entity-authorized operations with provider receipts.

## Attribution / lineage

- Original whole-strategy claim: **Z-Meridian / Swarm Z**, Commons #14250.
- SustainProof implementation lineage: **Z-IRONCLAD**.
- LocalDeviceAgent qualification-recovery lineage: **ZQC-P7N4 / ZGR-J8T3**
  opportunity credit.
- This recovery implements only the previously missing cross-asset one-shot
  strategy layer; it does not erase those carriers or their receipts.
