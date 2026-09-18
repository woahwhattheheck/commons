# Representative GGUF Diagnostic Report — Synthetic / Redacted

**Offer:** `gguf-diagnostic-10d-12k`  
**Engagement:** `synthetic-gguf-001`  
**Mode:** `SYNTHETIC_REHEARSAL`  
**Status:** evidence-contract rehearsal only — not a customer result, legal acceptance, delivery, payment, or revenue event

## Executive finding

A bounded synthetic ablation uses a distinct artifact identity and the synthetic restore returns to the original SHA-256 and byte count. Baseline, ablation, and restore receipt digests are recomputed from retained run semantics: run kind, exact input artifact, frozen harness-command identity, frozen evaluation-suite identity, and outcome-summary identity. A separate delivery receipt is recomputed from a retained manifest that binds the engagement, artifacts, run receipts, and report identity.

That demonstrates the **shape and tamper-detection behavior** of AT1–AT6. It does not establish any real customer fact.

## Representative evidence

| Test | Synthetic evidence | Fixture result |
| --- | --- | --- |
| AT1 original | `aaaaaaaa…aaaa`, 4,294,967,296 bytes | semantic fixture PASS |
| AT2 ablation | `bbbbbbbb…bbbb` differs from original | semantic fixture PASS |
| AT3 rollback | restored `aaaaaaaa…aaaa`, same byte count | semantic fixture PASS |
| AT4 run receipts | baseline `c2bb56a4…`, ablation `3d0762ba…`, restore `66f32417…`; all bind frozen harness/eval generation | semantic fixture PASS |
| AT5 finding | report identity `ffffffff…ffff` + limitations | semantic fixture PASS |
| AT6 delivery | manifest receipt `e0c7e292…` binds engagement/artifacts/run receipts/report | semantic fixture PASS |

A fixture PASS is **not** production readiness. The compiled close packet for this fixture is `SYNTHETIC_EVIDENCE_COMPLETE_NON_PRODUCTION` and still reports the current canonical buyer blocker.

## What a real customer evidence packet would contain

- immutable original GGUF SHA-256 + byte count;
- frozen harness command/config and evaluation-suite identities;
- baseline, ablation, and restore run payloads with recomputable receipts;
- bounded intervention artifact identity;
- byte-exact rollback identity;
- concise finding + explicit limitations; and
- a delivery manifest whose digest can be independently recomputed.

Customer model bytes, private evaluation cases, signed documents, credentials, and payment data are not Commons evidence.

## Recovery-runtime boundary

Receipt-shaped NDA/SOW/M1 values do not prove those events. The production recovery rail in `host/revenue_recovery.py` requires exact predecessor source bytes, exact external evidence bytes where applicable, schema-bound stage facts, and deterministic replay. The close kit never promotes standalone hashes to `nda_signed`, `sow_signed`, `m1_payment_received`, private file-transfer authority, customer acceptance, delivery, or revenue.

Current canonical recovery still says purchase intent `NEEDS_BUYER` and delivery `NOT_LANDED`, so no production-ready state is represented here.

## Representative limitations

1. No customer/model bytes were processed.
2. No buyer, NDA, SOW, M1 payment, acceptance, delivery, processor event, or cash event is represented.
3. A real harness result is meaningful only for the frozen customer harness/evaluation generation.
4. Byte-exact rollback is evidence; metric lift is not the acceptance rule.
5. A payment reference is commercial evidence only and never substitutes for AT1–AT6 or customer acceptance.

## Failure example

If a run receipt changes its input artifact, harness generation, evaluation generation, or payload without a matching recomputed digest, AT4 validation fails closed. If the delivery manifest is self-rewritten to point at the wrong report/run/artifact identities, AT6 fails even when the caller recomputes the manifest digest because the retained semantics no longer match the evidence packet.

If restored SHA-256 or byte count differs from AT1, AT3 fails. A positive benchmark result cannot paper over that mismatch.

## Expansion boundary

Only after a **real**, runtime-supported customer acceptance on the same GGUF should the separate 30-day White Box pilot be discussed. License/productization comes only after paid delivery; neither is implied by this synthetic rehearsal.
