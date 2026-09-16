# Service Deal Economics Desk

An offline owner-review control for one proposed services deal. The arithmetic layer answers a narrow question: does a proposed price cover the supplied delivery cost/risk model, and does the supplied capacity snapshot show enough unreserved minutes? The **current production layer now answers a second, separate question before it may say READY: did an independently retained host authority authenticate the exact owner policy, scope/cost basis, and capacity snapshot?**

This separation is deliberate. Candidate JSON can carry source references, hashes, and timestamps for arithmetic/replay, but those strings are not authority. A caller cannot make current production READY merely by lowering a margin policy, cheapening labor/external costs, inflating capacity, or inventing fresh-looking hashes/timestamps.

## Two layers

`engine.py` is the deterministic arithmetic/historical layer. It preserves the original cost, reserve, margin, capacity, freshness, and receipt calculations for inspection and regression testing. Its historical `compile_report()` output is **candidate arithmetic only**; direct use of that module is not a current production authorization path. The package namespace exposes it as `compile_arithmetic_report` to make that boundary explicit.

`authority.py` is the current production gate. `compile_current()` first computes the candidate arithmetic, then requires a fixed-host authority registry authenticated with an owner-only HMAC key. Only when both the arithmetic disposition and the independent input authority pass can the top-level current state be `READY_FOR_OWNER_QUOTE_REVIEW`. Missing, expired, tampered, replayed/forked, or subject-mismatched authority fails closed to `HOLD_INPUT_AUTHORITY_UNVERIFIED` while keeping the arithmetic visible for human review. `verify_current_authority()` owns the process clock (`datetime.now(timezone.utc)`); it will not mint `CURRENT_VERIFIED` from caller-selected time, and it refuses a historically valid receipt once process time is past the authenticated `quote_valid_until` bound.

The independently authenticated subject binds:

- the complete owner policy object, including policy generation, margin/risk parameters, evidence identity, and observation time;
- the complete deal scope/cost basis, including scope revision, delivery window, every line-item minute/rate/external cost and evidence identity; **only `target_price_cents` is excluded** because price is the candidate decision variable the desk is meant to test;
- the complete capacity snapshot, including window, total/reserved minutes, evidence identity, and observation time.

## Arithmetic

For each line item:

`labor cost = ceil(planned_minutes * internal_rate_cents_per_hour / 60)`

Then:

- direct cost = labor + explicit external cost;
- risk reserve = `ceil(direct_cost * risk_reserve_bps / 10000)`;
- loaded delivery cost = direct cost + reserve;
- minimum price = the smallest integer-cent price satisfying the policy gross-margin floor;
- available capacity = supplied total minutes - already-reserved minutes;
- proposed demand = exact sum of line-item minutes;
- capacity shortfall = positive excess demand only.

Candidate arithmetic still fails closed on stale/future evidence, currency/window mismatch, capacity overdraw, insufficient margin, insufficient capacity, invalid types, duplicate keys/IDs, and unsafe file ingress/egress.

## Fixed-host authority

Production current authority is intentionally not selected by CLI arguments or environment variables. On POSIX, the OS account home comes from the account database (`getpwuid`), not `HOME`. The fixed trust root is:

`~/.config/commons/service-deal-economics/`

with three retained files:

- `authority-key.json` — schema `commons.service-deal-economics.authority-key/v1`, containing exactly `schema` and a 32-byte lowercase-hex `key_hex`; owner-only permissions are required;
- `current-authority.json` — schema `commons.service-deal-economics.authority/v1`, containing generation, issue/expiry timestamps, the three exact subject roots, and `mac_sha256`;
- `authority-floor.json` — schema `commons.service-deal-economics.authority-floor/v1`, containing the current generation, the **canonical** registry SHA-256, and its own `mac_sha256`.

Both MACs are HMAC-SHA256 over canonical JSON excluding the `mac_sha256` field. The floor prevents swapping only the current registry to an older or same-generation fork. The OS-account trust root remains the administrative boundary: provisioning/rotation is deliberately out-of-band and there is **no repository command to mint a key, select an authority path, or sign candidate input**.

The implementation rejects symlinked trust paths, non-regular/bounded-file violations, owner mismatch, non-owner-only key permissions, duplicate JSON keys, malformed schemas/digests/timestamps, registry MAC failure, floor MAC failure, floor generation/root mismatch, not-yet-valid/expired authority, and any subject mismatch. Platforms without the required POSIX account/file semantics fail closed rather than falling back to a caller-controlled home path.

## Current CLI

Production owns current UTC and fixed trust paths. There is no `--as-of`, `--authority`, `--key`, or provisioning subcommand.

```bash
python -m revenue.service_deal_economics.cli compile input.json current-report.json --markdown current-report.md
python -m revenue.service_deal_economics.cli verify input.json current-report.json
```

`compile` exits successfully only for top-level `READY_FOR_OWNER_QUOTE_REVIEW`; otherwise it writes the inspectable HOLD packet and exits nonzero. `verify` revalidates the historical receipt, authenticates the embedded historical registry, reloads the current fixed-host registry/floor, and detects authority supersession, current authority failure, candidate drift, or report tamper. A new authority generation or a different canonical registry root makes the old current receipt stale even when arithmetic is unchanged.

## Authority ceiling

READY is still owner decision support only. All external authority remains mechanically false: no buyer contact, quote send/commitment, buyer acceptance, capacity reservation, staffing commitment, signed contract, payment, cash, or booked/recognized revenue. The desk does not allocate capacity across deals; the separate capacity-allocation control owns that problem.

## Tests

The original arithmetic suite remains intact. `test_authority.py` adds hostile coverage for candidate-only READY, forged owner policy, cheapened cost basis, inflated capacity, retimestamp/rehash attempts, target-price separation, registry/floor MAC tamper, same-generation fork, generation supersession, expiry/future authority, report reseal, missing authority history, key rotation, key permissions, symlink ingress, package/CLI escape hatches, and canonical registry identity. `test_quote_expiry.py` proves exact-before / exact-equality / +1 second quote-window behavior, future-receipt refusal, quote-field tamper invalidation, process-clock public verification, and falsey-authority refusal of `CURRENT_VERIFIED`. CI runs the suites normally and under `python -O` on Python 3.11 and 3.12.
