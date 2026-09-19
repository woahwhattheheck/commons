# Preserved original-intake test output

`INTAKE_EXECUTION_LOGS.tar.gz` contains the ten raw stdout/stderr logs referenced
by `INTAKE_EXECUTION.json` and `INTAKE_UNION_EXECUTION.json`. These are local
actual-app/loopback-HTTP tests with an explicitly recording compiler-adapter spy,
not hosted CI, real-parent compiler, or Chromium execution.

Archive bytes: 5370. SHA-256:
`5100c47a0fd89b0868fdece11a676878e1ce31d80b6e0f75091e395f207f76c6`.
Git blob: `3e29ddf16db1d6cab179b99ccc6a59095bf035f6`.

Inspect or unpack into an empty review directory:

```sh
tar -tzf INTAKE_EXECUTION_LOGS.tar.gz
tar -xzf INTAKE_EXECUTION_LOGS.tar.gz -C /path/to/empty-review-directory
```

The archive contains normal.log, optimized.log, resource-warnings.log,
root-normal.log, root-optimized.log, baseline-regressions.log, union-normal.log,
union-optimized.log, union-resource-warnings.log, and union-original-repair.log.
The individual log hashes are recorded in the corresponding execution receipt.
Nine logs show 39/39 passing tests with zero skips. The baseline negative control
intentionally fails with 32 failed assertions/subtests and one error; that is not
a count of independent product defects. Historical source bindings remain
immutable; the union receipt identifies the distinct RAW17/Keystone/Trellis app.

The archived traces may contain local synthetic test paths. They contain no real
University assessment input. Execution credit: ZZ-KESTREL-47 / GPT-6 Astra Pro.
Operation: uiowa-original-intake-kestrel47-20260919.
