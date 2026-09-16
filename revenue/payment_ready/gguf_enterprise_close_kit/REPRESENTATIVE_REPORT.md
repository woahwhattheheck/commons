# Representative GGUF Diagnostic Report — Synthetic / Redacted

**Offer:** `gguf-diagnostic-10d-12k`  
**Engagement:** `synthetic-gguf-001`  
**Status:** synthetic rehearsal only — not a customer result, acceptance, payment, or revenue event

## Executive finding

A bounded synthetic ablation produced an artifact with a distinct SHA-256 from the synthetic original, and the synthetic restore returned exactly to the original SHA-256 and byte count. Three distinct harness-run receipt identities represent baseline, ablation, and restore executions. This demonstrates the **shape of the AT1–AT6 evidence packet** and byte-exact rollback contract. It does not demonstrate any customer-model performance improvement.

## Evidence summary

| Test | Representative evidence | Result |
| --- | --- | --- |
| AT1 original hash | `aaaaaaaa…aaaa`, 4,294,967,296 bytes | evidence-shaped PASS |
| AT2 ablation differs | `bbbbbbbb…bbbb` != original | evidence-shaped PASS |
| AT3 byte-exact restore | restored `aaaaaaaa…aaaa`, same byte count | evidence-shaped PASS |
| AT4 harness receipts | baseline `cccc…`, ablation `dddd…`, restore `eeee…` | evidence-shaped PASS |
| AT5 concise finding | report identity `ffffffff…ffff` + limitations below | evidence-shaped PASS |
| AT6 delivery receipt | receipt `99999999…9999` binds required hashes | evidence-shaped PASS |

“Evidence-shaped PASS” here means the synthetic fixture satisfies the deterministic close-kit contract. It is not a representation that a real customer artifact was processed.

## What the customer would receive in a real engagement

- immutable original GGUF SHA-256 + byte count;
- frozen harness command/config and evaluation-suite identities;
- baseline, ablation, and restore run receipts;
- bounded intervention/ablation artifact identity;
- proof that the restored artifact is byte-identical to the original;
- concise finding describing what was shown and measured;
- explicit limitations and unresolved questions; and
- a hash-bound delivery receipt for acceptance review.

The customer model bytes, private evaluation cases, signed documents, credentials, and payment data are not part of the Commons evidence packet.

## Representative limitations

1. This report uses synthetic hashes and no customer/model bytes.
2. The contract proves artifact identity, evidence linkage, and rollback—not benchmark lift.
3. A real harness result remains meaningful only for the frozen customer harness/evaluation identity supplied for that engagement.
4. Customer acceptance is an external decision after review of AT1–AT6; the close-kit cannot self-accept.
5. A payment reference, if one later exists, is commercial evidence only and never substitutes for delivery or acceptance.

## Stop-state example

If the restored SHA-256 or byte count differs from AT1, AT3 fails and the engagement enters a rollback HOLD. TJLabs should not paper over the mismatch with a positive metric result or proceed to claim acceptance. The customer instead receives the safe evidence/limitations required to decide the next action.

## Expansion boundary

Only after a **real** customer accepts AT1–AT6 on the same GGUF should the separate 30-day White Box pilot be discussed. A license/productization path is later still and requires paid delivery; neither is implied by this synthetic report.
