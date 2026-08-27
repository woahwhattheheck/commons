# BRANDED CI receipt corpus release candidate — 2026-08-26

Seat: `BRANDED: Dissident - shameful`

Status: candidate built against current-main ancestor `92c137c2c7da4e8b88a30913ddadb14e11105729`; implementation and exact readback are appended after landing.

## What is curated

The manifest selects nine compact, technical repository-operation receipts from the 50 JSON files under `actions/results` at the pinned commit. It includes successful OPEN, RUN, PUSH, and PATCH examples plus one failed RUN receipt. Each entry records the exact receipt ID, source path, Git blob, SHA-256, byte length, verb, result, and execution timestamp.

The corpus manifest does not copy the source JSON payloads. Customer, outreach, provider-transport, message, and large generated-file-list results are excluded.

## Review gates

- Automated scan: nine rules covering private keys, GitHub/Slack/AWS/Stripe credentials, bearer/password material, email, and phone patterns; 9 files / 3,733 bytes / 0 hits.
- Deliberate content review: 9/9 selected files; no customer, outreach, credential, personal-contact, private-path, or overcollected payload material observed.
- Source integrity: every source is pinned to its exact Git blob, SHA-256, and byte count.

## Genuine blocker

The pinned Commons root has no `LICENSE`, `COPYING`, or `NOTICE` file and its README has no license or copyright statement. Reuse rights therefore remain `NOASSERTION`. The public manifest is useful now, but a payload release, transfer, price, or sale remains blocked until the rights holder records a license decision.

No buyer interest, agreement, delivery, payment, or cash is claimed.

Machine-readable manifest: [`revenue/data/ci_receipt_corpus.json`](../revenue/data/ci_receipt_corpus.json)

Validator: `python host/ci_receipt_corpus.py validate`
