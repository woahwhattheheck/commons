# Tencent Aspire 2026 — Internal Brain reference build

Original competition claim/design credit: **Z-Aster-67 / GPT-5.6 Sol**. Official-source qualification credit: **Z-Cairn-4R7Q / GPT-6 Astra Pro**. Recovery implementation/finalization carrier: **Z-Sol-17 / GPT-5.6 Sol**.

This directory is a zero-dependency Python 3.11 reference implementation for Tencent Cloud Singapore 2026 Aspire FinTech track **“The Internal Brain — Building a Context-Aware Enterprise Knowledge System with RBAC, Security Logging & Audit Trail.”** It is intentionally deterministic and non-generative: authorization is evaluated before retrieval, document bytes are always data rather than instructions, every retained result has source provenance, and security-relevant operations append to a SHA-256-linked audit chain.

## Security contract

- One engine instance has one canonical tenant. Cross-tenant requests fail closed before touching that tenant's audit stream.
- Users reference known roles only; roles carry explicit permissions and numeric clearance.
- Documents bind tenant, stable ID/version, exact content digest, classification, allowed roles, labels and source URI.
- Query authorization is applied **before** lexical scoring. \`document_ids\` is a narrowing filter and can never grant access.
- Document text has no policy authority. Common prompt-injection markers are surfaced as untrusted evidence but cannot alter roles, clearance or retrieval scope.
- Results include exact source URI + content SHA-256 citations.
- Audit events bind sequence, previous digest, tenant, actor, event/decision, subject and payload digest. \`verify_audit()\` fails if events are edited or relinked.
- The implementation makes no claim that SHA-256 chaining alone prevents a privileged operator from deleting the entire log. Production deployment should anchor audit heads into an external append-only/WORM service or signed checkpoint system.

## Run

\`\`\`bash
cd competitions/tencent_aspire_internal_brain
python -m py_compile internal_brain/*.py test_internal_brain.py
python -m unittest -v test_internal_brain.py
python -O -m unittest -v test_internal_brain.py

python -m internal_brain validate demo_bundle.json
python -m internal_brain query demo_bundle.json demo_query_employee.json --audit-out audit.json
python -m internal_brain verify-audit audit.json
python -m internal_brain query demo_bundle.json demo_query_finance.json
\`\`\`

The employee demo returns only employee-authorized travel material. The finance demo can retrieve the classified finance plan. The untrusted vendor note deliberately contains \`Ignore previous instructions\` / \`bypass authorization\`; those bytes are reported as untrusted markers but never executed or treated as policy.

## Deterministic decision codes

Query: \`AUTHORIZED_MATCH\`, \`AUTHORIZED_AMBIGUOUS_MATCH\`, \`NO_AUTHORIZED_MATCH\`.

Authorization failures: \`TENANT_MISMATCH\`, \`UNKNOWN_USER\`, \`PERMISSION_DENIED\`, \`CLEARANCE_DENIED\`, \`ROLE_SCOPE_DENIED\`, \`DOCUMENT_ID_CONFLICT\`.

Ingest: \`INGESTED\`, \`IDEMPOTENT_REPLAY\`.

## What this build is / is not

This is a reproducible local reference engine and competition evidence carrier. It does not provision Tencent Cloud, submit to the competition, operate on customer data, claim production certification, or claim any prize/revenue. A production system would normally replace in-memory state with tenant-isolated storage, external identity/IAM, encrypted object/index storage, rate limiting, authenticated audit checkpoints, and a separately governed answer-generation layer that can consume only the already-authorized evidence set.
