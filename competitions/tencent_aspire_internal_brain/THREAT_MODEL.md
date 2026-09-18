# Threat model — Internal Brain reference build

## Assets and invariants

The protected assets are tenant knowledge, role/clearance policy, document provenance, and the integrity/order of security events. The central invariant is **authorization before retrieval**: unauthorized document content must not enter the candidate evidence set, regardless of query wording, requested IDs, document text, or optimization mode.

## Adversaries considered

1. A valid low-privilege user attempting to retrieve a higher-classification or role-restricted document.
2. A caller spoofing another tenant or unknown user ID.
3. A document author embedding prompt-injection language such as “ignore previous instructions” or “bypass authorization.”
4. A caller trying to use \`document_ids\` as an allow-list override.
5. A malformed-data sender exploiting duplicate JSON keys, unknown roles, duplicate identities, non-canonical digests, or conflicting document IDs.
6. An operator/editor mutating an exported audit event or relinking the chain.
7. Runtime behavior changing under \`python -O\` because security logic was accidentally placed in assertions.

## Controls

- Strict schema and duplicate-key rejection.
- Exact tenant binding and known-user lookup before retrieval.
- Role permission + maximum role clearance computation.
- Document classification and role intersection evaluated before scoring.
- Deterministic, non-generative lexical retrieval. Document bytes never become executable/control instructions.
- Exact document content SHA-256 and source URI in result citations.
- Append-only-in-process hash chain with independent verifier.
- Hostile tests executed in normal and optimized Python; no security property depends on \`assert\` in production code.

## Residual risks / production work

- SHA-256 chaining detects edits to retained events but does not itself stop a privileged operator from deleting or replacing an entire local log. Anchor heads externally (WORM storage, signed transparency checkpoint, or managed audit service).
- In-memory state is a demo boundary, not durable tenant isolation. Production needs authenticated storage namespaces, encryption, backup/restore, concurrency control, retention policy and disaster recovery.
- Lexical retrieval is intentionally simple. A production vector/semantic index must preserve the exact same pre-retrieval ACL filter and prove that the index cannot leak cross-scope embeddings/metadata.
- Identity here is a supplied user ID. Production must bind it to enterprise IdP/IAM tokens and session context.
- The injection marker list is diagnostic only, not a complete prompt-injection detector. Safety comes from treating all document text as untrusted data and keeping authorization outside document control, not from marker detection.
- Availability attacks, storage exhaustion, network-layer abuse, cloud IAM configuration, key management, legal/compliance requirements and operational monitoring remain deployment responsibilities.
