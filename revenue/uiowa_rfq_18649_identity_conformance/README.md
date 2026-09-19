# Incremental-import identity conformance — UIOWA-103

Synthetic preparation only. This library tests an identity mapper; it is not a
second production mapper and produces no University findings or maturity scores.
Owner: ZZ-CIRRUS / GPT-6 Astra Pro. Operation: `uiowa-103-cirrus-20260919`.

## Run the driver tests

From the repository root, with Python 3.10 or newer and no third-party packages:

```sh
python -m unittest discover -s revenue/uiowa_rfq_18649_identity_conformance/tests -v
python -O -m unittest discover -s revenue/uiowa_rfq_18649_identity_conformance/tests -v
```

Fifteen tests exercise the eight conformance cases against explicitly named test
doubles and verify the source-bound loader. Seven injected defects cover positional IDs, delimiter collisions,
Unicode normalization, last-row-wins duplicates, ambiguous guesses, discarded
payloads and manufactured references. An exception-only target must fail every
case. These unit results validate the driver and loader; the separate canonical run below exercises the real mapper.

## Connect the actual mapper

Implement `adapter(data) -> Projection` and call `conformance.run(adapter)`.
The neutral input has `records` and `references` arrays. Each record carries
`origin`, `kind`, `local_id`, `revision`, `synthetic` and a `payload` object.
References have a stable `id` and `target` fields drawn from the four-part key.
An omitted origin is an intentionally unqualified reference, not the empty
origin. Do not change exact identifier spellings during translation.

The returned `Projection` must contain observed production results:

- `records`: four-part original key to the mapper's actual canonical ID.
- `references`: reference ID to the actual resolved canonical ID tuple; empty
  when unresolved. A diagnostic candidate set is NOT a successful resolution.
- `retained`: original key to sorted canonical-JSON strings of payloads actually
  retained by the mapper. Use `encode` on observed retained payloads, not on the
  driver's input to manufacture preservation.
- `diagnostics`: stable observed reason codes and identity/reference identifiers.
- `rejected`: true only when the target actually rejects the supplied input.

Do not synthesize IDs in the adapter, pre-deduplicate conflicts, copy input
payloads into output to hide losses, or translate every exception to success.
If the mapper cannot express a fixture, report the incompatibility explicitly.
`run` returns all eight PASS/FAIL observations and never treats an exception as a
pass. Callers should exit nonzero when `failed` is nonzero.

## Properties

Adding unrelated records, including a lexically earlier namespace, must not
re-key existing records. A new origin with the same local ID must not retarget
an established qualified reference. Forty deterministic permutations test
order independence. Eight incremental batches grow to 512 records while checking
all prior IDs after each append. Delimiter-rich IDs, canonically equivalent
Unicode spellings, case and leading/trailing spaces remain distinct originals.

Conflicting duplicate payloads must either be rejected or retain both versions
with diagnostics and no arbitrary resolved selection. Ambiguous unqualified
references and missing targets must remain unresolved and inspectable. This
battery does not test explicit equivalence semantics or cross-version replay;
those are separate integration responsibilities. It tests exact byte spelling,
not linguistic equivalence of Unicode identifiers.

## Coordination and validation scope

Canonical production mapper: LODESTONE-47, issue #16162, planned path
`revenue/uiowa_rfq_18649_identity_map/`. Published-component adapters and
cross-version replay: QUARTZ-731, issue #16165. This independent battery is
issue #16176; it changes neither occupied component. A real canonical-mapper run
requires its actual published source and an adapter bound to that revision.

The historical driver-only execution receipt is `validation.json` (11 tests at
that point). The completed source-bound execution is `canonical-execution.json`:
15 driver/loader tests in both normal and optimized Python, and all eight
conformance cases against the real canonical mapper in both modes. Canonical
normal/optimized result JSON was byte-identical. This result does not clear
separate equivalence or CLI/output-integrity findings from other reviewers.

## Run against the canonical mapper

After checking out the canonical component in the same repository:

```sh
python revenue/uiowa_rfq_18649_identity_conformance/lodestone_adapter.py
python -O revenue/uiowa_rfq_18649_identity_conformance/lodestone_adapter.py
```

The exact historical target executed for the checked-in receipt was
`6176eb9e74f634c580ca36789296a71e88ee72d7`,
`revenue/uiowa_rfq_18649_identity_map/identity_map.py`, Git blob
`ee97b82d7e198aad99beef961f09b0eee194be48`. To require those exact source bytes:

```sh
python revenue/uiowa_rfq_18649_identity_conformance/lodestone_adapter.py --expect-blob ee97b82d7e198aad99beef961f09b0eee194be48
```

A newer source requires a new execution receipt, not relabeling this one. The
runner prints the observed mapper and driver Git blob IDs. A missing mapper or
pin mismatch returns exit 2; an invariant failure returns 1; a successful
eight-case run returns 0. No missing-dependency skip can become a passing run.

`--mapper /path/to/identity_map.py` accepts a **trusted local Python source**
file, not an uploaded data document or remote URL. The loader executes that
source. Review its origin before use; `--expect-blob` checks the exact bytes
before execution. The target is never downloaded, vendored, or replaced by this
kit, and no dependency is installed.

The adapter translates only input field names and emits stable, explicitly
synthetic fixture locators. It observes actual `IdentityMap.report()` original
records and `IdentityMap.resolve()` selections, returning `occurrence_id` for
revision-bound identity. It never substitutes candidate lists for successful
resolution, hashes input records to manufacture passing IDs, or copies input
payloads into the projected output to conceal data loss. It catches only the
canonical mapper's declared `MappingError` as a rejected input.

