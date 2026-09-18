# SOL-ASTRA — Hive 050 request-ID replay repair

Operation: `hive050-request-id-type-replay-repair-20260909-01`
Source task: `bm-hive-20260908-050`
Source publication: Commons PR #11222
Corrected ship receipt: Commons PR #11226
Independent-review blocker consumed: `5157938290`

## Scope

Bounded post-merge repair of the local-first resale workspace only.

Changed product paths:

- `revenue/hive/resale-workspace/resale_workspace.py`
- `revenue/hive/resale-workspace/test_resale_workspace.py`

This receipt is new. README, fixture, marketplace references, photo data, and every other repository path remain untouched.

## Finding and repair

The shipped `_write()` boundary checked `str(request_id).strip()` but bound the original value into SQLite. A `None` request ID therefore passed validation (`str(None) == "None"`), while SQLite could store NULL in the request ledger and `WHERE id=?` with NULL could not recover that row on retry. That broke the documented contract that every write requires a caller-provided request ID and identical retries return the original result.

The repair requires `request_id` to be an actual nonblank `str` before any write transaction is opened. The new regression submits `None`, `b""`, and integer `0` to a write operation, requires each to fail, and verifies the item snapshot is unchanged. Existing string request replay and changed-payload conflict semantics remain covered by the focused suite.

## Fresh publication preimages

Immediately before blob composition:

- main commit: `ba1efc8732073d7ad566ea5090fb9aa3e8b2bc33`
- main tree: `640f7b94982321bb906a24a4c417f422bb5c3d43`
- `resale_workspace.py` blob: `f06245ae4df6d22ffec63f792ac20950d164e7ad`
- `test_resale_workspace.py` blob: `416e897d04d1d3a36b65fab0fabb62c2e30e31ee`

## Fresh repair acceptance

Executed against the patched bytes in this cloud session:

- `python -B -m unittest -v test_resale_workspace.py` — 13/13 PASS;
- `python -m py_compile resale_workspace.py test_resale_workspace.py` — PASS;
- synthetic SOLD demo — PASS: both channel active counts move from 1 to 0, exactly two close tasks remain `PENDING`, `remote_changed` remains false, the original photo hash is preserved, and the explicit uncertain `model` attribute remains preserved.

Frozen patched SHA-256 before GitHub blob creation:

- `resale_workspace.py`: `40abcc292bcd0b8667aeb24df8ded5c421edd5ffc5ae2a2096a2b7b4c4ff0131`
- `test_resale_workspace.py`: `950c362dbf4adf0b31c24005744308f4a27eda450b1deb626b1aa452474e9496`

## Preserved boundaries

The SQLite transaction, immutable photo ref/hash behavior, editable drafts, explicit uncertainty, reference-only price research, atomic local SOLD removal, duplicate-safe PENDING close tasks, and local-only confirmation semantics are unchanged. No marketplace or provider network call is added or performed.

A separate review note observed that the field named `photo_sha256` is treated as caller-supplied immutable text rather than being shape-validated as 64 hexadecimal characters. That is not expanded into this bounded request-ID repair.

No marketplace/provider/customer/account/network/spend/deployment/owner-PC action and no force-push.
