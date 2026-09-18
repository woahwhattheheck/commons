# SOL-ASTRA — Hive050 remote-close task-ID type repair

Operation: `HIVE050-REMOTE-CLOSE-TASK-ID-TYPE-REPAIR-20260909-01`

Source: merged PR #11266 (`Hive050: make remote close confirmation one-way`). Independent post-merge review: GitHub review `5160497544`.

## Reproduced defect

`mark_sold()` allocates close-task IDs as positive integers from the persisted `next` counter. `confirm_remote_close()` previously accepted any `task_id` value and resolved tasks with Python equality. Because `bool` is a subclass of `int`, `task_id=True` compares equal to integer task ID `1`; under a fresh request ID this is a distinct payload that can confirm the wrong integer task rather than an idempotent replay.

## Repair

- Require `type(task_id) is int` and `task_id > 0` before opening the write transaction.
- Regress `True`, `False`, string, float, `None`, zero, and negative IDs as fail-before-write/no-mutation cases.
- Preserve the valid positive-integer confirmation path, exact request-ID replay, first-confirmation-only operator note, SOLD local-active removal, duplicate-safe pending close tasks, and local-only/no-network behavior.

## Exact publication base

Fresh main at composition: `be045b70a605681ace1654da6c877deb49e61dea`, tree `4f8519ff626580aac3fd14ffe347e443a08b057c`.

Preimage blobs:
- `revenue/hive/resale-workspace/resale_workspace.py`: `e2b4068a28ab4f0ab699397fad84ef2d4616e821`
- `revenue/hive/resale-workspace/test_resale_workspace.py`: `60da6c30e41d7a90611fbdef928fe32d8d912eab`

Candidate blobs:
- source: `6e907f7a7f2296fc54b01c38ce021e09fe93ae37`
- test: `11087755898127b14f61f3ce8e7e62f07a0befcf`

No marketplace/provider/customer/account/network/spend/deployment action and no force-push. External remote-close confirmation remains an operator-recorded local state only.
