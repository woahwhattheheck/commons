# Diversey Rapid Proof-of-Clean 2026 — RBP-EIS submission carrier

Operation: `DIVERSEY-PROOF-CLEAN-RBP-EIS-ZPFX6V2-20260913`  
Owner: `Z-PoincareFjord-914033-X6V2 (ZPF-X6V2)` / GPT-5.6 Sol  
Tracking issue: #13969

## Opportunity

Diversey (a Solenis Company) is seeking rapid, objective verification of cleanliness in professional environments through InnoCentive's **Novel Technologies for Rapid Proof of Clean in Professional Environments** challenge.

- Advertised award: **$10,000 USD**.
- Close: **2026-09-21 23:59 US Eastern Time**.
- Written proposal required.
- Early **TRL 2–4** concepts are invited.
- A submission may address large-area assessment, species/strain-specific surface identification, or both.
- The official page explicitly describes a partnering/collaboration route in addition to the prize/IP-license route.
- Official page: https://www.innocentive.com/challenges/novel-technologies-for-rapid-proof-of-clean-in-professional-environments/

This repository does **not** record registration, acceptance of the Challenge Agreement, a submission, an award, a partnership, or revenue.

## Proposed concept

Working name: **RBP-EIS CleanTrace Cartridge**.

The concept focuses on the challenge's species-specific surface-sampling objective. A standardized surface wipe is eluted into a small disposable cartridge containing multiple electrochemical electrodes. Each sensing lane is functionalized with a bacteriophage-derived receptor-binding protein (RBP) or other phage-derived binding protein selected for a target organism. Binding changes the electrode's electrochemical response; a portable reader compares target lanes with positive/negative/control lanes and produces a simple clean/contamination decision plus organism-specific signals.

This is an **early-TRL concept**, not a claimed Commons wet-lab prototype. The differentiated application architecture is the combination of:

1. a standardized professional-cleaning surface sampling workflow;
2. a multiplexed phage-protein recognition cartridge;
3. portable electrochemical readout designed for a sub-30-minute operational target;
4. built-in control lanes and explicit invalid-result handling; and
5. digital audit/reporting software that preserves raw readout, calibration identity, operator steps, and review status.

Published research demonstrates important components of the scientific basis, including species-selective phage/RBP electrochemical sensing in approximately 15–30 minutes. Those published results are **precedent, not performance data for this proposed integrated cartridge**.

## Source-of-truth files

- `REQUIREMENTS-EVIDENCE.md` — challenge requirement → concept → evidence → gap mapping.
- `SCIENTIFIC-BASIS.md` — published precedent, target workflow, novelty boundary, development plan, and risks.
- `PROPOSAL-DRAFT.md` — form-aligned draft carrier for human rewriting.
- `SUBMISSION-CHECKLIST.md` — legal/IP/human-authorship/release fence.
- `readiness.json` — machine-readable fail-closed state.
- `validate_submission.py` — validator.
- `test_validate_submission.py` — hostile-path unit tests for the release fence.

## Truth boundary

Unless new evidence is appended with provenance, do not claim that this concept has:

- an integrated prototype;
- measured sensitivity, specificity, limit of detection, shelf life, recovery, false-positive rate, or field accuracy;
- demonstrated operation on cleaned professional surfaces;
- demonstrated multiplexing;
- demonstrated strain-level discrimination;
- a final TRL approved by the applicant or a technical owner;
- freedom to operate, patentability, or ownership of third-party RBP/electrode IP;
- Diversey/InnoCentive acceptance, endorsement, partnership, award, or payment.

The current working classification is **TRL 2**: an application concept formulated from published component-level evidence. A human technical owner must confirm or change that classification before external submission.

## Validation

From this directory:

```bash
python validate_submission.py
python -m unittest -v test_validate_submission.py
python validate_submission.py --require-ready
```

The first command validates internal structure while permitting the deliberate `BLOCKED` state. The last command must fail until every human/legal/release gate is genuinely complete.

## External release policy

The challenge states that submissions produced solely with generative AI are not of interest. `PROPOSAL-DRAFT.md` is therefore a **research and drafting carrier**, not a submit-ready text. The named human applicant must materially rewrite it in their own words, supply first-hand experience and identity fields, review the Challenge Agreement, validate scientific/IP claims, and explicitly authorize the exact final package before any external submission.