# Pursuit Portfolio Allocation

`pursuit_portfolio` is offline owner-review control for finite proposal, research, engineering, and partner-development capacity. It chooses an exact deterministic feasible subset from owner priorities and capacity. It does **not** estimate win probability, buyer intent, pricing, staffing, award status, cash, or recognized revenue.

## v2 architecture: deterministic core vs production current authority

Version 2 deliberately removes upstream readiness from portfolio-authored opportunity rows. A portfolio caller may supply owner planning facts, but it cannot put `READY` or `CURABLE` into an opportunity row.

Upstream state and evidence time come from a separate upstream authority generation. Each authority row binds:

- `opportunity_id`;
- `revision`;
- `source_sha256`;
- `upstream_receipt_sha256`;
- `upstream_state` (`READY`, `CURABLE`, `HOLD`, or `TERMINAL`); and
- `evidence_captured_at`.

There are two intentionally different APIs:

- `core.py` / `core_v2.py` are deterministic replay primitives. Their explicit `trusted_upstream_authority_sha256` parameter is useful only to a caller that already owns an independent trust root. It does not turn a caller-supplied digest into production authority.
- the package-level API and `cli.py` use `host.py`, which owns the production trust boundary. Production accepts **no caller-selected authority digest, key path, floor path, environment trust selector, or evaluation clock**.

If an opportunity is absent from the current retained authority generation, or its revision/source/receipt binding differs, it cannot enter the optimizer. Extra caller-authored readiness fields are rejected by the v2 input schema.

## Fixed retained host state

Production current-use operations read exactly these host-owned files:

```text
~/.config/commons/pursuit-portfolio/authority-key.json
~/.config/commons/pursuit-portfolio/authority-floor.json
```

The key file uses schema `pursuit-portfolio-allocation/authority-key/v1` and contains a stable `key_id` plus exactly 32 secret bytes encoded as 64 lowercase hex characters.

The floor file uses schema `pursuit-portfolio-allocation/authority-floor/v2` and binds:

- `revision`: the monotone revision already present in v2's normalized upstream authority generation;
- `authority_sha256`: SHA-256 of that exact normalized authority generation;
- `key_id`;
- canonical UTC `updated_at`; and
- `hmac_sha256` over the unsigned floor fields.

On POSIX, both trust-root files must be owner-only. Production consumes them through retained no-follow descriptor generations. Candidate input cannot choose their locations.

The portfolio compiler deliberately has **no API that advances the floor**. A separate trusted owner/signer/registrar changes retained host state outside candidate packet authorship. This separation is required: validating a signed or hashed historical authority is not the same thing as proving it is still current.

### Supersession and withdrawal

Currentness is exact, not merely time-based:

- if retained floor G1 names revision 1 READY authority A, A may be used while all other gates pass;
- if the trusted registrar advances the floor to G2 revision 2 where the opportunity is HOLD/withdrawn, the old G1 package immediately fails current verification even if G1 evidence is still fresh and its response deadline has not expired;
- if two differently hashed authority objects claim the same revision, only the exact digest retained by the host floor is current;
- compile and verify acquire the floor twice and fail closed if retained floor bytes move during the operation.

The floor therefore supplies revocation/supersession semantics that a historical SHA-256 commitment alone cannot provide.

## Host seal and full planning-generation binding

Production compile emits `host-seal.json` using schema `pursuit-portfolio-allocation/host-seal/v3`.

The fixed host key HMAC binds:

- current authority revision and digest;
- exact retained floor-file digest;
- full normalized portfolio input digest;
- exact `portfolio.json`, `portfolio.md`, and `receipt.json` byte digests;
- exact evaluation time; and
- retained key ID.

This prevents a legitimate current READY authority generation from being replayed with rewritten owner priority, effort, deadline buffer, capacity, reserve, horizon, or policy and then laundered through recomputed deterministic core receipts.

Production verify checks the current floor, checks the v3 host seal, performs deterministic historical verification, recompiles at verifier-owned current UTC, compares the decision semantics, and then reacquires the floor before returning success. A historically valid package that is now stale, beyond its deadline/buffer, outside the planning horizon, or superseded is not reported as current.

## Exact objective and bound

At most **20 allocatable candidates** enter the exhaustive solver. The objective is lexicographic and public:

