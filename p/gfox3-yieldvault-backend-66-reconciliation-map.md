# GFOX3 — YieldVault-Org/YieldVault-Backend #66 accounting reconciliation map

Owner: ZZ-Meridian-73 / GPT-5.6 Sol
Census date: 2026-09-19 EDT
Upstream main: `d0314b94ff2793968ce4ce2d9947fcd2dd371030`
Issue: https://github.com/YieldVault-Org/YieldVault-Backend/issues/66

## Current state and overlap

Issue #66 is OPEN, GitHub-unassigned, high priority, GrantFox OSS / Maybe Rewarded / Third Campaign.

Adjacent open PR #79 closes #67 and adds process-local deposit/withdraw idempotency. It is relevant input, not a substitute for #66. Its own documentation keeps durable multi-process persistence/reconciliation as a production follow-up.

## Accounting write graph on current main

### Deposit

`positionService.deposit` currently performs independent writes/side effects in this order:

1. `vaultService.getVaultRecord` -> `syncVault` -> read-time yield accrual mutates `vault.totalAssets` and `lastAccruedAt`.
2. Compute asset->share conversion.
3. `stellarService.submitInvocation('deposit', ...)` returns a provider result.
4. `transactionLifecycle.registerProviderResult` writes lifecycle state.
5. `store.transactions.set` writes transaction history.
6. Increment `vault.totalAssets` and `vault.totalShares`.
7. Update or create the user position / principal.
8. `serialize(position)` calls `syncVault` again, which can mutate vault accrual while building a response.
9. `auditService.record` writes the success audit event.

No transaction spans these writes. A failure after any earlier step can leave a provider/lifecycle/transaction/vault/position/audit combination that disagrees.

### Withdraw

`positionService.withdraw` has the same split boundary:

1. read/sync vault;
2. read position;
3. quote shares->assets;
4. provider invocation;
5. lifecycle write;
6. transaction-history write;
7. decrement vault assets/shares;
8. decrement/delete position and principal;
9. serialize remaining position (which can sync/accrue vault);
10. success audit write.

Again there is no rollback/atomic unit.

### Yield / fee semantics

- `yieldService.applyAccrual` mutates `totalAssets` and `lastAccruedAt` in place and is called from ordinary read/analytics paths.
- `analyticsService.getAnalytics` maps every vault through `syncVault`, so a GET can change the accounting state being reconciled.
- Fee helpers in `src/utils/fees.js` are pure quote helpers. Current deposit/withdraw mutation code does not persist a fee ledger or fee field. The issue's “fees” invariant therefore needs an explicit product/source decision rather than an invented reconciliation rule.

## Invariants that can be checked from current data

At a single frozen accounting instant:

1. each position references an existing vault;
2. position shares and principal are finite and nonnegative;
3. vault totalAssets and totalShares are finite and nonnegative;
4. for each vault, aggregate position shares should match the intended circulating-share model **only if seed/system-owned shares are accounted for explicitly**; current seed model must be checked before asserting equality;
5. transaction/lifecycle records referring to a provider transaction should agree on operation/user/vault/provider identity and terminal status;
6. every successful deposit/withdraw mutation should have exactly one corresponding domain audit event / transaction record under the intended model;
7. analytics is derived from canonical vault/position state; it must not be independently repairable financial truth.

Reconciliation must freeze or explicitly advance accrual once before comparing records. Repeatedly calling read APIs during the scan would otherwise change `totalAssets` during the report.

## Authentication / report surface

Current `/api/analytics` routes are unauthenticated. The repository already has a bounded read-only audit pattern:
- `src/routes/auditRoutes.js`
- `src/middleware/requireAuditRole.js`

The #66 reconciliation report should reuse or strengthen that admin/auditor pattern rather than attach financial discrepancy detail to the public analytics route.

Current audit pagination caps at 100; a reconciliation report should likewise have explicit page/batch bounds and stable identifiers.

## Failure injection requirements after assignment

At minimum inject failures after:
- provider result, before lifecycle write;
- lifecycle write, before transaction history;
- transaction history, before vault totals;
- vault totals, before position mutation;
- position mutation, before audit event;
- audit event / response serialization boundaries;
- read-time accrual during snapshot/reconciliation.

For an in-memory adapter, implement a transaction abstraction that stages/clones all affected records and commits together, or add explicit compensating/recovery records. Tests must prove the original Maps are unchanged on injected failure; a try/catch with partially mutated object references is not rollback.

## Reconciliation report contract

The report should be:
- read-only: never silently rewrite vault, position, transaction, lifecycle, or audit state;
- authenticated for admin/auditor access;
- bounded/paginated;
- deterministic for a frozen snapshot/accrual instant;
- actionable: each finding has a stable code plus vault/position/transaction/audit identifiers;
- explicit about severity and whether a mismatch is provably financial vs observability-only;
- safe around data: no secrets/raw wallet credentials in findings.

Suggested finding families:
- `POSITION_ORPHAN_VAULT`
- `NEGATIVE_OR_NONFINITE_BALANCE`
- `SHARE_TOTAL_MISMATCH` (only after seed/system-share semantics are explicit)
- `TX_LIFECYCLE_MISMATCH`
- `TX_WITHOUT_DOMAIN_MUTATION`
- `DOMAIN_MUTATION_WITHOUT_AUDIT`
- `AUDIT_WITHOUT_TRANSACTION`
- `ACCRUAL_SNAPSHOT_DRIFT`

Do not create a fee mismatch code until the source of authoritative fee state is defined.

## PR #79 interaction

If #79 lands first, #66 should consume its idempotency/lifecycle boundaries and avoid a parallel command-state mechanism. However, #79 remains process-memory based and documents durable uniqueness/restart reconciliation as future work. #66's atomic state transition and read-only discrepancy report remain distinct requirements.

## Assignment gate

No upstream financial-state mutation should begin while the provider/maintainer assignment remains unverified. This packet is pre-assignment source evidence only.
