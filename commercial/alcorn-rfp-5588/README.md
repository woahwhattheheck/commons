# Alcorn State RFP #5588 qualification carrier

Deterministic internal qualification for the live **AI Proficiency Labs** opportunity. This directory intentionally does **not** contain the buyer PDF or buyer addendum. It binds exact buyer-issued files by digest and exposes normalized, testable gates only.

## Source binding

Primary packet:

- Gmail message: `1a0a0186cbd89b53`
- buyer filename: `RFP#5588 NVIDIA v3.pdf`
- pages: `41`
- SHA-256: `107f0cc3ae880e4000ad89f0d6db6ad4908600afcdafcaf8d66ff4303170f688`
- proposal deadline: `2026-09-21T14:00:00-05:00`

Buyer Addendum #1:

- Gmail message: `1a0a703662d0e19f`
- buyer filename: `Addendum1 RFP5588.docx`
- document date: `2026-09-10`
- received: `2026-09-15T21:40:09+00:00`
- SHA-256: `82a26f82092e9de91f3e10f985bf9811983f122127fb15d35c9b2f746da72886`
- normalized effect: `PROPOSAL_STRUCTURE_DISCRETION_MINIMUM_SPEC_FLOOR`

The exact received 41-page RFP was visually inspected page-by-page and text-extracted. Its response checklist names Section VIII Cost Information and Section IX References, while Section VII 2.1.2 relies on an Item 12 Requirements Matrix. The received packet contains Sections I–VII and then jumps from Section VII item 7 to Exhibit A. `qualification.py` therefore fails closed while any of those three buyer-controlled artifacts remains missing.

Addendum #1 asked whether a consulting prime could propose disclosed hardware, software, or lab-delivery partners with responsibilities attributed. Alcorn reiterated that the requested equipment must meet the RFP minimum specifications and stated that each prospective vendor may submit a proposal in the manner it feels appropriately addresses the RFP. The carrier therefore records **proposal-structure discretion with the minimum-specification floor unchanged**. It does not invent a separate buyer-permission gate, and it does not treat the addendum as NVIDIA/OEM authority, partner credential inheritance, buyer acceptance, or waiver of any underlying requirement.

## What the engine proves

`qualification.py` is the lower-level evidence evaluator. It checks the exact packet identity, deadline, buyer-artifact completeness, current NVIDIA authorization scope, source-bound AI-infrastructure rollout history, callable reference-site evidence, operational submission gates, and—on a team route—an explicit current partner commitment plus a bounded TJLabs support scope.

`qualification_guarded.py` is the **canonical entrypoint**. It first source-binds Addendum #1 (message ID, filename, digest, document date, receive time, topic, and normalized effect), runs the lower-level evaluator, then attaches the bounded buyer-source finding without adding or removing substantive qualification gates. Public evidence IDs are pointers; do not place TINs, private addresses, credentials, or confidential buyer/partner material in this repository.

A `PRIME_READY` or `TEAMING_READY` result is **internal qualification only**. Every external authority field remains `false`; the engine cannot authorize buyer/partner contact, pricing release, signature, certification, submission, contract acceptance, payment mutation, award, cash, or revenue recognition.

## Run

```bash
python commercial/alcorn-rfp-5588/qualification_guarded.py \
  commercial/alcorn-rfp-5588/current_evidence.json
python -O commercial/alcorn-rfp-5588/qualification_guarded.py \
  commercial/alcorn-rfp-5588/current_evidence.json
python -m unittest commercial/alcorn-rfp-5588/test_qualification.py -v
python -O -m unittest commercial/alcorn-rfp-5588/test_qualification.py -v
python -m unittest commercial/alcorn-rfp-5588/test_addendum_guard.py -v
python -O -m unittest commercial/alcorn-rfp-5588/test_addendum_guard.py -v
```

The committed `current_evidence.json` is intentionally conservative and must evaluate `HOLD`. It records Addendum #1 as reviewed from an exact Gmail message+SHA source while preserving the three missing buyer artifacts and all still-unproven NVIDIA, reference, insurance, pricing, signature, logistics, training, warranty, and TJLabs commitment gates.

## Updating evidence

Only change `MISSING_BUYER_ARTIFACT` to `PRESENT_SOURCE_BOUND` when the corresponding Section VIII, Section IX, or Item 12 matrix is received from a buyer-controlled source or official amendment and has a bound SHA-256/evidence ID. Only populate NVIDIA authority from verifiable partner evidence with effective/expiry dates and scope. A prospect, target, directory listing, or self-assertion is not a commitment.

Do not rewrite Addendum #1 into NVIDIA/OEM authority, partner credential inheritance, buyer acceptance, or a waiver of minimum specifications. Any later buyer-controlled clarification must be independently source-bound by new source identity, digest, and normalized semantics.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)
