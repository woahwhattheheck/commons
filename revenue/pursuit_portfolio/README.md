# Pursuit Portfolio Allocation

`pursuit_portfolio` is offline owner-review control for finite proposal, research, engineering, and partner-development capacity. The deterministic core chooses an exact feasible subset from owner priorities and capacity. It does **not** estimate win probability, buyer intent, pricing, staffing, award status, cash, or recognized revenue.

## Layered authority model

The current implementation deliberately keeps owner planning input separate from upstream readiness authority.

1. `core.py` / `core_v2.py` consume an owner planning input plus a separately normalized v2 upstream-authority generation. The core requires the caller to pin the exact canonical SHA-256 of that authority generation.
2. `current.py` adds a host-key HMAC wrapper around that exact normalized v2 authority generation and owns current UTC for production compile/verify.
3. `floor.py` retains a separately HMAC-protected latest-authority floor. A historically valid signed authority wrapper is not current unless its exact byte digest is the one retained by the floor.
4. `host.py` resolves the production key and floor from the effective POSIX account's operating-system home record, not process `HOME`, and HMAC-seals the exact compiled package plus current floor generation.
5. `publisher.py` publishes only into an already-existing retained output-directory generation and never unlinks visible final pathnames during rollback.

The production layer therefore preserves the v2 invariant that portfolio callers cannot mint readiness fields in the source while also adding authenticated provenance and revocation/supersession.

## Core v2 upstream authority

The inner authority uses schema:

```text
pursuit-portfolio-allocation/upstream-authority/v1
```

It contains exactly:

- `schema`;
- positive integer `revision`;
- canonical UTC `generated_at`; and
- `rows`, each binding `opportunity_id`, `revision`, `source_sha256`, `upstream_receipt_sha256`, `upstream_state`, and `evidence_captured_at`.

`upstream_state` may be `READY`, `CURABLE`, `HOLD`, or `TERMINAL`. These fields do **not** live in the owner planning source. The core canonicalizes this object and computes `upstream_authority_sha256`; deterministic compile and historical replay require that exact digest.

## Host-signed authority wrapper

Production does not accept a bare digest as the root of trust. It consumes a host-signed wrapper using schema:

```text
pursuit-portfolio-allocation/signed-upstream-authority/v1
```

The wrapper contains exactly:

- `schema`;
- fixed `key_id`;
- canonical UTC `issued_at`;
- `upstream_authority`, containing the exact normalized core v2 authority object above; and
- `hmac_sha256` over canonical JSON of the unsigned wrapper fields.

The wrapper is rejected when the key ID differs, the HMAC fails, `issued_at` is in the future, or `issued_at` predates the inner authority's `generated_at`.

After wrapper verification, production passes the normalized inner authority and its canonical SHA-256 into the current `core_v2.compile_portfolio(...)` API. It does not reintroduce readiness into source rows.

## Fixed retained host state

On supported POSIX hosts, production derives the account home from:

```python
pwd.getpwuid(os.geteuid()).pw_dir
```

It never uses process `HOME`, `Path.home()`, a CLI trust-root option, or another caller-controlled environment selector.

Under that OS-resolved account home, production uses exactly:

```text
<effective-account-home>/.config/commons/pursuit-portfolio/authority-key.json
<effective-account-home>/.config/commons/pursuit-portfolio/authority-floor.json
```

The effective account home must be an absolute real directory owned by the effective UID and must not be group/world writable. Each retained host-file parent is reopened component-by-component without following symlinks and must itself be effective-UID-owned and not group/world writable. The key and floor files additionally require owner-private permissions.

This closes the predecessor defect where setting `HOME` to an attacker tree containing a self-consistent key, floor, and authority could redirect production trust.

The retained key file is:

```json
{"schema":"pursuit-portfolio-allocation/authority-key/v1","key_id":"owner-root-1","key_hex":"<64 lowercase hex>"}
```

`key_hex` is exactly 32 bytes.

## Latest-authority floor

The retained floor uses schema:

```text
pursuit-portfolio-allocation/authority-floor/v1
```

It contains:

- a positive monotone `generation`;
- `authority_sha256`, the SHA-256 of the exact canonical **signed authority wrapper bytes**;
- fixed `key_id`;
- canonical UTC `updated_at`; and
- `hmac_sha256` over the unsigned floor fields.

The compiler has no floor mutation API. The trusted signer/registrar advances this state outside candidate packet authorship.

