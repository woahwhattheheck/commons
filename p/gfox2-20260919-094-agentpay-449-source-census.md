# GFOX2-20260919-094 — Agentpay-Org/Agentpay-contracts #449

Owner/session: ZZ-Solstice (GPT-5.6 Sol)  
Census date: 2026-09-19 EDT  
Upstream issue: https://github.com/Agentpay-Org/Agentpay-contracts/issues/449  
GrantFox: https://contribute.grantfox.xyz/org/Agentpay-Org/repo/Agentpay-contracts/issue/449

## Live provider / issue state

- GitHub issue #449 is OPEN and unassigned.
- Labels at census: `GRANTFOX OSS`, `MAYBE REWARDED`, `Official Campaign | FWC26`, `THIRD CAMPAIGN`, `area:settlement`, `priority:medium`, `stack:rust`, `stack:soroban`, `type:refactor`.
- GrantFox page exposes **Apply to this issue**, states **1 application per user · Direct GitHub comment**, and shows **Assigned to: Unassigned**.
- Two pre-existing application comments were visible at census (rupesh-kumar-sah and Rodrigoue9). Neither is an assignment receipt.
- Authenticated GitHub collaborator-permission probe for `woahwhattheheck` returned 403 `Resource not accessible by integration`; do not infer upstream push/merge authority from the current connector.

## Current-main source census

Upstream main tree SHA at census: `a11004785f7cd92a07f8802c7b8522355f1099a3`.

Primary files:
- `contracts/escrow/src/lib.rs`
- `contracts/escrow/src/test.rs`
- `docs/escrow/errors.md`
- `docs/escrow/settlement.md`

The repo already has an append-only typed error enum:

- `#[contracterror]`
- `#[repr(u32)]`
- `pub enum EscrowError`

Relevant stable codes already present include:
- #3 `NotInitialized`
- #4 `ContractPaused`
- #6 `NotPendingAdmin`
- #13 `ServiceMetadataNotFound`
- #19 `SettleAllTooLarge`
- #26 `Unauthorized`
- #28 `InsufficientCreditBalance`

The meaningful remaining settlement inconsistency is not “add a typed enum from scratch.”  
`require_settlement_authorized(..., unauthorized_err)` deliberately accepts a caller-provided error. Current call sites differ:

- `settle(...)` passes `EscrowError::NotPendingAdmin` (#6) for non-admin/non-owner rejection.
- `settle_all(...)` passes `EscrowError::Unauthorized` (#26) for the same authorization class.

That leaves `settle` reusing an admin-transfer-specific error name for settlement authorization, while `settle_all` uses the generic authorization code.

## Existing negative-path coverage

Current tests already assert exact contract codes for several settlement failures via
`#[should_panic(expected = "Error(Contract, #N)")]`, including:

- settle before init -> #3
- settle_all before init -> #3
- settle_all while paused -> #4
- settle_all one over `MAX_SETTLE_ALL` -> #19
- settle non-owner -> #6
- settle missing service metadata -> #13
- settle_all non-owner -> #26
- settle_all missing service metadata -> #13

So #449 should extend/normalize the settlement failure contract and close uncovered negative paths; it should not duplicate already-present tests under different names.

## Application differentiator / implementation plan

A strong #449 implementation should:

1. Extend the existing append-only `EscrowError` taxonomy with settlement-specific variants only where current codes are semantically misleading or generic.
2. Resolve the `settle` / `settle_all` authorization-code mismatch with an explicit compatibility decision; preserve discriminant stability for existing codes and document any new ones.
3. Build a complete failure-path matrix for settlement guards and invalid inputs, asserting exact discriminants rather than only “failed”.
4. Add explicit regression coverage proving contract-controlled rejection paths resolve to typed contract errors rather than accidental Rust panics.
5. Update `docs/escrow/errors.md` and `docs/escrow/settlement.md` with every relevant trigger/code.
6. Gate with:
   - `cargo fmt --check`
   - `cargo clippy --all-targets -- -D warnings`
   - `cargo test`
7. Keep the PR narrowly scoped and use `Closes #449`.

## Assignment gate

Do **not** begin assignment-dependent upstream implementation until the GrantFox / maintainer assignment state permits it. A provider application or GitHub comment is not assignment.

## Durable Slack claim

Claim thread: https://tokenjunkielabs.slack.com/archives/C0BVANHNB26/p1789854755061409?thread_ts=1789854650.659969&cid=C0BVANHNB26

This packet exists so a later worker can resume from verified source state without repeating the census.
