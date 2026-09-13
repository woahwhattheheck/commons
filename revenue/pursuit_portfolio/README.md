# Pursuit Portfolio Allocation

`pursuit_portfolio` is an offline owner-review control for the point where several opportunities can be individually credible while proposal, research, engineering, and partner-development capacity remains finite.

The exact optimizer is intentionally boring: maximize explicit owner priority units, then allocated count, then minimize pursuit effort, then lexicographic opportunity IDs. It does **not** estimate win probability, expected revenue, buyer intent, pricing, staffing, or whether a bid should be submitted.

## Trust split

There are deliberately separate engine and production layers.

- `core.py` is deterministic optimization/replay machinery. Bare core `portfolio.json` / `receipt.json` bytes prove only deterministic engine integrity for supplied rows. They do **not** establish that a caller-authored `READY`/`CURABLE` claim was independently reviewed or that owner planning inputs were host-approved.
- `current.py` contains the authenticated upstream-authority verifier, fresh-current verifier, and descriptor primitives. Explicit-key callables there exist for tests/internal host composition and are not the production authority root.
- `host.py` is the production authority boundary. It reads one fixed owner-retained key location, exposes no caller-selected key path, and emits a second HMAC seal over the **full normalized input digest plus every exact compiled artifact**.
- `publisher.py` publishes only into an already-existing retained directory generation and never deletes visible pathnames on rollback.

This gives two independent bindings with the same retained host key:

1. the upstream-authority HMAC proves the exact READY/CURABLE opportunity generation/state projection; and
2. `host-seal.json` proves the exact full owner-planning generation and compiled package, so priority/effort/buffer/capacity/reserve/policy edits cannot be laundered through recomputed self-hashes.

## Fixed retained host key

Production uses exactly:

```text
~/.config/commons/pursuit-portfolio/authority-key.json
```

The CLI has no `--key`, key positional argument, environment-variable key selector, or candidate-controlled key registry. Tests may patch the module constant; production does not expose that selection surface.

The retained key file is:

```json
{"schema":"pursuit-portfolio-allocation/authority-key/v1","key_id":"owner-root-1","key_hex":"<64 lowercase hex>"}
```

`key_hex` is exactly 32 bytes. On POSIX the file must grant no group/other permissions. The raw key is never copied into portfolio output.

An upstream-authority envelope has schema `pursuit-portfolio-allocation/upstream-authority/v1`, a `key_id`, canonical UTC `issued_at`, exact READY/CURABLE entries, and `hmac_sha256` over canonical JSON of `{entries,issued_at,key_id,schema}`. The authority generation must not be future-issued or predate the evidence it attests to. Its READY/CURABLE set must exactly match the normalized candidate generation; missing, extra, changed, or relabeled rows fail closed.

The authority signer is intentionally outside this candidate-facing compiler. Possession of an unsigned/self-hashed input packet does not mint upstream host authority.

## Host seal

`host-seal.json` uses schema `pursuit-portfolio-allocation/host-seal/v1`. Its HMAC covers canonical bindings for:

- `input_sha256` of the full normalized owner-planning input;
- exact `portfolio.json`, `portfolio.md`, `receipt.json`, `upstream-authority.json`, and `current-receipt.json` byte digests;
- the exact evaluation time; and
- the retained authority `key_id`.

Verification checks this HMAC before accepting the full planning generation, then independently checks upstream authority, deterministic historical integrity, and fresh-current semantics.

## What the optimizer answers

Given authenticated upstream READY/CURABLE rows, non-allocatable HOLD/TERMINAL rows, official deadline evidence, explicit owner `priority_units`, positive pursuit effort units, and owner-declared capacity/reserve policy, it returns:

- `ALLOCATED_READY` for authenticated upstream-ready rows selected by the exact optimum;
- `CURABLE_RECOVERY_ALLOCATED` for authenticated still-curable rows receiving recovery capacity;
- `DEFERRED_CAPACITY` for an otherwise eligible row outside the optimum;
- `HOLD_UPSTREAM`, `TERMINAL`, `DEADLINE_BUFFER_BREACHED`, or `HOLD` for rows that cannot enter allocation;
- exact available/reserve/usable/allocated/headroom facts; and
- narrow per-row capacity counterfactuals.

Those counterfactuals do not promise that changing capacity preserves the same global optimum.

## Objective and bound

At most 20 allocatable candidates enter the exhaustive solver. Larger portfolios fail closed and must be split/reduced by an owner planning horizon.

The objective is, in order:

1. maximize total explicit owner `priority_units`;
2. maximize allocated opportunity count;
3. minimize total pursuit effort units;
4. choose the lexicographically smallest opportunity-ID tuple.

There is no hidden score, ratio, probability, LLM ranking, expected-value model, or revenue forecast.

## Policy binding

`policy.policy_sha256` is SHA-256 over canonical normalized policy JSON without the `policy_sha256` field. In production the normalized input containing that policy is additionally bound by the fixed-host HMAC seal. Silent capacity, reserve, priority, effort, buffer, horizon, or evidence-freshness edits therefore invalidate the trusted package.

## Current-use CLI

Production compile owns current UTC and requires the source, authenticated authority generation, and an **already-existing owner-controlled output directory**. The retained host key is resolved only from the fixed host path above:

```bash
mkdir -m 700 out/portfolio-review
python -m revenue.pursuit_portfolio.cli compile \
  portfolio-input.json upstream-authority.json out/portfolio-review
```

Production verify again resolves the fixed retained host key and performs host-seal verification, historical byte-integrity verification, upstream-authority verification, and fresh-current semantic reassessment. A portfolio that was once allocated but is now stale, outside the planning horizon, or beyond its deadline/buffer does not remain current merely because old hashes still match:

```bash
python -m revenue.pursuit_portfolio.cli verify out/portfolio-review
```

A successful production publication contains six bound artifacts:

- `portfolio.json`
- `portfolio.md`
- `receipt.json`
- `upstream-authority.json`
- `current-receipt.json`
- `host-seal.json`

## Descriptor custody

Current-use file ingress walks every path component without following symlinks, opens the final regular file from the retained parent directory descriptor, bounds the byte count, reads the same descriptor generation twice, and rejects a generation that changes while being consumed.

Publication never creates or replaces the destination directory. The owner must create it first. The publisher opens that exact directory generation through the same no-symlink component walk and creates each final artifact exclusively relative to the retained descriptor. Before success, every visible final pathname must still name the exact inode written by the retained file descriptor. If a later artifact fails, already-published files are preserved and reported as partial publication; the implementation never unlinks a visible final pathname during rollback.

The secure current-use descriptor path fails closed on platforms that cannot provide the required `dir_fd`, `O_DIRECTORY`, and `O_NOFOLLOW` semantics rather than silently downgrading custody.

## Authority ceiling

This module is offline owner portfolio decision support only. It performs no buyer/partner contact, email/SMS/DM/call, registration, question submission, portal mutation, proposal/bid submission, pricing, staffing assignment, scheduling, signature/certification, contract acceptance, spend, invoice/payment/refund/bank action, award claim, buyer-intent inference, probability/forecast, cash assertion, or recognized-revenue action.

`ALLOCATED_READY` under the production current-use path means only that an authenticated upstream-ready generation fits the host-sealed owner planning constraints at the recorded evaluation time and still passes fresh-current verification. It is not submission or spend authority.
