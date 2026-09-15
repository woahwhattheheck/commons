# WRF 5417 — Domenico Santoro research-teaming call brief

> **INTERNAL / SUPPORT-ONLY.** This is call preparation, not a proposal submission, Western University commitment, named-team authorization, cost-share commitment, or permission to contact anyone else. The live carrier remains `HOLD / NOT SUBMITTED / $0 BOOKED` until the existing readiness gates clear.

## Mailbox / trust state

Dr. Domenico Santoro replied that he was interested in hearing the idea and offered same-day call windows. Parallel automation then sent multiple scheduling replies within seconds, prompting him to ask whether the outreach was a scam. One cleanup reply has already been sent acknowledging the automation collision, apologizing, withdrawing the noisy scheduling messages, and stating that Bryce will wait for Dr. Santoro to confirm a time or send a call link.

**Single-writer rule:** do not send another scheduling, reassurance, reminder, deck, attachment, calendar invite, or follow-up unless Dr. Santoro replies again or Bryce explicitly takes over the thread. The call is not assumed booked merely because earlier messages proposed times.

If the call happens, begin with one sentence only: *“Thanks for still considering the conversation after the duplicate emails; I’m keeping this focused on whether the research idea and a truthful role make sense.”* Then move immediately to substance.

## Why this conversation matters

WRF Project 5417 asks proposers to select 3–5 drinking-water/wastewater use cases, compare camera technologies from simple imaging through multi/hyperspectral options, validate camera-derived observations against conventional measurements, test performance across site/lighting/weather/deployment conditions, and assess cross-site/cross-camera transferability with minimal retraining.

Dr. Santoro is a coauthor of the 2024 *Water Practice & Technology* paper **“A novel camera-based sensor for real-time wastewater quality monitoring”** (DOI `10.2166/wpt.2024.211`). The published system used monochrome-camera images under six LED illuminants on real secondary wastewater effluent. Public abstract/reporting describes:

- focus on low turbidity, roughly 0–15 NTU;
- 96 real wastewater samples;
- >96% precision/accuracy for 2-NTU-class turbidity classification;
- neural-network regression with reported R² about 0.76 for turbidity and 0.72 for visible-range absorbance;
- planned/ongoing extension toward combined-sewer-overflow monitoring and waste-activated-sludge upset detection.

That work sits directly on the seam WRF 5417 now emphasizes: camera hardware → conventional water-quality reference → algorithm → field transferability.

## Desired outcome of the call

Do **not** try to “close” a partner in the first five minutes. Exit with explicit answers to these questions:

1. **Scientific fit:** Does the minimum-sensing + multi-site transfer framing make scientific sense for 5417, or is it missing a critical wastewater/optical constraint?
2. **Role fit:** Is Dr. Santoro interested in any concrete role (research partner, Co-PI if eligible, advisor, paid subcontractor), or should the team speak with another Western colleague instead?
3. **Evidence fit:** What prior camera/wastewater methods, data, protocols, hardware, or field knowledge could truthfully support a proposal—and what cannot be represented without new approval?
4. **Execution fit:** What experiments and utility/site access would be needed to make the cross-site claims credible within 24–30 months?
5. **Permission boundary:** What, if anything, may be written into a proposal after the call? Do not infer permission to name Western, name an individual, quote effort, promise data/site access, assign budget, or claim cost share.

A useful outcome can be “scientifically interesting, but no role.” That is better than inventing a team.

## 20-minute agenda

### 0–2 min — Reset + thesis

- Briefly acknowledge the duplicate-email error; do not over-explain automation.
- State the thesis in one sentence: **build a measurement-linked camera monitoring framework that identifies the lowest sufficient imaging system and quantifies how much performance survives site/camera/process domain shift.**
- Emphasize that Token Junkie Labs is not claiming wastewater-domain credentials it does not have; that is why this discussion exists.

### 2–7 min — Learn from the 2024 sensor

Ask, then listen:

- In the six-LED/monochrome setup, which sources of variance mattered most in practice: optical path, fouling, bubbles/solids, ambient light, camera exposure, temperature, sample handling, or wastewater matrix changes?
- What was the true ground-truth workflow for turbidity and absorbance, and how tightly did measurements need to align in time with imagery?
- Did the biggest errors come from low-signal physics, dataset size, instrument/reference uncertainty, or model limitations?
- Which parts of the prototype would survive a field deployment unchanged, and which would need enclosure/cleaning/calibration/redesign?
- For the proposed CSO or waste-activated-sludge extensions, what measurement target would be most defensible: regression to a conventional parameter, event classification, anomaly detection, or operator-confirmed process state?

Goal: turn the proposal from generic “camera AI” into a field-valid measurement study.

### 7–13 min — Shape the WRF experiment

Pressure-test this architecture:

