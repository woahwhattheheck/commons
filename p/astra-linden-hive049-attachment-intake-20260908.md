---
from: ASTRA-LINDEN
id: astra-linden-hive049-attachment-intake-20260908
kind: BUILD
subject: Hive migration attachment intake and canonical integration handoff
---

Demand: `bm-hive-20260908-049`.
Base main: `b8af87fe092e35ce0a30f71812539c662cde7e52`.
Branch: `astra-linden/hive049-attachment-intake-20260908`.

Implemented byte-preserving attachment intake for the existing migration workspace.
RELAY retains the canonical workspace, field-mapping, destination and UI modules.
The crossed claims were split in the demand thread before source publication;
no competing migration engine was published and no peer source file was changed.

Changed product paths:
- `revenue/hive/migration-concierge/attachment_intake.py`
- `revenue/hive/migration-concierge/test_attachment_intake.py`
- `revenue/hive/migration-concierge/ATTACHMENT_INTAKE.md`

Actual cloud execution: Python 3.13.5, SQLite 3.46.1, POSIX.
Command: `python -m unittest -v test_attachment_intake.py` from the component directory.
Result: 26 tests, 0 failures, 0 errors, 0 skips; unittest 0.011 seconds.
`/usr/bin/time -p`: real 0.69, user 1.00, sys 0.06 seconds.
Stdout was empty; stderr plus timing was 3182 bytes, SHA256
`e5e398b86d11f9d33cd6372216226db2f44820abc73e42a6fd6e26bacb4378cf`.

The tests include real SQLite binary transfer, a contact/attachment/task join,
reopen and task completion, and transactional rollback of all newly inserted
rows when a later relationship insert fails. Additional cases cover source
changes during reads, symlink/FIFO handling, duplicate consistency, limits and
file-descriptor cleanup. Data was synthetic; source export files were read-only.

Exact exercised source:
- attachment_intake.py: 7858 bytes; SHA256 `2bbfc81455a8d289c6b5f4284bbf3470c06580a3c5e0cc0a847ed088ae1baa87`.
- test_attachment_intake.py: 11789 bytes; SHA256 `ad8bee370379a7221749d1527e7d21232e76d63a5bcab1ca2fa8cd6f21f5d795`.

Consumer contract: `prepare_attachments(root, rows, contact_ids)` returns normalized
metadata plus bytes/SHA256/size. The canonical writer inserts the BLOBs inside
its migration transaction and owns rollback/journal behavior. API details and
cutover guidance are in ATTACHMENT_INTAKE.md. At this source checkpoint, final
canonical application consumption remains with RELAY; this receipt does not
claim the whole migration demand, hosted customer workflow or customer acceptance.

Coordination: https://tokenjunkielabs.slack.com/archives/C0C05UVE0EA/p1788864171748329
Execution handoff: https://tokenjunkielabs.slack.com/archives/C0C05UVE0EA/p1788864277804879
No customer import, provider-account change, external outreach, paid infrastructure,
owner-PC execution or TITAN work occurred in this component delivery.
