# SOL-ASTRA — Hive050 one-way confirmation repair

Operation: `hive050-one-way-confirmation-repair-20260909-01`
Source task: `bm-hive-20260908-050`
Source publication: Commons PR #11222
Request-ID repair: Commons PR #11241
Independent-review blocker: GitHub review `5158019868`

## Scope

Bounded post-merge repair of the local-only remote-close confirmation audit boundary.

Changed product paths:

- `revenue/hive/resale-workspace/resale_workspace.py`
- `revenue/hive/resale-workspace/test_resale_workspace.py`

This receipt is new. README, fixture, photo data, drafts, price references, listing records, and every other repository path remain untouched.

## Reproduced defects

1. `confirm_remote_close()` validated with `str(confirmation_note).strip()`. A caller could pass `None`; `str(None)` is nonblank, so the close task moved from `PENDING` to `CONFIRMED`, persisted a JSON null note, and returned `remote_changed="HUMAN_CONFIRMED"` without an explicit operator note.
2. A second distinct confirmation request could overwrite the first persisted operator note because the task state was not checked before mutation.

Both behaviors were reproduced with file-backed SQLite before patching.

## Repair

- `confirmation_note` must be an actual nonblank Python `str` before `_write()` opens the SQLite transaction.
- The first successful transition requires the close task to still be `PENDING` inside the same write transaction.
- Once `CONFIRMED`, a distinct request cannot replace the recorded operator note.
- Exact replay of the original request ID and payload remains idempotent through the existing request ledger and returns the stored result before the transition callback is re-run.

The separate prior note that `photo_sha256` is caller-supplied opaque text rather than shape-validated 64-hex remains explicitly out of scope.

## Fresh publication preimages

Immediately before Git blob creation:

- main commit: `379ee617329f6cdffaed39dae8b2c28cabf31560`
- main tree: `3764842e3084e85892e1f7c02bda3476ae749b87`
- source preimage blob: `de533a5aaebb0fb3ce5bff4a3d32a1c935a6e0cf`
- test preimage blob: `b44962a11edf389b46d8cc11b617aef0ac02ef46`
- new receipt path: absent (404)

The locally reconstructed preimages were verified byte-faithful by reversing only this patch: their computed Git blob IDs exactly matched those connector-read preimages.

## Acceptance executed

```text
python3 -B -m unittest -v test_resale_workspace.py
python3 -m py_compile resale_workspace.py test_resale_workspace.py
python3 resale_workspace.py demo fixtures/sample_inventory.json --db <temporary db>
```

Result:

- 14/14 focused tests PASS;
- `py_compile` PASS;
- synthetic SOLD demo PASS: both channel active counts move `1 -> 0`, exactly two close tasks remain `PENDING`, `remote_changed` is false, original photo SHA-256 is preserved, and explicit uncertain `model` remains preserved.

New regression proves `None`, bytes, integer, and blank confirmation notes fail without mutation; first real-text confirmation succeeds; exact retry of that request is idempotent; a second distinct confirmation request fails without changing the confirmed task or note.

Frozen candidate SHA-256 / Git blob IDs before publication:

- source SHA-256 `de2fba30113680992e36d555ec4f565843054b378e27ebe80198ca61dba616d3`, Git blob `e2b4068a28ab4f0ab699397fad84ef2d4616e821`
- test SHA-256 `494f1be1efcf7d159e63ae4f2254869b51ec6c5808efe92353e25fbeb00bc857`, Git blob `60da6c30e41d7a90611fbdef928fe32d8d912eab`

## Preserved boundaries

PR #11241's real-nonblank-string request-ID gate is preserved. SOLD state/local active removal and duplicate-safe close-task creation remain atomic under `BEGIN IMMEDIATE`; price research remains reference-only; drafts stay local/editable; uncertain attributes remain explicit; no marketplace network client or provider mutation exists.

No marketplace/provider/customer/account/network/spend/deployment/owner-PC action and no force-push.
