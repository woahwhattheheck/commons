# Aspire submission packet — draft, not submitted

## Challenge fit

**Track:** Aspire FinTech — “The Internal Brain: Building a Context-Aware Enterprise Knowledge System with RBAC, Security Logging & Audit Trail.”

**Build:** a deterministic reference engine demonstrating the hard security boundary underneath an enterprise knowledge assistant: strict tenant/user/role/document semantics; authorization before retrieval; evidence citations; prompt-injection-resistant document handling; deterministic denial/ambiguity reason codes; and a tamper-evident audit chain.

## 90-second demo script

1. Validate \`demo_bundle.json\` and show tenant, roles, users, documents.
2. Query as \`maya\` (employee) for travel rules. Show \`travel-policy\` and \`vendor-note\`; point out the vendor note contains malicious instruction text but the response explicitly reports it as untrusted data.
3. Ask \`maya\` for the finance plan by both natural-language query and exact \`document_ids=["finance-plan"]\`. Show the finance document remains absent: caller-supplied IDs narrow scope; they never grant it.
4. Query as \`li\` (finance) and retrieve \`finance-plan\` with exact source URI + content SHA-256.
5. Export the query audit chain and run \`verify-audit\` successfully.
6. Edit one prior event or previous-digest field; verifier fails.
7. Run the hostile tests in ordinary Python and with \`python -O\` to demonstrate the boundary does not depend on assertions.

## Architecture narrative

\`strict JSON -> tenant/user role resolution -> pre-retrieval ACL/classification filter -> deterministic scorer -> source/digest citations -> deterministic result receipt -> hash-linked security event\`

The reference engine deliberately avoids an LLM in the trust root. In a production architecture, an LLM may summarize only the authorized evidence returned by this layer; it never decides what the caller is allowed to see. That separation makes policy testable and keeps document prompt injection from becoming authorization logic.

## Evidence to include

- \`internal_brain/core.py\` — security model, retrieval, receipts, audit chain.
- \`test_internal_brain.py\` — hostile authorization/audit/injection tests.
- \`THREAT_MODEL.md\` — explicit residual risks and production boundary.
- \`demo_bundle.json\` + two role-specific queries.
- Normal and \`python -O\` test transcript from exact submitted commit.

## Limitations stated to judges

This repository build is local/in-memory and intentionally zero-dependency. It is not a production Tencent Cloud deployment and makes no certification claim. Cloud deployment should add enterprise identity, encrypted tenant-isolated persistence, a semantic index whose server-side filters preserve ACLs, external/WORM audit checkpoints, rate limiting and operational controls. The demo proves the authorization/provenance/audit kernel those services must preserve.

## External action boundary

No Tencent account action, competition registration, final submission, customer-data upload, prize acceptance, or revenue claim is performed by this artifact. Submission remains an explicit owner/provider action.
