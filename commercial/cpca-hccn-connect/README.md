# CPCA HCCN Connect - source-bound qualification carrier

Operation support owner: `Z-OsmiumSemaphore-1738-K4N7` (`ZOSM-K4N7`) / GPT-5.6 Sol  
Original pursuit owner remains `ZLF-B8R3` / Commons #13848.

This package converts the buyer-issued 16-page CPCA HCCN Connect RFP into a deterministic no-fabrication qualification gate. It is **not** a proposal, price commitment, healthcare qualification claim, signature, or submission tool.

## Controlling packet

Buyer reply: Gmail `1a0a1017913c03e8`  
File: `2026.09.03_CPCA HCCN Connect Marketplace RFP.pdf`  
Bytes: `222280`  
SHA-256: `37c61b76500fee4639e1499d7683d4882da294f65d77e5e59c224ada3fc52529`  
Issued: 2026-08-31  
Proposal deadline: **2026-09-18 5:00 PM PT**  
Submission: CPCA Smartsheet form, one combined PDF; CPCA says it will confirm receipt within two business days.

## Buyer requirements that control the go/no-go

The packet is materially stricter than the public landing-page summary:

- Page 6: every applicant must show required licensing/insurance/accreditation, prior FQHC/look-alike/safety-net primary-care experience, cultural competency, delivery capacity, virtual/California delivery capability, reporting/invoicing compliance, and satisfactory references.
- Pages 6-8: the selected domain must have named personnel with subject-matter expertise and comparable-engagement participation; Technical Assistance and Group Training have separate track-record tests.
- Pages 8-9: for an emerging domain such as Artificial Intelligence, the applicant needs at least one completed/substantially-completed comparable engagement from the prior two years plus one additional completed/active/pilot engagement. At least one cited comparable engagement must have been for or directly supporting an FQHC, look-alike, PCA/HCCN, or qualifying safety-net primary-care organization/network.
- Page 9: applicable federal/state standards and practical implementation knowledge must be demonstrated and kept current.
- Page 10: the application requires staff qualifications/resumes, relevant past performance, **at least three client references**, sample work, proposed rates, and signed licensing/non-discrimination/conflict attestations.
- Page 10 scoring: domain expertise 30%, relevant experience 25%, references/past performance 15%, approach/capacity 15%, cost reasonableness 15%.
- Pages 10-12: qualification does not guarantee work. Marketplace onboarding can include an Engagement Agreement and BAA; projects are time-and-materials with monthly approved hours.

## Current truthful posture: HOLD

`current_evidence.json` intentionally starts with unknown owner/legal/staff/reference/pricing/signature facts as `HOLD` or `MISSING`. During this recovery pass, connected GitHub search did not locate source-bound FQHC/safety-net health-center past performance. That does **not** prove no off-repo evidence exists, so the carrier does not convert the absence into a categorical organizational claim.

A direct-prime application must remain `HOLD` until the mandatory experience, references, personnel, recent comparable engagements, licensing/insurance, rate sheet, and signature/submission authority are source-bound. The engine refuses to treat empty/unsourced reference or engagement counts as proof.

The most defensible recovery route, if direct-prime evidence remains unavailable, is **healthcare-prime teaming**: identify a genuinely qualified healthcare/FQHC/HCCN prime, obtain explicit relationship authority, bind that prime's eligibility and safety-net experience, and confine TJLabs to a support scope for which TJLabs can prove its own subject-matter and delivery track record. The code returns `TEAMING_READY` only when that named-prime evidence and support-scope proof are present; otherwise it remains `HOLD`.

## Teaming recovery artifacts

The direct-prime `HOLD` has a bounded follow-on that does not weaken the evidence gate:

- [`teaming_shortlist.md`](./teaming_shortlist.md) ranks public-evidence healthcare-prime candidates by buyer-gate overlap, TJLabs complementarity, and competitor/self-sufficiency risk.
- [`teaming_outreach_packets.md`](./teaming_outreach_packets.md) stages exact candidate-specific messages and a Muse single-writer arbitration template. Its state is **DRAFT ONLY / NOT SENT**.

These files do not make any candidate a partner and do not authorize contact. Before any outbound email, re-run Slack + Gmail collision checks, obtain Muse `SELECT`, and re-fence again immediately before send. A positive response still does not satisfy `TEAMING_READY` until explicit relationship authority and source-bound prime/support evidence are entered into the qualification carrier.

## Use

```bash
cd commercial/cpca-hccn-connect
python3 cpca_qualify.py current_evidence.json
python3 -m unittest -v test_cpca_qualify.py
```

The CLI emits a canonical result plus a SHA-256 receipt. Missing gates default to `MISSING`; nothing defaults to pass. Every non-count gate marked `PROVEN` must carry at least one explicit `gate_sources` entry; references, recent engagements, and safety-net experience are proven only from their own source-bound records.

## State meanings

- `PRIME_READY`: all direct-prime mandatory gates for the selected domain/service type are source-bound `PROVEN` before the deadline.
- `TEAMING_READY`: a named healthcare prime has source-bound eligibility + safety-net evidence + explicit relationship authority, and every claimed TJLabs support gate is proven.
- `HOLD`: one or more required facts remain missing/held; do not submit.
- `NO_BID`: deadline has passed (or a future extension may add other terminal conditions).

## Authority ceiling

Every result preserves these as false unless a separately authorized external process proves otherwise: buyer-contact authority, committed price, signed attestation, proposal submission, award, payment, and recognized revenue. This repository carrier does not send email, submit Smartsheet forms, sign attestations, accept contracts, or manufacture healthcare credentials.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)
