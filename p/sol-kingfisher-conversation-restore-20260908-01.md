from: SOL-KINGFISHER
to: TABLE
kind: SHIP_EVIDENCE
id: sol-kingfisher-conversation-restore-20260908-01
source_task: bm-hive-20260908-005
status: SOURCE_TESTED / PUBLICATION_IN_THIS_CHANGE

# Conversation Desk v1 export restore

Additive recovery operator only. The shipped Conversation Desk remains owned by ASTRA-OSPREY and is unchanged. This increment adds a strict restore path for the existing `conversation-desk-export-v1` download without editing `app.py`, the browser UI, schema, OCR, drafting, or message behavior.

Owned new paths:

- `revenue/hive/conversation-desk/restore_export.py` — Git blob `9628cff3fa331a6397cdf41f3b82705b8c95502f`, SHA-256 `96b402d8acbbd343208caaf15a59ec7884e7394ca7ed46b6cabf6c94baa69c46`, 13,901 bytes.
- `revenue/hive/conversation-desk/test_restore_export.py` — Git blob `4cd151e38b070e6503e21cfcbe9bf82e45548f66`, SHA-256 `247087ddd03a64a223b522381948cf3411c0371ebb01ad158636d6732efb0ec2`, 11,569 bytes.
- `revenue/hive/conversation-desk/RESTORE.md` — Git blob `9ab21ec66b03d9fb1d98dc3f829f44b416a60af7`, SHA-256 `7faac0758289ce2ffaa024ad06bc1bb9da2cf1c527dfc8677cb65706cacffedc`, 3,387 bytes.
- this receipt.

Consumed canonical application surface: current shipped `revenue/hive/conversation-desk/app.py` blob `9343f224c66db9fbdfb8baf9745713da83be6e47`. Local integration used a test-only copy of its exact Store/schema, field validator, image validator and export interfaces; that harness is not part of this publication. The focused test is written to import the actual sibling `app.py` when run from the repository.

Executed in this cloud container:

`PYTHONWARNINGS=error::ResourceWarning python3 -B -m unittest -v test_restore_export.py` — 10/10 tests passed in 1.383s, zero skips.

`python3 -m py_compile restore_export.py test_restore_export.py` — passed.

The tests use synthetic text and a synthetic 1×1 PNG only. They exercise real temporary SQLite databases and filesystem publication: export→restore→re-export equivalence for all seven saved fields; exact screenshot bytes/SHA/MIME/name and conversation association/order; empty exports; malformed/nonfinite/wrong-shape JSON; duplicate IDs; invalid saved fields; tampered image bytes/SHA/MIME/size/owner/nested metadata; refusal to overwrite an existing file or dangling link; missing destination parent; CLI success/failure; and eight concurrent restore attempts with exactly one exclusive hard-link winner.

The v1 export contains current saved state, not prior revision history. Restore therefore regenerates IDs, revisions and timestamps and returns explicit old→new ID maps. It validates the complete export before creating a temporary database, replays records only through canonical `app.Store.create` and `app.Store.add_image`, re-exports and verifies semantic equivalence, then publishes the new database without overwrite. No customer chats, external sends, provider actions, deployment, payment, spend, or owner-PC execution occurred.

Slack source claim: `1788869488.302199`. Progress receipt: `1788869856.844679`. Final PR, merge and current-main readback are posted to the source thread after the connected GitHub write sequence completes.
