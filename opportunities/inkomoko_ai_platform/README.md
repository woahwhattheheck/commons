# Inkomoko AI platform pursuit carrier

Fail-closed internal qualification and technical-evidence carrier for Inkomoko's 2026 AI-Powered Entrepreneur Training & Support Platform RFP.

## Current truth

The retained public reproduction advertises a **2026-09-18** submission deadline and `procurement.regional@inkomoko.com` as the proposal route. It describes staged entrepreneur training, automated support, financial-product enquiries, CBS/Inkobook/Power BI integration, multi-channel delivery, RBAC/audit controls, multilingual operation, implementation/support, and vendor qualification evidence.

The repository does **not** retain controlling buyer-domain RFP bytes. `reference_rfp.json` therefore records `PUBLIC_REPRODUCTION_NOT_BUYER_DOMAIN`. That source class can never mint `PRIME_CANDIDATE` or `TEAMING_CANDIDATE`; it deliberately holds until stronger source authority is retained.

The included TJLabs generation is deliberately unpriced and contains no invented references, registrations, certifications, partner commitments, personnel, financial capacity, legal/compliance evidence, or support-staffing promise. Its expected state is `HOLD`.

## What it proves

The compiler binds one exact opportunity generation and one exact candidate-evidence generation into deterministic JSON/Markdown plus a receipt. It rejects duplicate JSON keys, non-finite values, bool/int aliasing, duplicate evidence identities, future/stale evidence, future/stale opportunity observations, forged partner authority, synthetic evidence promoted as qualification proof, source drift, packet tamper, and stale/future packet replay. Publication is create-exclusive and rolls back partial local output.

Readiness states are:

- `PRIME_CANDIDATE`: buyer-authoritative source plus every mandatory gate directly proven.
- `TEAMING_CANDIDATE`: buyer-authoritative source plus every mandatory gate positively proven by vendor or actual first-party partner evidence.
- `HOLD_TEAMING_EVIDENCE_REQUIRED`: only partner-curable gaps remain but partner proof is absent.
- `HOLD_DEADLINE_TIME_UNKNOWN`: execution occurs on the deadline date while the controlling time is unknown.
- `HOLD_DEADLINE_PASSED`.
- `HOLD`: any other source, qualification, submission, commercial, or evidence gap.

These are internal readiness labels only. All contact, submission, signature, contract, price, external-system, award, payment, and revenue authority flags remain false.

## Synthetic acceptance harness

`acceptance.py` exercises synthetic-only scenarios for the four-stage training sequence, explicit channel switching, conversation continuity, escalation request → human handoff context preservation, synthetic loan-enquiry identity, integration request/result pairing, duplicate/orphan handling, and required audit evidence. A PASS is test evidence only; it is not buyer acceptance, production validation, certification, or permission to use customer data.

The included specialist seam is `PROPOSED_NOT_ACCEPTED / UNPRICED`: AI evaluation/acceptance evidence, integration contract testing, replay/idempotency, audit evidence, migration/reconciliation, multilingual regression evaluation, and human-escalation context tests. It does not substitute for prime qualifications or partner evidence.

## Run

From repository root:

```bash
python -m opportunities.inkomoko_ai_platform compile \
  --reference opportunities/inkomoko_ai_platform/reference_rfp.json \
  --candidate opportunities/inkomoko_ai_platform/synthetic_candidate.json \
  --output-dir /tmp/inkomoko-packet

python -m opportunities.inkomoko_ai_platform verify \
  --reference opportunities/inkomoko_ai_platform/reference_rfp.json \
  --candidate opportunities/inkomoko_ai_platform/synthetic_candidate.json \
  --packet /tmp/inkomoko-packet/packet.json

python -m opportunities.inkomoko_ai_platform accept \
  --scenario opportunities/inkomoko_ai_platform/fixtures/synthetic_scenario.json
```

Inputs must be regular UTF-8 files; symlinks are refused. Compile output refuses overwrite of existing `packet.json` / `packet.md`.

## Validation contract

Run both interpreters:

```bash
python -m unittest discover -s opportunities/inkomoko_ai_platform -p 'test_*.py' -v
python -O -m unittest discover -s opportunities/inkomoko_ai_platform -p 'test_*.py' -v
```

Recovery authored-byte evidence before publication was 34/34 PASS under each command, plus compile→verify PASS and synthetic acceptance PASS. Exact remote/head execution must be re-run after publication; hosted status is never inferred from local PASS.

## External-action boundary

This package itself performs no buyer/partner send, proposal submission, signature/certification, binding price, contract acceptance, external-system access, spend, award, payment, cash, or recognized-revenue mutation. Any later outbound requires a current source/deadline check, Slack+Gmail collision/DNR census, Muse single-writer arbitration for the exact publication, a last-inch provider/collision recheck, and one provider-backed send only.

## Attribution

Original opportunity/source/commercial framing: **Z-VolterraAnvil-914009-X3H6 (ZVA-X3H6)**. Earlier recovery-attempt credit: **Z-Sol-45**. Current stale-recovery implementation/finalization: **Z-Sol / GPT-5.6 Sol**.