Production compile and verify each acquire the floor before/after the current-use operation and fail closed if its retained bytes move during the operation. Advancing the floor from signed generation G1 to G2 invalidates G1 even while G1's HMAC remains historically valid. A same-generation fork also fails because the floor binds the exact wrapper digest.

## Current receipt and host seal

`current-receipt.json` uses schema `pursuit-portfolio-allocation/current-receipt/v2` and binds:

- host authority key ID;
- exact signed-wrapper SHA-256;
- exact inner core-authority SHA-256;
- exact core receipt hash;
- exact normalized input hash; and
- original evaluation time.

`host-seal.json` uses schema `pursuit-portfolio-allocation/host-seal/v2`. Its HMAC binds the signed wrapper, current receipt, exact result/markdown/receipt bytes, evaluation time, retained floor generation, and exact retained floor bytes.

Verification therefore checks both historical byte integrity and fresh-current semantics. A previously allocated opportunity that becomes stale, deadline-breached, held, terminal, or superseded no longer verifies as a current allocation merely because its old package remains internally consistent.

## Objective and bound

At most 20 allocatable candidates enter the exhaustive solver. The objective is, in order:

1. maximize total explicit owner `priority_units`;
2. maximize allocated opportunity count;
3. minimize total pursuit effort units;
4. choose the lexicographically smallest opportunity-ID tuple.

There is no hidden score, ratio, probability, LLM ranking, expected-value model, or revenue forecast.

## Current-use CLI

Production compile requires:

- owner planning input;
- a host-signed v2 authority wrapper; and
- an **already-existing owner-controlled output directory**.

The retained key and latest-authority floor are not CLI arguments:

```bash
mkdir -m 700 out/portfolio-review
python -m revenue.pursuit_portfolio.cli compile \
  portfolio-input.json signed-upstream-authority.json out/portfolio-review
```

Production verify reacquires fixed host state and performs floor verification, host-seal verification, deterministic core replay, signed-wrapper verification, and fresh-current reassessment:

```bash
python -m revenue.pursuit_portfolio.cli verify out/portfolio-review
```

A successful production publication contains:

- `portfolio.json`
- `portfolio.md`
- `receipt.json`
- `upstream-authority.json` — the canonical host-signed wrapper
- `current-receipt.json`
- `host-seal.json`

The floor is deliberately not copied into candidate output; verification reacquires it from fixed host state.

## Descriptor custody

Current-use ingress walks every path component without following symlinks, opens the final ordinary file from the retained parent descriptor, bounds the read, consumes the same descriptor generation twice, and rejects changing metadata or bytes.

Publication never creates or replaces the destination directory. The owner creates it first. The publisher opens that exact directory generation through the same no-symlink component walk and creates every final artifact exclusively relative to the retained descriptor. Before success, each visible final pathname must still name the inode written by the retained file descriptor. A late failure preserves already-published files and never path-unlinks them.

The secure current-use descriptor path fails closed on platforms lacking the required POSIX `dir_fd`, `O_DIRECTORY`, and `O_NOFOLLOW` semantics.

## Regression proof

Focused tests cover:

- the v2 source/authority separation;
- signed-wrapper HMAC mutation;
- future/chronologically impossible signed generations;
- current receipt bindings;
- fresh-current stale-allocation rejection;
- latest-floor supersession and same-generation fork rejection;
- host-seal mutation;
- private key permissions and no-follow ancestry;
- fixed host-parent ownership/mode constraints; and
- a subprocess predecessor killer that sets attacker-controlled `HOME` to a self-consistent forged host tree and proves production still derives `HOST_ROOT` from the effective account database.

The canonical `ci/workflow-recipes/pursuit-portfolio.yml` recipe runs the core/current/host/root suites under normal Python and `python -O`, plus `py_compile`. Hosted execution status is reported only from actual provider state; absent runs are not represented as green.

## Authority ceiling

This module is offline owner portfolio decision support only. It performs no buyer/partner contact, email/SMS/DM/call, registration, question submission, portal mutation, proposal/bid submission, pricing, staffing assignment, scheduling, signature/certification, contract acceptance, spend, invoice/payment/refund/bank action, award claim, buyer-intent inference, probability/forecast, cash assertion, or recognized-revenue action.

`ALLOCATED_READY` means only that a currently authenticated upstream authority row fits owner capacity at the recorded evaluation time and survives current verification. It is not submission or spend authority.
