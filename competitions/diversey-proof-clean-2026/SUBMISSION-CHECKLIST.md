# Diversey Proof-of-Clean — submission and release checklist

**This checklist does not authorize an external submission.** It keeps a research carrier from being mistaken for an accepted legal/IP commitment or a validated biosensor.

## A. Revalidate the opportunity

Immediately before any external action:

- [ ] Re-open the official challenge page and confirm it is still active.
- [ ] Confirm close remains 2026-09-21 23:59 US Eastern.
- [ ] Confirm advertised award, eligibility, participation types, form fields, attachment rules and maximum-submission count.
- [ ] Read the current Challenge Agreement in full.
- [ ] Record the agreement/version/date actually reviewed.

## B. Applicant / eligibility — HUMAN ONLY

- [ ] Select the truthful participation type.
- [ ] Supply legal applicant/entity name and contact details.
- [ ] Confirm the applicant is not excluded by Solenis/Diversey employment/family/affiliate rules.
- [ ] Supply first-hand team roles, relevant experience and project history.
- [ ] Confirm who has authority to submit and accept any resulting obligations.

Do not infer identity, legal status, biographies or authority from GitHub metadata.

## C. Technical truth

- [ ] Human technical owner confirms or revises the working TRL 2 classification.
- [ ] Every cited paper has been opened and checked against the statement attributed to it.
- [ ] Literature performance is never presented as CleanTrace performance.
- [ ] The final proposal says there is no integrated CleanTrace prototype unless new evidence exists.
- [ ] Detection limit, sensitivity, specificity, false-result rate, shelf life and surface recovery remain unmeasured unless exact evidence is attached.
- [ ] ≤25 minutes is labeled a design target, not an achieved result.
- [ ] Strain-level identification is not claimed without binder-specific validation.
- [ ] Whole-room assessment is not claimed for this surface-sampling v1 concept.
- [ ] Software/audit capability is not used as a substitute for wet-lab biosensor evidence.

## D. Scientific / partner review

Before an external technical claim:

- [ ] A qualified biosensor/microbiology reviewer assesses binder selection, electrode chemistry, sample handling and validation plan.
- [ ] Target organism(s) are selected from a real professional-cleaning use case, not merely from convenient published papers.
- [ ] Reference method and acceptance criteria are defined for any future experiment.
- [ ] Viable-vs-nonviable detection requirement is explicit.
- [ ] Surface recovery and cleaning-chemical matrix effects are treated as separate validation problems.

## E. IP / legal review — HUMAN ONLY

- [ ] Challenge Agreement IP/license terms reviewed and accepted only by an authorized human.
- [ ] Ownership of the final proposal is understood.
- [ ] Phage/RBP source, access and licensing path reviewed.
- [ ] Electrode/transducer chemistry IP reviewed.
- [ ] Freedom-to-operate/patentability claims are removed unless supported by legal review.
- [ ] No third-party figure, diagram, table or copyrighted text is reused without permission.
- [ ] No confidential buyer/partner information is included without authorization.

The proposal may cite public scientific results and identifiers; it must not copy article prose or figures.

## F. Human-authorship gate

The official challenge says submissions produced solely with generative AI are not of interest.

- [ ] Named applicant has materially rewritten `PROPOSAL-DRAFT.md` in their own words into a separate final artifact.
- [ ] Human applicant supplies first-hand experience/skills and chooses participation/partnering posture.
- [ ] Human applicant can independently explain the scientific mechanism, limitations and development plan.
- [ ] Final text has no `[HUMAN: ...]` or `[UNMEASURED ...]` drafting markers.
- [ ] Final text has been checked for unsupported specificity, invented history and marketing overclaim.
- [ ] Final proposal file is hashed and its path/hash entered into `readiness.json`.

## G. Commercial posture

- [ ] Human decides whether to pursue the $10,000 prize/license route, partnering route, or another allowed participation type.
- [ ] If partnering is selected, role split is explicit: Commons software/evidence/control layer vs biosensor/microbiology validation capability.
- [ ] No statement implies Diversey interest in this specific concept before Diversey communicates it.
- [ ] No expected award/payment is booked as revenue.

## H. Machine gate

Run from this directory:

```bash
python validate_submission.py
python -m unittest -v test_validate_submission.py
python validate_submission.py --require-ready
```

Expected pre-human state:

- structural validation: PASS;
- unit tests: PASS;
- `--require-ready`: exit code 2 while `state=BLOCKED`.

Do not change `state` to `READY` merely to make the final command green.

## I. Final release fence — HUMAN ONLY

Before any portal submit action:

- [ ] `state` is `READY` for factual reasons.
- [ ] All `human_gates` are true and individually evidenced.
- [ ] Current Challenge Agreement has actually been accepted by the authorized Solver.
- [ ] Final human proposal bytes match the SHA-256 recorded in `readiness.json`.
- [ ] Applicant identity / participation type / partnership posture are correct.
- [ ] Final technical/IP review is complete.
- [ ] Explicit authorization exists to submit this exact package.

Only then may an authorized human/account owner cross the external release fence.

## J. Post-submission, only if it actually occurs

- [ ] Set `external_actions.submitted=true` only after a real portal submission.
- [ ] Preserve portal receipt, exact timestamp and submitted artifact hash.
- [ ] Record accepted Challenge Agreement/version.
- [ ] Do not set `award_received` without an actual award notice.
- [ ] Do not set `payment_received` without actual settlement evidence.
- [ ] If Diversey proposes collaboration, record the exact communication and open a separate commercial-negotiation lane rather than rewriting history in this carrier.
