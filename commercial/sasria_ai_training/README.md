# Sasria RFP2026/22 AI-training readiness carrier

A dependency-free, fail-closed teaming/readiness package for **Sasria SOC Ltd RFP2026/22 — Appointment of Service Provider for Artificial Intelligence Training**.

The truthful TJLabs posture is **teaming-first / direct-prime HOLD** unless a qualified South African training lead supplies procurement, accreditation, certification, training-history, reference, platform-access, pricing, signatory, and portal evidence. The active commercial lane is separately governed; this source package does not authorize contact or submission.

## Source posture

- Official submission/query system: <https://procurement.sasria.co.za/>
- Solicitation: `RFP2026/22`
- Working close used by this carrier: **2026-09-17 12:00 SAST (UTC+02:00)**.
- Official Sasria RFP/amendments control. This repository does not contain an authenticated buyer-document byte snapshot and is not the procurement source of record.

## Readiness model

The compiler records candidate/reviewer evidence for required returnables, recognized AI-governance framework alignment, training-body accreditation, certification capability, one-year platform access, externally supplied buyer-score inputs, all six captured role pathways, and an explicitly paid TJLabs specialist workshare.

`RESPONSE_ASSEMBLY_READY` means only that those captured response-building gates are structurally complete. It does **not** mean the prime is qualified, the buyer has accepted a score, or a submission is authorized.

### Submission authority is deliberately hard-HOLD

Caller JSON fields `portal_account_confirmed`, `authorized_signatory_confirmed`, and `prime_approved_submission` are retained only as **candidate assertions**. Even literal `true/true/true` cannot mint `SUBMISSION_READY`. The machine status remains `HOLD` with `trusted_submission_authority_not_bound` until a future separately trusted authority source/generation is designed and reviewed.

This closes the unsafe predecessor where the same caller who authored the evidence JSON could self-assert portal/signatory/prime approval and manufacture the package's strongest status.

## Paid TJLabs seam

See [`TEAMING_WORKSHARE.md`](./TEAMING_WORKSHARE.md). The supported workshare commercial state is only `PAID_SCOPE_TO_BE_AGREED`. `FREE_DISCOVERY` or another state fails the workshare gate. This is not a contract, accepted price, award, invoice, payment, or booked revenue.

## Strict-input / CLI boundary

The CLI validates nested object/list/string/boolean shapes before compilation. Hostile but valid JSON such as `prime.returnables: []`, `prime.framework_alignment: true`, or `training_pathways: null` returns deterministic exit code `2`, prints a controlled `INPUT_ERROR` on stderr, emits no traceback, and creates no requested output artifacts. The same predecessors are exercised under normal Python and `python -O`.

The included HOLD fixture can be run with:

```bash
python -m commercial.sasria_ai_training.cli \
  commercial/sasria_ai_training/example_hold.json \
  --json-out /tmp/sasria-readiness.json \
  --markdown-out /tmp/sasria-readiness.md
```

A successful compile still returns exit code `2` because this carrier intentionally cannot authorize submission.

## Claims boundary

This package does **not** certify CSD/B-BBEE status, establish South African procurement eligibility, claim training accreditation/certification authority, validate references/facilitators, issue buyer scores, register a portal account, authorize/sign/submit a bid, create a partnership/subcontract, or establish award/payment/cash/revenue.

## Tests

```bash
python -m unittest test_sasria_ai_training test_sasria_ai_training_hardening -v
python -O -m unittest test_sasria_ai_training test_sasria_ai_training_hardening -v
```

The root suites cover returnables, score caps/threshold, role completeness, paid-workshare separation, deterministic receipts, direct-public-API malformed inputs, caller authority self-mint prevention, the known HOLD fixture, and hostile real-CLI JSON shapes with no partial output publication.
