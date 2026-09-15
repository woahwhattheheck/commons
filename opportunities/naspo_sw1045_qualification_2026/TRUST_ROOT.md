# NASPO SW1045 v1 trust-root ceiling

## Security decision

The v1 qualification compiler is intentionally **not capable of emitting a READY state from metadata alone**.

`source_snapshot.json`, `attachment_manifest.json`, `requirements.json`, owner evidence refs, URLs, and digest strings are all caller-supplied inputs. Validating their schema and internal consistency is useful for diagnostics and draft preparation, but it does not authenticate an official solicitation packet or prove custody of the bytes named by those fields.

Therefore every supported v1 executable/import path hard-fails packet readiness until an independent packet trust root exists. As a result:

- Prime routes remain `HOLD_OFFICIAL_PACKET_REQUIRED` instead of `PRIME_READY_FOR_OWNER_REVIEW`.
- A selected teaming route may remain `TEAMING_DRAFT_READY_FOR_OWNER_REVIEW`, but caller-authored partner + packet metadata cannot promote it to `TEAMING_SUBCONTRACT_READY_FOR_OWNER_REVIEW`.
- Existing authority bits remain false; this repair does not authorize contact, registration, portal access, proposal submission, representations, pricing, signature, spend, contract acceptance, payment, or revenue recognition.

## One executable authority

There is one current executable/import authority: `qualification_core.py`. `qualification.py` is a compatibility re-export of that same authority and contains no monkeypatch or separate policy generation.

The predecessor source bytes are retained as `qualification_core_v1.source`, a non-`.py` provenance artifact. `qualification_core.py` loads those implementation bytes only after replacing the predecessor `packet_ready()` definition with the fail-closed v1 policy in an isolated namespace; the loader refuses to run if the exact predecessor policy marker is not present once. The retained `.source` file is not a supported module or CLI.

This closes the post-merge #14556 defect where the predecessor had remained directly importable/executable as `qualification_core.py`, allowing a fresh process to bypass the wrapper-level monkeypatch.

## Regression boundary

`test_qualification_core_boundary.py` directly imports the core path and also spawns the core CLI in fresh interpreters under normal and `-O` execution. It supplies the same self-consistent caller-authored packet/owner metadata that the predecessor accepted for PRIME READY and TEAMING READY and requires both paths to remain fail closed. Verification also recomputes the fail-closed generation and rejects a forged READY receipt.

The path-scoped workflow runs both the original regression suite and the direct-core boundary suite on Python 3.11 and 3.13, normal and optimized, then verifies the truthful current receipt through both the public entrypoint and direct core CLI.

## What a future READY-capable version must add

A later version may restore READY states only after it has a trust root that does not originate solely in the same caller metadata being evaluated. At minimum it must:

1. consume the official packet/addenda bytes (or an independently authenticated equivalent),
2. compute digests from those consumed bytes rather than trust supplied digest strings,
3. derive or bind the attachment inventory to those authenticated bytes,
4. bind each requirement's `source_document_id` and digest to the authenticated manifest/preimage,
5. authenticate official source identity rather than treating an arbitrary HTTPS URL as proof,
6. keep owner/partner evidence distinct from packet provenance, and
7. add predecessor-killer tests showing caller-authored metadata alone cannot mint READY through every supported module and CLI path.

Until those conditions exist, HOLD/DRAFT is the truthful state and is an intentional product guarantee, not missing functionality.
