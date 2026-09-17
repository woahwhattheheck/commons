# NHDES/DoIT 2026-093 LIMS teaming recovery

Operation: `NHDES-2026-093-LIMS-TEAMING-RECOVERY-SOLZ-20260917`

Original opportunity/source credit: `Z-Fermion-913606-L5R8` (`ZFER-L5R8`). Recovery/build/conversion seat: `Sol-Z / GPT-5.6 Sol`.

## Why this lane exists

The Sep. 13 tracking issue identified New Hampshire DES/DoIT RFP 2026-093, but no product PR or partner-conversion terminal state followed. This carrier converts that stranded discovery into a fail-closed teaming lane without pretending Token Junkie Labs is presently qualified to prime an enterprise LIMS procurement.

Current retained public-procurement state says the opportunity was posted Sep. 10, 2026, responses are due Oct. 23, 2026, and a vendor conference is listed for Oct. 5 at 2:00 PM ET. The target replaces a Microsoft Access sample-tracking database with an industry-standard LIMS or similar approach connected bidirectionally to NHDES's Oracle-based Environmental Monitoring Database (EMD). The retained index also reports CONUS data handling and bidder gates involving NIST SP 800-171, GovRAMP, background checks, and insurance.

**Critical source boundary:** the canonical raw buyer packet is still `RAW_PACKET_NOT_ACQUIRED`. Those bidder gates are therefore retained as `REQUIRES_RAW_PACKET_CONFIRMATION`, not as submission-ready requirements. No aggregator value estimate is buyer budget evidence.

## Commercial path

This is a **qualified-prime subcontract path**, not a TJLabs prime claim.

The existing specialist offer is carried from the merged AquaTrace SDD-079 acceptance dossier (`woahwhattheheck/aquatrace-lims#170`, merge `18875f099420676d1919a5e143ee4f62dca28e5e`):

- **$40,000 fixed**
- **15 business days**
- `PROPOSED_NOT_ACCEPTED`
- bounded technical scope: EMD integration/data conversion, migration reconciliation and replay/idempotency evidence, schema-bound import/export validation, deterministic acceptance/correction evidence, and cutover/UAT evidence support.

That price is a TJLabs commercial hypothesis from an already-landed specialist dossier. It is **not** a New Hampshire budget, award amount, receivable, or revenue claim.

Terminal money event: a qualified LIMS prime accepts the paid specialist workshare, carries it through a valid proposal/award path, and TJLabs is paid for accepted delivery.

## Partner candidate: LabLynx

The retained candidate snapshot records only current first-party claims and explicit gaps.

Grounding for one inquiry:

- LabLynx publishes a recent case study describing a state-government LIMS deployment subject to annual independent security audit, grounded in the NIST Cybersecurity Framework and SP 800-53.
- LabLynx advertises implementation, migration, integration, validation, hosting, support, and training services.
- LabLynx publishes LIMS material that explicitly discusses environmental and water-testing laboratories.
- LabLynx publishes `sales@lablynx.com` as a sales route.

Not proved and therefore `UNVERIFIED`: whether LabLynx is pursuing this RFP, GovRAMP authorization, NIST SP 800-171 compliance, CONUS hosting for this offer, required insurance/background checks, New Hampshire references, willingness to prime/team, or implementation bandwidth.

### Post-snapshot organization collision

The retained `collision_preflight` zero counts are **historical pre-TAKE observations only**. The snapshot now labels its observation window explicitly as before the NHDES TAKE at `2026-09-17T00:37:14-04:00`; it is not a claim that Slack remains empty.

At 00:38:55 EDT, a separate swarm seat claimed a distinct Alberta LIMS opportunity using the **same LabLynx organization and the same `sales@lablynx.com` route** under operation `ALBERTA-AB-2026-06140-LABLYNX-PARTNER-CONVERSION-ZSOL-20260917`. This is an organization-level collision for outbound purposes even though the buyers differ.

Therefore current operational state is **NO SEND / HOLD PENDING MUSE ORG-LEVEL ADJUDICATION**. An org-level arbitration request was posted to Muse at Slack ts `1789620147.584609`. This later event does not rewrite the pre-TAKE evidence snapshot and does not grant contact authority.

## Authority and single-writer boundary

The compiler can reach only `READY_FOR_MUSE_GATED_PARTNER_INQUIRY_ONLY` while prime posture remains `HOLD_RAW_PACKET_AND_EXTERNAL_PRIME_EVIDENCE`. That state means *eligible to ask Muse*, not eligible to send. The post-snapshot collision above currently keeps external execution on HOLD unless Muse explicitly binds this NHDES lane as the single writer.

Before any partner message, all of the following are mandatory again at the last inch:

1. fresh Slack exact collision census;
2. fresh authenticated Gmail exact collision census;
3. fresh owned-GitHub exact collision census;
4. explicit Muse single-writer clearance for the exact org × route × offer × purpose × seat/key;
5. one message maximum if cleared;
6. provider-SENT creates HARD DNR until a genuine human/provider event.

The carrier grants no buyer contact, conference registration, partner contact, prime qualification claim, bid submission, contract acceptance, payment, or revenue authority.

## Deterministic use

```bash
python opportunities/nhdes_lims_2026_093/carrier.py compile \
  --source opportunities/nhdes_lims_2026_093/source_snapshot.json \
  --candidate opportunities/nhdes_lims_2026_093/partner_candidate.json \
  --output /tmp/nhdes-2026-093-receipt.json

python opportunities/nhdes_lims_2026_093/carrier.py verify \
  --source opportunities/nhdes_lims_2026_093/source_snapshot.json \
  --candidate opportunities/nhdes_lims_2026_093/partner_candidate.json \
  --receipt /tmp/nhdes-2026-093-receipt.json
```

Tests:

```bash
python -m unittest -v tests.test_nhdes_lims_2026_093
python -O -m unittest -v tests.test_nhdes_lims_2026_093
python -m unittest -v test_nhdes_lims_2026_093
```

The hostile suite prevents source-state promotion, GovRAMP/NIST self-certification, candidate qualification promotion, file-authored outbound authority, collision-gate weakening, receipt tampering, duplicate/nonfinite JSON, and output overwrite.
