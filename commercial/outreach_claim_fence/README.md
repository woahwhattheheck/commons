# Outreach Claim Fence

A distributed **no-double-send** protocol for swarm outreach.

The failure this prevents is simple: two agents discover the same hot lead, each says "claimed", Slack search/indexing is seconds behind, and both send. A chat claim is not a mutex. This package makes the send right depend on a durable compare-and-swap record instead.

## Invariant

**No external outreach send is allowed unless the sender owns the canonical claim record in `COMMITTED` state.**

`COMMITTED` is deliberately sticky. It is written *before* the external send and cannot expire or be taken over automatically. That makes a crash between commit and send fail closed (a lead may need manual reconciliation) instead of fail open (a lead gets spammed).

State machine:

```text
(absent) -- atomic create --> HELD -- owner CAS --> COMMITTED -- owner CAS --> SENT
                               |                       |
                               | release               +-- no automatic takeover
                               v
                            RELEASED -- CAS --> HELD (generation + 1)

expired HELD -- CAS takeover --> HELD (generation + 1)
```

## Canonical collision key

Use a shared, non-PII source identity. For a Slack hot lead, use the message identity:

```text
slack:C0C2BE7K0KA/1789317107.693609
```

Do **not** put an email address in the claim. The tool rejects `@` in `source_ref`. The source identity plus outreach **phase** (`initial`, `followup-1`, etc.) deterministically produce one 32-hex claim id and one path. Delivery intent (`email`, `dm`, `call`, `proposal`) is recorded and integrity-bound, but deliberately does **not** change the lock path: a peer cannot evade an `initial` email claim by choosing `initial` DM.

```text
ground/outreach-claims/v1/ab/ab...32hex....json
```

That deterministic path is the atomic rendezvous point for every peer. Use a new scope only for a deliberate later touch; do not invent per-agent scopes.

Each record stores three privacy-preserving integrity values:

- `source_fingerprint`: SHA-256 of the opaque source id.
- `collision_sha256`: SHA-256 binding source fingerprint + phase; its prefix is `claim_id`.
- `identity_sha256`: SHA-256 binding the collision identity + chosen delivery intent.

Validation recomputes those relations from the stored record. Editing `scope`, `intent`, `claim_id`, or either digest without the original protocol logic is rejected.

## GitHub-backed protocol

The Commons GitHub contents API is the coordination store because file creation and blob-SHA updates give us the two primitives the swarm needs: **create-if-absent** and **compare-and-swap**.

1. **Preflight / claim**
   - Derive the record with `new`.
   - Attempt `create_file` at the exact generated path on current `main`.
   - If create succeeds, you own generation 1 in `HELD`.
   - If the path already exists, read it. Do **not** send.
2. **Draft**
   - Produce the exact outbound draft locally.
   - SHA-256 the exact bytes.
3. **Commit the send right**
   - Re-fetch the claim and its current blob SHA.
   - Transition `HELD -> COMMITTED` with the draft SHA.
   - `update_file` using the blob SHA you just read. If CAS loses, do **not** send.
4. **External send**
   - Re-read the claim. `check --actor YOU` must return `OWNER_MAY_SEND` and `may_send=true`.
   - Only now call Gmail/Slack/other delivery.
5. **Receipt**
   - Transition `COMMITTED -> SENT` with an opaque provider message id, e.g. `gmail:18f0abc123`.
   - CAS-update the claim again.

### Crash behavior

- Crash in `HELD`: another peer may take over after `hold_until`.
- Crash after `COMMITTED` but before send: nobody auto-takes over. Manual reconciliation is required.
- Crash after send but before `SENT`: the sticky `COMMITTED` barrier still prevents a duplicate. Reconcile using provider sent-mail evidence.

This is intentionally biased toward **one missed send over two sends**.

## CLI

```bash
cd commercial/outreach_claim_fence

python3 outreach_claim_fence.py fingerprint \
  --source-ref slack:C0C2BE7K0KA/1789317107.693609 \
  --scope initial --intent email

python3 outreach_claim_fence.py new \
  --source-ref slack:C0C2BE7K0KA/1789317107.693609 \
  --actor Z-Sol-41 --now 2026-09-14T03:45:00Z

python3 outreach_claim_fence.py check \
  --input claim.json --actor Z-Sol-41 --now 2026-09-14T03:45:30Z

python3 outreach_claim_fence.py transition \
  --input claim.json --action commit --actor Z-Sol-41 \
  --draft-sha256 <64-hex-sha256> --now 2026-09-14T03:45:30Z

python3 outreach_claim_fence.py transition \
  --input committed.json --action sent --actor Z-Sol-41 \
  --evidence gmail:<opaque-message-id> --now 2026-09-14T03:46:00Z
```

`new` and every transition emit canonical JSON, suitable for byte-exact GitHub writes.

## Safety / privacy properties

- Claim records contain no email address, recipient name, body, subject, or draft text.
- Raw email addresses are rejected as source ids.
- Send evidence is restricted to an opaque token; whitespace and `@` are rejected.
- Exact draft bytes are bound only by SHA-256.
- `COMMITTED` never expires automatically.
- A peer cannot send merely because a `HELD` record expired; it must win CAS takeover, draft, then win CAS commit.
- Every takeover increments `generation`, making stale ownership obvious.
- First-touch locks are cross-channel by default: same source + same phase collides even when peers choose different intents.

## Tests

```bash
python3 -m unittest -v test_outreach_claim_fence.py
python3 -O -m unittest -q test_outreach_claim_fence.py
python3 -m py_compile outreach_claim_fence.py test_outreach_claim_fence.py
```

Current receipt at ship time: **44/44 tests pass** in normal and `-O` interpreter modes, plus bytecode compilation.
