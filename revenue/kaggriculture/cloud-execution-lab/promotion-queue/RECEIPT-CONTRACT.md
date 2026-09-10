# Promotion receipt contract — `titan-promotion-queue-receipt/v1`

A receipt is a single JSON document sealing one promotion attempt. Field
order is irrelevant: the integrity digest is computed over the canonical
encoding (`sort_keys=True`, `separators=(",",":")`, `ensure_ascii=True`,
`allow_nan=False`).

## Top-level fields

| field | meaning |
| --- | --- |
| `schema_version` | `1` |
| `receipt_type` | `titan-promotion-queue-receipt/v1` |
| `receipt_id` | `r-<submission-id>-a<attempt>` |
| `submission_id` | queue submission id (equals the pin id) |
| `attempt` | 1-based attempt number for this submission |
| `created_at` | UTC ISO-8601 sealing time |
| `policy_version` | promotion policy version, e.g. `promotion-policy/v1` |
| `verdict` | `PROMOTE` or `REJECT` |
| `queue_pin` | pin id, input digest, and all named `{sha256, bytes}` records |
| `predecessors` | per slot: name, artifact/games/contract/evidence SHA-256, panel id |
| `comparisons` | per slot: strategy, verdict, gate exit code, report SHA-256, grid, failed checks, aggregate deltas, input hashes, duration |
| `timings` | started/finished timestamps, total and per-slot milliseconds |
| `integrity` | see below |
| `extra` | strategy, exact submitted config SHA-256, and the parent runner's gate-script digest field |

## Queue-pin input set

A valid successor receipt carries the complete variable-arity submission pin.
The fixed records are:

- `candidate_artifact`;
- `candidate_games`;
- `policy`;
- `predecessor_config`;
- `engine_identity`;
- `runner_identity`.

For every predecessor config slot there are exactly two additional records:

```text
predecessor_slot.<base64url-encoded-exact-slot-key>.games
predecessor_slot.<base64url-encoded-exact-slot-key>.artifact
```

The slot token is reversible UTF-8 base64url without padding. The config itself
is also pinned, so each dynamic record has an unambiguous semantic edge back to
its slot and field. The queue rejects missing, extra, legacy six-input, or
otherwise config-inconsistent record sets before invoking a gate.

Each `predecessors.<slot>.games_sha256` and `artifact_sha256` is expected to
match one of the corresponding dynamic queue-pin records. The current receipt
schema embeds the entire queue pin, so adding the dynamic records does not
require a parallel receipt version.

## Integrity

```json
"integrity": {
  "algorithm": "sha256-canonical-json-v1",
  "digest": "<sha256 of the canonical receipt with integrity.digest removed>",
  "prev_receipt_digest": "<digest of the previous attempt's receipt, or null>"
}
```

Verification recomputes the digest from the presented bytes: any edit to
inputs, results, policy version, timings, or metadata invalidates it.
`promote.py receipt <id> --verify` performs this check. Repeated successful or
gate-completed attempts link via `prev_receipt_digest`, forming a
per-submission hash chain.

A run rejected before gate preparation—for example because a predecessor panel
was replaced after submission—does not create a receipt. Its queue attempt
record contains the bounded error, and any previously sealed receipt remains
the submission's `last_receipt`.

## Optional key signature

With `promote.py run --signing-key <keyfile>` (or `ReceiptStore.build(...,
signing_key=...)`), the queue additionally seals each receipt with an
HMAC-SHA256 signature:

```json
"integrity": {
  "algorithm": "hmac-sha256-v1",
  "digest": "<sha256 of the canonical receipt with integrity.digest and integrity.signature removed>",
  "signature": "<hmac-sha256 over the canonical receipt with integrity.signature removed>",
  "prev_receipt_digest": "<digest of the previous attempt's receipt, or null>"
}
```

The signature covers the sealed digest, so a consumer can verify both
integrity and key attribution with `ReceiptStore.verify(receipt,
signing_key=key)`. Keys are raw bytes read from a file the operator supplies;
keys never appear in receipts, logs, or queue state. Without `--signing-key`,
the receipt is tamper-evident but not key-attributed.

## What the receipt does not claim

- It proves declared input co-identity: which candidate, policy, config,
  opaque engine/runner identity files, and predecessor panel/artifact bytes
  were submitted together and handed to the existing queue/gate path.
- It does **not** prove that any games panel was produced by the named
  candidate, predecessor artifact, engine, or runner.
- The `extra.gate_sha256` field is inherited from the parent runner and is not
  a dependency-closed gate/import inventory. It must not be interpreted as
  proof of all executed Python/native/config bytes or protection against gate
  TOCTOU.
- Opaque engine/runner identity files are not authenticated repository trees
  or dependency manifests at this layer.
- Filesystem link/inode/publication defenses and pre/post execution closure
  rehashing are outside this receipt contract.
- `PROMOTE` means only that the submitted candidate panel satisfied the
  submitted policy against the submitted predecessor panels under the invoked
  gate. It is not causal execution proof, a Kaggle submission, a leaderboard
  claim, or release authorization.
