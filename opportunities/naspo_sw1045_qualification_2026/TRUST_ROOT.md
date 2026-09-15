# NASPO SW1045 v1 trust-root ceiling

## Security decision

The v1 qualification compiler is intentionally **not capable of emitting a READY state from metadata alone**.

`source_snapshot.json`, `attachment_manifest.json`, `requirements.json`, owner evidence refs, URLs, and digest strings are all caller-supplied inputs. Validating their schema and internal consistency is useful for diagnostics and draft preparation, but it does not authenticate an official solicitation packet or prove custody of the bytes named by those fields.

Therefore `qualification.packet_ready(...)` is fail-closed and always returns `False` in v1. As a result:

- Prime routes remain `HOLD_OFFICIAL_PACKET_REQUIRED` instead of `PRIME_READY_FOR_OWNER_REVIEW`.
- A selected teaming route may remain `TEAMING_DRAFT_READY_FOR_OWNER_REVIEW`, but caller-authored partner + packet metadata cannot promote it to `TEAMING_SUBCONTRACT_READY_FOR_OWNER_REVIEW`.
- Existing authority bits remain false; this repair does not authorize contact, registration, portal access, proposal submission, representations, pricing, signature, spend, contract acceptance, payment, or revenue recognition.

## Why this repair exists

The predecessor accepted a self-consistent set of caller-authored booleans, URLs, document IDs, and SHA-256 strings as sufficient to set `official_packet_ready=True`. That let a caller manufacture the trust root the compiler was meant to verify. Requirements could also name document IDs/digests without the compiler consuming a trusted preimage.

The recovery preserves the predecessor's validation and receipt machinery but removes that privilege escalation. The original implementation is retained as `qualification_core.py`; the public `qualification.py` wrapper replaces only the `packet_ready` policy hook. The original regression suite is retained as `qualification_tests_v1.py`; unsafe READY expectations are replaced by predecessor-killer tests in `test_qualification.py`.

## What a future READY-capable version must add

A later version may restore READY states only after it has a trust root that does not originate solely in the same caller metadata being evaluated. At minimum it must:

1. consume the official packet/addenda bytes (or an independently authenticated equivalent),
2. compute digests from those consumed bytes rather than trust supplied digest strings,
3. derive or bind the attachment inventory to those authenticated bytes,
4. bind each requirement's `source_document_id` and digest to the authenticated manifest/preimage,
5. authenticate official source identity rather than treating an arbitrary HTTPS URL as proof,
6. keep owner/partner evidence distinct from packet provenance, and
7. add predecessor-killer tests showing caller-authored metadata alone cannot mint READY.

Until those conditions exist, HOLD/DRAFT is the truthful state and is an intentional product guarantee, not missing functionality.
