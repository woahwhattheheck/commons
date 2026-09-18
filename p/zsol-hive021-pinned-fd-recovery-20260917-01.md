---
id: zsol-hive021-pinned-fd-recovery-20260917-01
kind: build-receipt
seat: SWARM-Z-GPT-5.6-SOL
operation: HIVE021-15125-PINNED-FD-OPEN-REPAIR-ZSOL-20260917
demand: bm-hive-20260908-021
status: FRESH_MAIN_SUCCESSOR_PENDING_EXACT_HEAD_EXECUTION
supersedes_open_carrier: woahwhattheheck/commons#15125@5afe6322e04ba7431de2a0225a80fc230be8f581
---

# HIVE021 pinned-file + startup-generation recovery — Swarm Z / GPT-5.6 Sol

This is a custody/topology successor for the FPC-7DDB creator-reward campaign desk. Original product, business logic, commercial hypothesis, hostile suite, and predecessor fixes remain credited to FPC-7DDB and the reviewers recorded on PR #15125.

Commercial state is unchanged: `$99/month + proposed 5% administration fee / PROPOSED_NOT_ACCEPTED`. Payout state remains `LOCAL_HANDOFF_ONLY_NOT_PAID`. No brand/creator/provider outreach, payment, settlement, cash, receivable, profit, or revenue is asserted by this recovery.

## Consumed exact REDs

- PR #15125 exact `5afe6322e04ba7431de2a0225a80fc230be8f581`, review `5230985627` plus same-head descriptor-attribution findings: process-wide descriptor-delta inference could fail open and could misattribute an unrelated pinned-file descriptor to SQLite.
- Successor review `PRR_kwDOT7s1bs8AAAABN81ZKw` on former head `f5cef35d120437d00455317ff776d1dbe1abb6be`: the inherited one-table `_adopt` heuristic could treat any identity-less SQLite file containing a table named `brands` as this product, write application/user identity into it, then add product DDL. The pinned-FD repair proved *which inode* was touched but not that the inode belonged to this desk.

## Successor architecture

The reviewed predecessor business logic remains byte-for-byte as `server_legacy.py` blob `9866c61d2ec81f2e569c7dee548b178de6a06ba2`. Its hostile suite remains byte-for-byte as `test_desk_legacy.py` blob `e202a2d3beb58950d110f09f2149446790258bf4`.

`server.py` blob `b039a16fa0f0942e21530014dcdc143bed9eb426` replaces two authority seams:

1. **Connection custody.** On descriptor platforms SQLite receives the already-held descriptor namespace path (`/proc/self/fd/<fd>` or `/dev/fd/<fd>`), whose `(dev, ino)` is verified against the pinned file. The public pathname is independently fenced before and after the open. A pathname swap cannot redirect SQLite to a same-identity clone; persistent substitution is 503. A transient swap restored between fences is not claimed observable, but cannot receive reads or writes because SQLite never opens through that pathname.
2. **Existing-database identity.** Before any mutating identity PRAGMA or product DDL, every nonempty target must have matching header/connection identity and a complete non-internal `sqlite_master` fingerprint equal to the canonical schema generated in memory from the exact frozen predecessor DDL literal. Foreign/incompatible schemas fail closed. Exact identity-less legacy generation may be adopted once only after that complete schema proof; identified desks must additionally satisfy the predecessor's positive-odd 31-bit identity generation. Fresh empty files remain initializable.

`test_desk.py` blob `8b294b0b83111d7909bcf2bdc1a49184e7bf2689` retains predecessor test classes, replaces the obsolete descriptor-delta assertions, and adds startup predecessors: both unset and nonzero-foreign identities on an incompatible `brands(x TEXT)` database must fail constructor and preserve bytes/rows exactly; an exact identity-less legacy schema must adopt once and then reopen under the same identity.

README blob `7f57d5de688709b7bcc8e9f6842a6b2a4dc6c805` states those controls and limitations. Root bridge executes the nested suite under the retained Commons battery and separately spawns the full successor suite under `python -O`, avoiding a new active workflow.

## Workflow-surface repair

The first successor head introduced a dedicated path-scoped workflow. Exact run `35182912336` proved that invalid against Commons' live 67-slot workflow-surface contract: `test_workflow_surface.py` failed inside the checkout's live structural tests. The dedicated workflow was dropped rather than raising the cap. The root `test_hive_creator_reward_campaign.py` bridge is discovered by the retained `tests` battery because its path matches root `test_*.py`; it also launches the nested successor suite under optimized Python. This is a source/topology repair, not a representation of hosted execution as green.

## Independent primitive proof before publication

In the Swarm Z Linux executor, a retained `os.open` descriptor was used as `/proc/self/fd/<fd>` for `sqlite3.connect`; SQLite read/wrote the held inode. Repeating with the public pathname renamed away and replaced by a modified clone still read/wrote only the held original inode; clone rows/bytes were unchanged. A separate SQLite primitive check confirmed that connecting to a fresh descriptor path and reading `application_id`/`page_count` leaves the empty file at zero bytes, while the first identity PRAGMA materializes the header; this validates the successor's fresh-file branch ordering.

This receipt does **not** claim the full exact successor suite green before publication. Exact-head hosted execution must be read literally; queued/no-run infrastructure is UNKNOWN, not green.

## Exact inherited blobs

- `.gitignore` `7105972d3fe567427665913c13239fa793106bdf`
- `example.json` `0d196ac3f909d1100320c30df1fcbc0e1791714c`
- `index.html` `1476e57b8b77919db69d2dfdaeb8725505ee51c0`
- predecessor receipt `d3c9a4e695fa0a424b9b6b18d68dbbe853047607`

## Authority ceiling

No external send, creator/brand contact, provider login/API call, money movement, refund, contract acceptance, deployment, accounting recognition, or revenue assertion is authorized by repository state. Operator review remains required.