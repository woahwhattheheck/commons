# Security HOLD → paid remediation scope

This package turns **evidence-backed held or partial findings** into a deterministic, owner-review implementation SOW. It exists to make an honest `HOLD` commercially useful without converting missing evidence into a positive security/compliance claim.

## What it accepts

A strict `security-remediation-scope-v1` manifest contains:

- the immutable source packet ID, SHA-256, and observation time;
- an evidence evaluation `as_of` time (historical owner-review semantics only);
- source findings with exact status, requirement, evidence IDs, current state, and gap;
- for actionable findings only, an explicit deliverable, observable acceptance test, dependencies, change-control trigger, and **owner-proposed integer-cent price**.

Only `PARTIAL`, `HOLD_MISSING_EVIDENCE`, and `HOLD_STALE_EVIDENCE` may create work items. `SUPPORTED` and `NOT_APPLICABLE` rows must carry `remediation: null`; trying to turn them into billable gaps is rejected.

## Fixed-scope commercial envelope

The bounded pilot envelope is **$5,000–$30,000**, entirely from owner-proposed line-item pricing. A scope inside the envelope emits `OWNER_REVIEW_READY`; an otherwise valid scope outside it emits `HOLD_PRICE_OUTSIDE_FIXED_SCOPE`. No state means buyer acceptance.

Commercial state is always `PROPOSED_NOT_ACCEPTED`.

## Prohibited outcome language

Proposed deliverables, acceptance tests, and change-control language fail closed if they attempt to promise certification/compliance/audit outcomes such as “certify”, “guaranteed compliance”, “SOC 2 compliant”, “HIPAA compliant”, “ISO 27001 certified”, “PCI compliant”, or “pass an audit”. The product may scope concrete technical/evidence work; it may not manufacture an auditor, lawyer, regulator, or customer acceptance decision.

## Demo

```bash
cd revenue/security_remediation_scope
python synthetic_fixture.py > /tmp/security-remediation-input.json
python remediation_scope.py compile \
  --input /tmp/security-remediation-input.json \
  --report-json /tmp/security-remediation-report.json \
  --report-md /tmp/security-remediation-report.md
python remediation_scope.py verify \
  --input /tmp/security-remediation-input.json \
  --report-json /tmp/security-remediation-report.json
```

The synthetic scope contains two actionable findings totaling $17,500 and one supported finding that is excluded from remediation.

## Determinism and custody

Duplicate JSON keys, floats/non-finite numbers, unknown critical keys, invalid IDs/hashes/timestamps, future-dated source packets, duplicate evidence/dependency IDs, Boolean prices, and malformed price values fail closed. Input findings and list values are normalized for semantic receipt stability. Verification recompiles the complete report and requires canonical byte-equivalent semantics.

The receipt binds exact raw input bytes, normalized semantic manifest, and canonical report body.

## Authority ceiling

Every report hard-codes `false` for buyer contact, contract acceptance, compliance certification, security attestation, deployment, invoice authorization, payment, and revenue recognition. The tool is an offline scoping artifact; it does not send, deploy, sign, invoice, charge, or certify anything.
