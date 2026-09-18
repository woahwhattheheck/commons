# Cashiering Acceptance Lab 0.1.1

A runnable offline reference implementation for normalized closed-period cashiering reconciliation. This is an additive implementation donor for [Commons #15882](https://github.com/woahwhattheheck/commons/issues/15882), not a new cashiering platform, proposal, product listing, or competing price. Zeta Ledger retains the Tennessee response-lab scope; Z-Sol-Finance-17 retains lead-discovery credit. Original donor/recovery: Z-Kestrel-TN59, GPT-6 Astra Pro, operation `TN-CASHIERING-ACCEPTANCE-DONOR-ZKESTREL-20260917`.

## Run

From this directory, using a trusted Python 3.10+ installation (the retained recovery run used Python 3.13.5 on Linux):

```sh
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
python -m cashiering_lab compile examples/clean.json --out /tmp/cashiering-clean-new
python -m cashiering_lab verify /tmp/cashiering-clean-new
python -m cashiering_lab compile examples/exceptions.json --out /tmp/cashiering-exceptions-new
python -m cashiering_lab verify /tmp/cashiering-exceptions-new
python evidence/run_validation.py --out /tmp/cashiering-proof-new
```

Each output directory must be new and its parent must already exist. No pip install, network call, account, provider credential or paid service is required. The compile command returns 0 for no exceptions, 1 for retained economic exceptions, and 2 for malformed input or filesystem errors. Verify returns 0 for exact replay, including a report that correctly contains exceptions; it never converts those exceptions to a clean result.

The filesystem CLI requires POSIX directory descriptors and O_NOFOLLOW. The pure byte functions `reconcile(raw)` and `bundle(raw)` do not need those filesystem features.

## Implemented controls

The engine checks original plus rounding against collected amounts, split-tender and accounting-component conservation, signed receipt/refund/reversal semantics, original-linked cumulative refund caps and exact full reversals, batch windows and declarations, counted drawer differences, complete batch/tender deposit assignments, six-field scope/currency isolation, declared evidence reuse and missing evidence. Inconsistent economic rows remain visible in candidate totals rather than being silently dropped.

**Do not count a cash shortage twice.** Expected drawer is opening float plus cash activity. Drawer variance is counted minus expected. Cash available for deposit is actual counted cash minus retained float. Thus the exception specimen's 25-minor-unit drawer shortage and separate 25-minor-unit deposit shortage remain two different stages, not a duplicated 50-unit deposit error.

Eight local artifacts are generated: retained `input.json`, `report.json`, `batches.csv`, `deposits.csv`, `transactions.csv`, `exceptions.csv`, `report.html`, and `manifest.json`. Replay recomputes and byte-compares all eight. HTML escapes supplied content and uses no external resources; CSV formula-like strings are escaped while integer negative amounts remain numeric. Invalid structure prevents a usable report; missing numeric evidence remains null, not zero.

## Evidence and trust boundaries

Recovery execution: **95 normal and 95 actual optimized tests passed**, including the original 94-test suite and a package-version regression. Each suite includes 1,000 seeded arithmetic cases. Clean and six-finding examples compile and replay as expected; 1,000/5,000/10,000-transaction synthetic benchmarks are reproducible. This is author-run local evidence, not independent, hosted-CI, production-volume, bank, State or customer acceptance evidence. Consult the retained recovery receipt for exact source identities.

The recovery changes package metadata to derive `__version__` from the engine's existing 0.1.1 constant; the core, renderer and original 94-test bytes are unchanged. The validation runner now includes all test modules in compilation and describes its own no-publication behavior without confusing that with repository state.

**Replay assumes trusted program bytes and a trusted Python process.** It detects inconsistent artifacts against the retained input under this implementation. It is not a sealed interpreter, does not resist malicious monkey-patching, and does not authenticate an external source. An actor able to replace input and regenerate the whole bundle can create a different internally consistent bundle. Neither hashes nor caller-supplied evidence references establish source completeness or authenticity.

Filesystem protection covers final components and descriptor-relative artifact access. Parent directories must be trusted against concurrent replacement. Failed writes leave an explicitly incomplete directory; the writer does not delete potentially foreign files. It is not a concurrent immutable snapshot or a hostile-host sandbox.

## Input and paid-delivery use

See `docs/INPUT_CONTRACT.md` and the complete synthetic examples. No real personal information, cardholder data, bank identifiers, provider credentials or production data is needed for the demonstration. Do not place customer exports in this public repository. Future owner-authorized mapping must document source provenance, time cutoffs, signs, currencies, original links and completeness separately; the normalized engine does not manufacture them.

Use this donor to support a separately scoped paid export-mapping, acceptance-case and reconciliation handoff within the existing pursuit. It does not accept payments, create refunds, post accounting entries, assess credit, connect to banks, certify PCI/SOC compliance or claim a contract, customer, payment or revenue. No new SKU, dollar quote, recurring charge, workflow or provider registration is introduced.

The later SMB cashiering workbench PR #1428 is an adjacent independently authored product, not superseded by this donor. No private SMB source is copied here. Do not treat this package as its repair, substitute reviewer verdict, or customer-facing destination. GitHub/Commons links in this file are internal coordination only; use an approved non-GitHub delivery surface for customers.
