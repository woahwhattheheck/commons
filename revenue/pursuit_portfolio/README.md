# Pursuit Portfolio Allocation

`pursuit_portfolio` is an offline owner-review control for the point where several opportunities can be individually credible while proposal, research, engineering, and partner-development capacity remains finite.

The exact optimizer is intentionally boring: maximize explicit owner priority units, then allocated count, then minimize pursuit effort, then lexicographic opportunity IDs. It does **not** estimate win probability, expected revenue, buyer intent, pricing, staffing, or whether a bid should be submitted.

## Trust split

There are now two deliberately different layers.

- `core.py` is the deterministic optimization/replay engine. Bare core `portfolio.json` / `receipt.json` bytes prove only deterministic engine integrity for the supplied rows. They are **not** sufficient evidence that a caller-authored `READY` or `CURABLE` claim was independently reviewed.
- `current.py` + `publisher.py` + the CLI are the production current-use boundary. A row may enter the optimizer as `READY` or `CURABLE` only when its exact opportunity/revision/source digest/upstream receipt digest/evidence reference/evidence timestamp/deadline/state projection is present in a separately retained HMAC-authenticated upstream-authority generation.

The authority key is a separately retained 32-byte host secret, represented by an owner-only JSON file:

```json
{"schema":"pursuit-portfolio-allocation/authority-key/v1","key_id":"owner-root-1","key_hex":"<64 lowercase hex>"}
```

On POSIX the key file must not grant group/other permissions. The raw key is never copied into portfolio output.

An upstream-authority envelope has schema `pursuit-portfolio-allocation/upstream-authority/v1`, a `key_id`, canonical UTC `issued_at`, exact READY/CURABLE entries, and `hmac_sha256` over canonical JSON of `{entries,issued_at,key_id,schema}`. The authority generation must not be future-issued or predate the evidence it attests to. Its READY/CURABLE set must exactly match the normalized candidate generation; missing, extra, changed, or relabeled rows fail closed.

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

`policy.policy_sha256` is SHA-256 over canonical normalized policy JSON without the `policy_sha256` field. This detects silent edits to capacity, reserve, planning horizon, and evidence-freshness policy. Policy is still an owner input; the digest is an integrity commitment, not proof that a third party approved the policy.

## Current-use CLI

Production compile owns current UTC and requires the source, authenticated authority generation, separately retained key, and an **already-existing owner-controlled output directory**:

```bash
mkdir -m 700 out/portfolio-review
python -m revenue.pursuit_portfolio.cli compile \
  portfolio-input.json upstream-authority.json owner-authority-key.json \
  out/portfolio-review
```

Production verify requires the retained key and performs both historical byte-integrity verification and a fresh-current semantic re-evaluation. A portfolio that was once allocated but is now stale, outside the planning horizon, or beyond its deadline/buffer does not remain current merely because its old receipt is intact:

```bash
python -m revenue.pursuit_portfolio.cli verify \
  out/portfolio-review owner-authority-key.json
```

A successful current-use publication contains five bound artifacts:

- `portfolio.json`
- `portfolio.md`
- `receipt.json`
- `upstream-authority.json`
- `current-receipt.json`

`current-receipt.json` binds the core input/receipt to the exact authenticated authority generation and key ID.

## Descriptor custody

Current-use file ingress walks every path component without following symlinks, opens the final regular file from the retained parent directory descriptor, bounds the byte count, reads the same descriptor generation twice, and rejects a generation that changes while being consumed.

Publication never creates or replaces the destination directory. The owner must create it first. The publisher opens that exact directory generation through the same no-symlink component walk and creates each final artifact exclusively relative to the retained descriptor. If a later artifact fails, already-published files are preserved and reported as partial publication; the implementation never unlinks a visible final pathname during rollback.

The secure current-use descriptor path intentionally fails closed on platforms that cannot provide the required `dir_fd`, `O_DIRECTORY`, and `O_NOFOLLOW` semantics rather than silently downgrading custody.

## Authority ceiling

This module is offline owner portfolio decision support only. It performs no buyer/partner contact, email/SMS/DM/call, registration, question submission, portal mutation, proposal/bid submission, pricing, staffing assignment, scheduling, signature/certification, contract acceptance, spend, invoice/payment/refund/bank action, award claim, buyer-intent inference, probability/forecast, cash assertion, or recognized-revenue action.

`ALLOCATED_READY` under the current-use path means only that an authenticated upstream-ready generation fits the supplied owner planning constraints at the recorded evaluation time and still passes fresh-current verification. It is not submission or spend authority.
