# SOL-ASTRA receipt — `socotec-cmt-network-federation-lims-01`

Scope is the additive synthetic/read-only SOCOTEC CMT network federation package only. No live LIMS/QMS/scheduling/instrument/reporting/customer/provider system was contacted or mutated.

## Acceptance frozen

- 500 synthetic jobs / 25 namespaces.
- 400 `READY`; 100 truth-set `HOLD`.
- Holds: 17 `SCOPE_MISMATCH`, 17 `METHOD_VERSION_MISMATCH`, 17 `EQUIPMENT_UNAVAILABLE`, 17 `QUALIFICATION_INVALID`, 16 `CAPACITY_EXCEEDED`, 16 `DUPLICATE_JOB_ID`.
- Every READY job routes once to its golden site/personnel/method/equipment/qualification.
- Zero namespace collisions; cross-site work requires a deterministic authorized-transfer ticket.
- Legacy payload hashes reconcile read-only; tamper fails closed.
- Same-submission changed payload fails closed; exact replay adds zero state.
- Human release is unsent/copy-only; automation identities are rejected; automatic release disabled.

Test, fixture, manifest, Git, and merged-main readback hashes are recorded in the canonical Slack SHIPPED receipt after publication.
