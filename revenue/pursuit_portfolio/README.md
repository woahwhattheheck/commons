# Pursuit Portfolio Allocation

`pursuit_portfolio` is offline owner-review control for finite proposal, research, engineering, and partner-development capacity. It chooses an exact deterministic feasible subset from owner priorities and capacity. It does **not** estimate win probability, buyer intent, pricing, staffing, award status, cash, or recognized revenue.

## v2 trust boundary

Version 2 deliberately removes upstream readiness from portfolio-authored opportunity rows. A portfolio caller may supply owner planning facts, but it cannot mint `READY` or `CURABLE`.

Upstream state and evidence time come from a **separate upstream authority generation**. Each authority row binds:

- `opportunity_id`;
- `revision`;
- `source_sha256`;
- `upstream_receipt_sha256`;
- `upstream_state` (`READY`, `CURABLE`, `HOLD`, or `TERMINAL`); and
- `evidence_captured_at`.

The normalized authority object is SHA-256 addressed. `compile` and `verify` both require the same trusted digest as an independent argument. The digest must come from an owner/reviewer or upstream validation path that is independent of the portfolio submitter. `authority-digest` is only a normalization/digest convenience; computing a hash does **not** make an untrusted authority authentic.

If an opportunity is absent from the trusted authority generation, or its revision/source/receipt binding differs, it is `HOLD` and cannot enter the optimizer. Extra caller-authored readiness fields are rejected by the v2 schema.

## Exact objective and bound

At most **20 allocatable candidates** enter the exhaustive solver. The objective is lexicographic and public:

1. maximize total explicit owner `priority_units`;
2. maximize number of allocated opportunities;
3. minimize total pursuit effort units;
4. choose the lexicographically smallest opportunity-ID tuple.

There is no hidden score, probability, expected-value model, or revenue forecast.

## Policy binding

`policy.policy_sha256` is SHA-256 of canonical JSON for the normalized policy object without `policy_sha256`. Canonical JSON is UTF-8, sorted keys, no spaces, and one trailing newline.

## File-generation custody

v2 treats filesystem names as mutable references rather than object identity:

- input files are opened once with no-follow where available, validated with `fstat`, read from that descriptor under the byte bound, and generation-checked again after the read;
- verification opens the compiled directory once and reads all three artifacts relative to the retained directory descriptor;
- publication opens and retains the parent directory generation, creates the output directory relative to that descriptor, retains the new directory descriptor, writes children create-exclusive relative to it, fsyncs files/directories, and confirms visible generations;
- publication never unlinks a visible final pathname during rollback. A late failure deliberately preserves partial publication so a foreign replacement cannot be deleted and the filesystem truth is not erased.

Because partial publication is evidence, retry into a **fresh output directory** after investigating a failed publication.

## CLI

First normalize the upstream authority object and obtain the digest that an independent review path will pin:

```bash
python -m revenue.pursuit_portfolio.cli authority-digest \
  revenue/pursuit_portfolio/example-authority.json
```

For the checked-in example this prints:

```text
d1461d3f25d36a7b7dbb4368f51a9b0ce73363202833a589449e08fe2e02ffe1
```

Compile and verify with that independently retained digest:

```bash
python -m revenue.pursuit_portfolio.cli compile \
  revenue/pursuit_portfolio/example.json \
  revenue/pursuit_portfolio/example-authority.json \
  out/portfolio-review \
  --trusted-authority-sha256 d1461d3f25d36a7b7dbb4368f51a9b0ce73363202833a589449e08fe2e02ffe1

python -m revenue.pursuit_portfolio.cli verify \
  out/portfolio-review \
  --trusted-authority-sha256 d1461d3f25d36a7b7dbb4368f51a9b0ce73363202833a589449e08fe2e02ffe1
```

Production `compile` samples current UTC itself. Tests and deterministic replay may pass a trusted explicit `evaluated_at`; compiled output records that instant and embeds the normalized input plus authority generation so `verify` can recompile exact bytes while still requiring the independent authority digest.

## Allocation states

- `ALLOCATED_READY`: independently-authorized upstream `READY` row selected by the exact owner-capacity optimum.
- `CURABLE_RECOVERY_ALLOCATED`: owner capacity allocated to an independently-authorized `CURABLE` row; this is not submission readiness.
- `DEFERRED_CAPACITY`: otherwise eligible row outside the optimum.
- `HOLD_UPSTREAM`, `TERMINAL`, `DEADLINE_BUFFER_BREACHED`, or `HOLD`: row cannot enter allocation.

Capacity counterfactuals are intentionally narrow. They show what would make one deferred row individually fit against incumbent residual headroom; they do not promise an unchanged global optimum.

## Tests

```bash
python -m unittest -v test_pursuit_portfolio.py
python -O -m unittest -v test_pursuit_portfolio.py
python -m py_compile revenue/pursuit_portfolio/core.py revenue/pursuit_portfolio/core_v2.py revenue/pursuit_portfolio/cli.py test_pursuit_portfolio.py
```

## Authority ceiling

This module is **offline owner portfolio decision support only**. It performs no buyer/partner contact, email/SMS/DM/call, registration, question submission, portal mutation, proposal/bid submission, pricing, staffing assignment, scheduling, signature/certification, contract acceptance, spend, invoice/payment/refund/bank action, award claim, buyer-intent inference, probability/forecast, cash assertion, or recognized-revenue action.
