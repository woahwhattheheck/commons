# Dynamic Automotive Drop-Off & Diagnostic Intake — delivery core

This directory is an **offline/static delivery-readiness core** for the fixed **$4,000 / seven-day** offer sent to Dynamic Automotive Repair on 2026-09-13. The offer is still `SENT_NOT_ACCEPTED`: this package is not a customer YES, contract, deployment, shop-system integration, recognized revenue, repair authorization, diagnosis, estimate approval, charge, or customer message.

## What is implemented

The browser page and dependency-free ES-module engine model the actual handoff promised in the outbound offer rather than another generic callback form:

- vehicle/contact/symptom/request/drop-off capture;
- durable partial intake: missing required information is saved in `NEEDS_CLARIFICATION` instead of disappearing;
- VIN or plate+state identity canonicalization and a SHA-256 vehicle fingerprint;
- `sourceKey` idempotence: an exact browser/source replay creates zero duplicate jobs, while changed content under the same key fails closed;
- attachment metadata custody: the browser hashes selected file bytes with WebCrypto, and the engine binds filename/type/size/SHA-256 to the same intake (the demo does **not** persist file bytes);
- arrival receipt tied to the exact vehicle fingerprint, arrival channel, and—when the key-box flow is selected—a required key envelope/tag;
- explicit staff states `ARRIVED -> NEEDS_CLARIFICATION | DIAGNOSIS -> ESTIMATE_READY` with no encoded diagnosis or commercial decision;
- append-only per-intake history with one global monotonic sequence;
- deterministic current-queue + full-history JSON export with a content-addressed receipt;
- responsive mobile-first UI that renders untrusted record values through DOM `textContent`/text nodes rather than HTML injection.

## Authority boundary

The engine hard-codes all five decision-authority flags to false. Queue movement records **where staff work is**, not what the diagnosis is or whether work is approved. There is no SMS/email sender, payment rail, repair order write, DMS/shop-management connector, cloud persistence, deployment, or external network call in this core.

The demo uses browser `localStorage` for convenience and therefore is **not** a production privacy/security architecture. A real implementation requires buyer-approved identity/RBAC, retention/deletion rules, encrypted server-side persistence, attachment storage, audit controls, shop-system adapters, customer consent policy, and deployment/acceptance testing.

## Run and verify

Serve this directory with any static HTTP server and open `index.html` for the mobile/browser flow. Engine acceptance is network-free:

```bash
node --check engine.mjs
node --check app.mjs
node --check acceptance.mjs
node --test test_engine.mjs
node acceptance.mjs
```

The acceptance script creates four synthetic intakes and requires one record in each operational queue (`ARRIVED`, `NEEDS_CLARIFICATION`, `DIAGNOSIS`, `ESTIMATE_READY`), one hash-bound attachment, zero duplicate records from an exact source replay, all authority flags false, and a byte-stable verified export receipt.