**A. Lowest-sufficient-sensor ladder**  
Commodity RGB/monochrome + controlled illumination first; add spectral bands only when a defined use case shows measurable incremental value. Ask where the six-LED approach belongs in that ladder and whether the meaningful comparison is camera spectral sensitivity, active illumination wavelengths, or both.

**B. Paired conventional ground truth**  
Every scored camera observation must pair to an accepted lab/sensor/operator reference under a predeclared alignment window. Ask which wastewater references are realistic to collect frequently enough for model development without creating an impossible field burden.

**C. Site-held-out transfer**  
Instead of random-image train/test splits, reserve whole sites/camera configurations/time periods. Compare zero-shot transfer, calibration-only adaptation, lightweight fine-tuning, and full retraining. Ask what confounders must be stratified so “site transfer” is not merely a change in lighting or operator procedure.

**D. Failure/abstention**  
Missing, stale, fouled, misaligned, out-of-calibration, or out-of-domain observations should become HOLD/abstain states rather than silent predictions. Ask what operational failure modes a utility would actually need surfaced.

### 13–17 min — Define a credible Western seam

Offer role shapes, not commitments:

- **Scientific/wastewater validation lead:** experimental design, conventional-reference selection, process interpretation, field confounders, result review.
- **Camera-sensor work-package lead:** translate the 2024 prototype lessons into the technology ladder and field protocol.
- **Advisor/subcontractor:** bounded design/review hours if a PI/Co-PI role is inappropriate or impossible on deadline.
- **Referral:** if Dr. Santoro is interested scientifically but cannot participate, ask whether a more appropriate Western colleague could be introduced.

Token Junkie Labs' bounded seam can remain reproducibility/evidence engineering: acquisition/ground-truth lineage, deterministic data-quality gates, transfer-test harnesses, replayable metric calculation, ambiguity/abstention controls, and evidence packaging. Do not present TJLabs as the water-science prime.

### 17–20 min — Convert interest into explicit next facts

If there is interest, obtain only what is actually agreed:

- preferred role title/category;
- whether Western participation is institutionally plausible on this deadline;
- who must approve participation;
- whether any existing data/protocol/hardware can be referenced and under what conditions;
- approximate effort only if Dr. Santoro volunteers or agrees to discuss it;
- whether he permits his/Western's name to appear in a draft before institutional approval;
- what one follow-up artifact he wants (one-page work package, technical outline, budget scope, or nothing).

Repeat back the boundary: **nothing will be represented as committed until explicitly approved.**

## High-value technical questions if time is short

If only five questions fit, use these:

1. What single physical/operational confounder most threatens transferring the 2024 camera method from one wastewater stream/site to another?
2. Which conventional measurements can realistically provide enough paired labels for a multi-site study without overwhelming utility staff?
3. Would you compare camera classes, active illumination wavelengths, or the combined optical system to answer WRF's “minimum requirements” question?
4. For CSO/sludge/process monitoring, which target has the best combination of operational value, visual observability, and defensible ground truth?
5. Is there a role you could realistically take—or a colleague you would recommend—before the proposal deadline, and what may we truthfully say in the proposal?

## Decision table after the call

| Observation | Action |
|---|---|
| Interested + explicit role + permission to draft | Add only the agreed role to a marked draft; collect CV/Current & Pending/institutional/budget approvals before readiness changes |
| Interested scientifically, institutional timing unclear | Keep team gate HOLD; prepare one bounded work-package note for approval |
| Advisor/subcontractor only | Define deliverables/hours/rate later; do not invent effort or budget now |
| Referral offered | Contact the referred person only after the referral is actually made or permission is explicit |
| No participation | Record no; do not name Western/Dr. Santoro; continue partner route |
| No reply after cleanup | Do not chase immediately; preserve trust and let the existing owner decide any later follow-up |

## Non-negotiable boundaries

- No representation that Western University is a partner before explicit agreement and any required institutional approval.
- No invented Co-PI eligibility, CV, Current & Pending, salary, indirect rate, effort, cost share, site access, datasets, equipment, or letters of commitment.
- No request that Dr. Santoro solve TJLabs' separate My Portal, financial-statement, W-9, PI-eligibility, grant-management, certification, or 33% contribution gates.
- No statement that a good call makes the proposal submission-ready.
- No portal submission or legal/financial certification authority is created by this conversation.

## Public source anchors

- WRF Project 5417 official grant page: `https://portal.waterrf.org/outbound-grant-details/3352`
- Antonini G, Pearce JM, Berruti F, Santoro D. *A novel camera-based sensor for real-time wastewater quality monitoring.* Water Practice & Technology (2024). DOI: `10.2166/wpt.2024.211`
- Existing internal proposal architecture: `opportunities/wrf_5417_camera_ai/proposal_draft.md`

## Internal handoff note

The call should update live issue `#13845` with facts only: response status, agreed/declined role, permissions, named institutional approver if supplied, requested follow-up, and which readiness gates changed. Do not convert conversational enthusiasm into `PROVEN` evidence without the required documents/consents.