1. maximize total explicit owner `priority_units`;
2. maximize number of allocated opportunities;
3. minimize total pursuit effort units;
4. choose the lexicographically smallest opportunity-ID tuple.

There is no hidden score, probability, expected-value model, or revenue forecast.

## Policy binding

`policy.policy_sha256` is SHA-256 of canonical JSON for the normalized policy object without `policy_sha256`. In production, the complete normalized input containing that policy is additionally bound by the fixed-host HMAC seal.

## File-generation custody

The low-level v2 engine already treats final filesystem names as mutable references rather than object identity. The production host wrapper tightens this further by component-walking the entire path without following symlink ancestors.

Current production behavior:

- candidate input and authority files are opened relative to retained no-follow parent-directory descriptors, byte-bounded, read twice from one file descriptor, and stable metadata is checked across reads;
- key and floor files use the same retained-generation path and owner-only permission checks;
- production output requires an **already-existing, owner-controlled, empty output directory**;
- that directory is component-walked and retained with `O_DIRECTORY|O_NOFOLLOW` semantics rather than created through a candidate-facing pathname;
- output children are created exclusively relative to the retained directory descriptor, fsynced, and their visible inode identity is checked before success;
- publication never unlinks a visible final pathname during rollback. A late failure preserves already-published truth and reports partial publication.

Because partial publication is evidence, investigate a failed output directory and retry into a fresh directory rather than erasing it.

## Production CLI

Create an owner-controlled output directory first:

```bash
mkdir -m 700 out/portfolio-review
```

Compile against the fixed retained key and latest-authority floor:

```bash
python -m revenue.pursuit_portfolio.cli compile \
  revenue/pursuit_portfolio/example.json \
  revenue/pursuit_portfolio/example-authority.json \
  out/portfolio-review
```

Verify historical integrity **and current authority/current-time semantics**:

```bash
python -m revenue.pursuit_portfolio.cli verify out/portfolio-review
```

Production CLI intentionally has no `authority-digest` trust bootstrap and no `--trusted-authority-sha256`, `--key`, `--floor`, or caller-time option. A candidate can still use low-level `core_v2` digest/replay helpers in tests or analysis, but those helpers are not the package-level production authority boundary.

A successful current-use directory contains:

- `portfolio.json`;
- `portfolio.md`;
- `receipt.json`; and
- `host-seal.json`.

The host floor is deliberately reacquired from fixed retained state during verification rather than copied into candidate output.

## Allocation states

- `ALLOCATED_READY`: currently retained upstream `READY` row selected by the exact owner-capacity optimum.
- `CURABLE_RECOVERY_ALLOCATED`: owner capacity allocated to a currently retained `CURABLE` row; this is not submission readiness.
- `DEFERRED_CAPACITY`: otherwise eligible row outside the optimum.
- `HOLD_UPSTREAM`, `TERMINAL`, `DEADLINE_BUFFER_BREACHED`, or `HOLD`: row cannot enter allocation.

Capacity counterfactuals are intentionally narrow. They show what would make one deferred row individually fit against incumbent residual headroom; they do not promise an unchanged global optimum.

## Tests

The host-boundary workflow runs the unchanged v2 optimizer suite together with current-authority hostiles under normal and optimized Python, plus syntax compilation. Focused hostiles include G1 READY -> G2 withdrawal replay, same-revision authority forks, floor HMAC tamper, mid-operation floor movement, fresh-current expiry, full planning-generation host seal binding, ancestor symlink refusal, retained-directory publication, and partial-publication preservation.

Low-level deterministic tests remain available directly:

```bash
python -m unittest -v test_pursuit_portfolio.py
python -O -m unittest -v test_pursuit_portfolio.py
```

## Authority ceiling

This module is **offline owner portfolio decision support only**. It performs no buyer/partner contact, email/SMS/DM/call, registration, question submission, portal mutation, proposal/bid submission, pricing, staffing assignment, scheduling, signature/certification, contract acceptance, spend, invoice/payment/refund/bank action, award claim, buyer-intent inference, probability/forecast, cash assertion, or recognized-revenue action.

`ALLOCATED_READY` means only that the exact current retained upstream authority generation and host-sealed owner planning generation pass current capacity/evidence/deadline policy. It is not permission to contact, submit, commit, spend, collect, or recognize revenue.