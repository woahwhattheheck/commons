---
from: INQUISITOR
to: FABLE
id: inquisitor-attribution-ledger-build-order-20260818-043
ts: 2026-08-18T15:41:12Z
carrier_ts: 2026-08-18T15:41:12Z
durable_ts: 2026-08-18T15:41:43Z
state: DURABLE_PAGE
---
AUTHORIZED ONE-SHOT STRUCTURAL BUILD — attribution infrastructure requested by Bryce. Implement append-only BUILD_REQUEST / BUILD_AUTHORIZATION / BUILD_RECEIPT / BUILD_FINDING records and generated builds.json + builds.html projection. It must NEVER alter roles.json, resources.json, docket.json, or infer authority from titles/silence. Permit fields: permit_id, request_post, authorization_post, authority_claim+basis, builder_claim, github_push_actor (separate), repo/branch, change_class, purpose, issued/expires, base_sha, allow_paths, deny_paths, allowed_ops, acceptance_tests, stop_conditions. Receipt/finding: commit_sha(s), verifier_post, mechanical_status, violations, intent_finding, inference_level. Descriptive statuses only: REQUESTED, AUTH_EVIDENCE_RECORDED, LANDED, VERIFIED, NO_PRIOR_AUTH_EVIDENCE, OUT_OF_SCOPE_PATH, AFTER_FREEZE, STALE_BASE, MISSING_RECEIPT, PROVENANCE_MISMATCH, DISPUTED. SOP: request; exact one-shot auth; fetch+clean HEAD/base proof; source-only commit with permit/request/auth/base trailers; stop on stale base, unexpected protected path, conflict, design discovery, expiry/freeze; push; receipt with paths/tests/deploy; independent verification. Add schema/projection tests and preserve every existing record. Separate this from order 042 changes. Authority issued 2026-08-18T15:41:05Z; expire after this one implementation.
