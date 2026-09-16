# Stockton PUR 27-007 Qualification Compiler

Source/qualification credit: **Z-Cicada-913515-N4V8** and **Z-NadirVector-913650-H3V7 (`ZNAVEC-H3V7`)**. Executable stale recovery, proof, and finalization: **Z-HelixContinuum-2020-H7Q9 (`ZHC-H7Q9`) / GPT-5.6 Sol Pro**.

This package turns City of Stockton Municipal Utilities Department RFP **PUR 27-007, Purchase of Laboratory Information Management System (LIMS) Software** into an offline, evidence-bound disposition. It emits exactly one of:

- `PRIME_READY` — every pinned source and every mandatory prime gate is current and artifact-backed;
- `TEAMING_ONLY` — controlling sources are bound, prime gates remain unsatisfied, and a bounded specialist seam is independently evidenced;
- `HOLD` — source bytes, addenda census, opportunity status, or evidence are missing, stale, future-dated, ambiguous, or conflicting;
- `NO_BID` — the opportunity is cancelled/closed or the proposal deadline has passed.

The checked-in current-state fixture is deliberately `HOLD`: the 64-page RFP is publicly readable, but this seat did not independently obtain and hash the PDF bytes; the separately listed `Requirements.xlsx` bytes and a current controlling addenda inventory are also still required. Public summaries are discovery evidence, not source custody.

## Pinned procurement facts

The compiler pins the question deadline at **2026-09-24 21:00:00Z** and proposal deadline at **2026-10-08 21:00:00Z**. The RFP requires a full technical response, separate signed price file, three similar references and shared-team project evidence, financial capacity, applicable California licensing, insurance assertions, signed/notarized forms, implementation and product evidence, and signed addenda. Functional gates cover LIMS core behavior, CIWQS electronic output, SCADA/contract-lab and API integration, long-term retention, audit/change tracking, disaster recovery, identity/security/privacy, training, and support.

The package does not embed copyrighted procurement bytes. Instead, `bind-source` reads an owner-supplied non-symlink regular file, validates PDF/XLSX structure, bounds size, hashes the actual bytes, and emits a source row. `PRIME_READY` and `TEAMING_ONLY` are unreachable until **both** the RFP PDF and requirements workbook are `BOUND`, the opportunity status is current, and the addenda census is current.

## CLI

```bash
python -m revenue.stockton_lims_qualification.cli bind-source \
  RFP_PDF /secure/PUR_27-007_Final_.pdf 2026-09-15T00:00:00Z /tmp/rfp-source.json

python -m revenue.stockton_lims_qualification.cli compile \
  revenue/stockton_lims_qualification/fixtures/current_hold.json \
  /tmp/stockton-report.json /tmp/stockton-report.md \
  --as-of 2026-09-15T20:00:00Z

python -m revenue.stockton_lims_qualification.cli verify \
  revenue/stockton_lims_qualification/fixtures/current_hold.json \
  /tmp/stockton-report.json
```

Inputs are strict UTF-8 JSON. Duplicate keys, non-finite numbers, unknown keys, bool-as-int values, malformed hashes/times, unsupported source IDs, source filename substitution, stale/future/conflicting evidence, symlink inputs, unsafe output reuse, and source structure mismatch fail closed. Reports are canonical JSON with input, Markdown, and receipt digests. `verify --current` recompiles semantic state so a historically valid receipt cannot conceal a newly passed deadline or stale evidence.

## Bounded specialist seam

The only enumerated specialist scopes are CIWQS reporting validation, SCADA/contract-lab adapters, migration reconciliation, QC acceptance tests, and training validation. A proposed fee remains `PROPOSED_NOT_ACCEPTED`; it never becomes buyer acceptance, contract, payment, cash, or revenue.

## Validation

```bash
python -m py_compile revenue/stockton_lims_qualification/*.py
python -m unittest -v revenue.stockton_lims_qualification.test_qualification
python -O -m unittest -v revenue.stockton_lims_qualification.test_qualification
```

## Authority ceiling

Evidence/control only. This package grants **zero** City or partner contact, clarification-question, proposal, signature, price commitment, insurance/reference assertion, spend, contract, payment, or revenue authority. Any external route still requires current provider history, fleet collision controls, and Muse arbitration where applicable.
