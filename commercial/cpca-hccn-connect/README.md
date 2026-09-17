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

The most defensible recovery route, if direct-prime evidence remains unavailable, is **healthcare-prime teaming**: identify a genuinely qualified healthcare/FQHC/HCCN prime, obtain explicit relationship authority, bind that prime's eligibility and safety-net experience, and confine TJLabs to a support scope for which TJLabs can prove its own subject-matter and delivery track record.

The legacy `cpca_qualify.py` state `TEAMING_READY` is now treated only as a **diagnostic predecessor signal**. The legacy evaluator can derive that label from caller-authored prime/source fields, so code ownership and receipt binding do not make those facts authentic. `cpca_partner_readiness.py` v3 therefore never promotes that diagnostic label into workshare discussion authority. Without a separately provider-authenticated evidence adapter, top-level readiness, `workshare.state`, and `application.state` all remain `HOLD` (except terminal `NO_BID`).

The v3 receipt still preserves strong provenance: public caller inputs are rejected unless they are exact plain JSON types, then frozen once into canonical byte snapshots before any semantic read. The code-owned predecessor evaluates an independent clone of that frozen snapshot while receipt binding uses another clone of the same bytes, preventing nested stateful mappings or evaluator mutation from creating evaluation-vs-binding splits. Receipts bind canonical specification semantics, exact specification-file bytes, the canonical frozen evidence digest, prime identity fields, application-manifest/source identities, the exact legacy implementation bytes, the qualification source packet, and the exact legacy result. Cross-prime/source/spec/evidence/legacy transplants therefore fail semantic verification even when visible state labels collide.

This generation has no provider-authenticated private-evidence adapter. Caller-authored source locators, hashes, booleans, or even a structurally complete application manifest are retained for provenance but are **not authentication** and cannot authorize either workshare discussion readiness or application readiness.

## Teaming recovery artifacts

The direct-prime `HOLD` has a bounded follow-on that does not weaken the evidence gate:

- [`teaming_shortlist.md`](./teaming_shortlist.md) ranks public-evidence healthcare-prime candidates by buyer-gate overlap, TJLabs complementarity, and competitor/self-sufficiency risk.
- [`teaming_outreach_packets.md`](./teaming_outreach_packets.md) stages exact candidate-specific messages and a Muse single-writer arbitration template. Its state is **DRAFT ONLY / NOT SENT**.
- [`partner_workshare/`](./partner_workshare/) is the executable positive-reply workshare packager. It fixes the healthcare-prime/TJLabs responsibility split, binds relationship and qualification evidence, renders a one-page review packet, and never grants external or commercial authority.
- [`cpca_partner_readiness.py`](./cpca_partner_readiness.py) records the legacy diagnostic signal and emits a canonical v3 receipt, but hard-HOLDs both workshare and application readiness until a future provider-authenticated adapter can prove the relevant facts.

These artifacts do not make any candidate a partner and do not authorize contact. Before any outbound email or contact-form message, re-run Slack + Gmail collision checks, obtain Muse `SELECT`, and re-fence again immediately before send. A positive response or internally reviewable workshare still leaves this repository carrier at `HOLD` until separately provider-authenticated prime/workshare/application evidence and human authority exist.

## Use

```bash
cd commercial/cpca-hccn-connect
python3 cpca_qualify.py current_evidence.json
python3 cpca_partner_readiness.py current_evidence.json
python3 -m unittest -v test_cpca_qualify.py
python3 -m unittest -v test_cpca_partner_readiness.py
```

`cpca_qualify.py` emits the legacy qualification result plus a SHA-256 receipt. `cpca_partner_readiness.py` code-owns `qualification_spec.json` and `cpca_qualify.py`, freezes supplied spec/evidence into strict plain-JSON snapshots before evaluation, and emits the truth-narrowed v3 provenance receipt. There is no caller-selectable legacy evaluator or specification override on the partner-readiness CLI. Missing gates default to `MISSING`; nothing defaults to pass. Every non-count gate marked `PROVEN` must carry at least one explicit `gate_sources` entry; references, recent engagements, and safety-net experience are proven only from their own retained records, and retained records alone still do not become provider authentication.

## State meanings

- `PRIME_READY` (legacy qualifier only): all direct-prime mandatory gates for the selected domain/service type are source-bound `PROVEN` before the deadline. The v3 partner-readiness wrapper does not inherit this as application authority.
- `TEAMING_READY` (legacy qualifier only): the legacy named-prime/support predicate passed. In v3 this remains a diagnostic signal only and grants no workshare or application authority.
- `WORKSHARE_DISCUSSION_READY`: **not emitted by v3**. This label is reserved until a separately provider-authenticated workshare evidence adapter exists and is reviewed.
- `HOLD`: the v3 default for both workshare and application readiness whenever provider authentication is absent or any required fact remains unresolved; do not submit or claim partnership authority.
- `NO_BID`: deadline has passed (or a future extension may add other terminal conditions).

## Authority ceiling

Every result preserves these as false unless a separately authorized external process proves otherwise: buyer-contact authority, credential-use authority, committed price, staff commitment, signed attestation, proposal submission, award, payment, and recognized revenue. This repository carrier does not send email, submit Smartsheet forms, sign attestations, accept contracts, use another organization's credentials, or manufacture healthcare qualifications.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../../commercial.html). Not remints of tip SKUs. Cite grok-bass-md-larger-fixed-20260916-01.
