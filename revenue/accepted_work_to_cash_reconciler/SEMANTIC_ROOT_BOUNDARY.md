# Accepted-work-to-cash semantic-root boundary

The reconciler composes the merged `revenue_funnel_control` generation and then adds a narrower owner-action layer. The upstream compiler/verifier identities, source-class policy sets, and the rest of the imported engine generation are therefore authority-bearing code, not caller policy.

## Ordinary module rebinding

Package bootstrap installs a loader wrapper for the exact `revenue.accepted_work_to_cash_reconciler.engine` module before that module executes. After normal module execution completes, the exact module object is converted to a sealed module type. Existing engine globals cannot then be assigned or deleted through ordinary module attribute operations. This includes the upstream compiler/verifier aliases, route and external-acceptance class sets, public compile/verify functions, and their semantic helpers.

The package remains lazy: importing the package alone does not import the engine. Direct submodule import is sealed before control returns to caller code. `python -m revenue.accepted_work_to_cash_reconciler.engine` continues through the normal loader code path without eager-package-import warnings. Ordinary `importlib.reload(engine)` remains supported; import metadata may refresh, source executes again, and the same exact module object remains sealed after reload.

Retained hostile tests attempt to replace the upstream compiler with a forged generation carrying `stage=INVOICED_OR_AWARDED` and `settlement_target_cents=0`, replace the upstream verifier with an always-true verifier, replace public compile functions, and widen external-acceptance/route class sets. Those ordinary rebindings must be rejected before the forged generation can produce a self-verifying `DONE_ZERO_VALUE` or stronger acceptance state. The same root tests run under the repository's normal and `python -O` retained battery.

## Explicit non-claim

This is not a machine-strong sandbox against arbitrary same-interpreter or host takeover. Direct mutation of a module's backing `__dict__`, `sys.meta_path` surgery, custom loader execution, reflective mutation of function defaults/closures/code objects, installed-source replacement, debugger/frame surgery, interpreter replacement, or operating-system/process-boundary defeat are outside this ordinary module-rebinding boundary. Consumers needing resistance to those capabilities require a separately controlled interpreter/process boundary.

The cash boundary is unchanged: retained payment confirmations are not provider authentication; upstream `PAID` still resolves only to `VERIFY_PROVIDER_CASH`; all external-send, Muse-selection, invoice, provider/payment, receivable/accounting, and revenue-recognition authority remains hard false.
