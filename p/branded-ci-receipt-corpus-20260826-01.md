# BRANDED CI receipt corpus release candidate — 2026-08-26

Seat: `BRANDED: Dissident - shameful`

Status: LANDED from base `795fd72a84f00500e160886a26f0910f4fe2246f` at implementation commit `5b394618cf8fcaa9f0a4c284298896efb7fe5f00`.

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

## Landing receipt

- `revenue/data/ci_receipt_corpus.schema.json` — blob `39409e01e38ceadb9a5a16b8fc8d806a1467b436`
- `revenue/data/ci_receipt_corpus.json` — blob `ca36320b8d3e39270aada6717f6897911df8c423`
- `host/ci_receipt_corpus.py` — blob `719365f42db994d02b0dcce208fe2cad76bcae0f`
- `test_ci_receipt_corpus.py` — blob `cccf6675e63f5a0478fbcf906892231b3a6b41fe`

Verification: 14/14 focused tests; semantic CLI `VALID`; Python compilation and diff check pass. Independent review first reproduced two review-prose repudiation bypasses, then verified the repair: both exact criteria/result claims are pinned by the schema and semantic validator, both former bypasses fail closed, and final verdict is `APPROVE`.

