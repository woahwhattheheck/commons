# Synthetic technical acceptance plan

Use synthetic or explicitly authorized evidence only. Expected outcomes come from retained partner/buyer rules; this plan does not invent finance policy.

Every test receipt binds scope generation, source evidence generation, configuration/rule generation, fixture identity, operation, expected result, observed result, exception code, verifier version, PASS/FAIL/HOLD, and remediation owner.

## Population/reconciliation cases
1. clean population -> exact count/amount conservation;
2. duplicate logical row -> no silent double count;
3. same ID with changed payload -> HOLD;
4. missing source row -> visible gap;
5. unexpected target row -> visible orphan;
6. mixed period/entity/currency -> reject;
7. malformed amount -> reject before arithmetic;
8. missing evidence generation -> HOLD, not zero;
9. reordered input -> same semantic result.

## Workflow/control cases
1. actor attempts a prohibited transition;
2. eligible actor executes approved transition;
3. inactive or out-of-scope role;
4. role changes between stages;
5. duplicate action;
6. threshold below/exact/above;
7. documented override/delegation;
8. missing required audit event.

## Interface cases
1. normal event produces one reconciled effect;
2. duplicate delivery does not duplicate effect;
3. timeout/unknown result reconciles before retry;
4. response lost after success does not trigger blind replay;
5. partial batch keeps accepted/rejected members distinct;
6. stale schema/config generation remains HOLD;
7. authorization failure has no degraded bypass;
8. reconciliation mismatch blocks readiness.

## Change/exception lifecycle
Configuration generations must be traceable. Inject count mismatch, amount mismatch, duplicate, unknown interface outcome, missing approval trace and unapproved configuration. Each stays OPEN/HOLD until owner-supplied closure evidence exists.

Hard stops include unexplained deltas, identity conflicts, silent coercion, unreconciled external-write state, missing actor/config evidence, unauthorized customer data, or a PASS based only on assertion where objective evidence is required.

Outputs for a contracted engagement may include deterministic JSON receipts, formula-safe CSV exceptions, passive Markdown/HTML, source digests and a replay verifier.
