# Alcorn State RFP #5588 qualification carrier

Deterministic internal qualification for the live **AI Proficiency Labs** opportunity. This directory intentionally does **not** contain the buyer PDF. It binds the exact buyer-issued attachment by digest and exposes normalized, testable gates only.

## Source binding

- Gmail message: `1a0a0186cbd89b53`
- buyer filename: `RFP#5588 NVIDIA v3.pdf`
- pages: `41`
- SHA-256: `107f0cc3ae880e4000ad89f0d6db6ad4908600afcdafcaf8d66ff4303170f688`
- proposal deadline: `2026-09-21T14:00:00-05:00`

The exact received file was visually inspected page-by-page and text-extracted. Its response checklist names Section VIII Cost Information and Section IX References, while Section VII 2.1.2 relies on an Item 12 Requirements Matrix. The received packet contains Sections I–VII and then jumps from Section VII item 7 to Exhibit A. `qualification.py` therefore fails closed while any of those three buyer-controlled artifacts remains missing.

## What the engine proves

`qualification.py` checks the exact packet identity, deadline, buyer-artifact completeness, current NVIDIA authorization scope, source-bound AI-infrastructure rollout history, callable reference-site evidence, operational submission gates, and—on a team route—an explicit current partner commitment plus a bounded TJLabs support scope. Public evidence IDs are pointers; do not place TINs, private addresses, credentials, or confidential buyer/partner material in this repository.

A `PRIME_READY` or `TEAMING_READY` result is **internal qualification only**. Every external authority field remains `false`; the engine cannot authorize buyer/partner contact, pricing release, signature, certification, submission, contract acceptance, payment mutation, award, cash, or revenue recognition.

## Run

```bash
python commercial/alcorn-rfp-5588/qualification.py \
  commercial/alcorn-rfp-5588/current_evidence.json
python -O commercial/alcorn-rfp-5588/qualification.py \
  commercial/alcorn-rfp-5588/current_evidence.json
python -m unittest commercial/alcorn-rfp-5588/test_qualification.py -v
python -O -m unittest commercial/alcorn-rfp-5588/test_qualification.py -v
```

The committed `current_evidence.json` is intentionally conservative and must evaluate `HOLD`. It records the live gap rather than pretending an unconfirmed target is a partner.

## Updating evidence

Only change `MISSING_BUYER_ARTIFACT` to `PRESENT_SOURCE_BOUND` when the corresponding Section VIII, Section IX, or Item 12 matrix is received from a buyer-controlled source or official amendment and has a bound SHA-256/evidence ID. Only populate NVIDIA authority from verifiable partner evidence with effective/expiry dates and scope. A prospect, target, directory listing, or self-assertion is not a commitment.
