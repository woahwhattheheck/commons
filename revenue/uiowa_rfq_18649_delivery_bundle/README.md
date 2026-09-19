# Reproducible analyst-handoff delivery bundle

An offline transport component for the existing RFQ 18649 workbench. It preserves
an exported draft and its accompanying inspection report as **exact input bytes**,
validates their cross-references, and creates a deterministic four-member ZIP.
It changes neither workbench state nor parent-compiler scoring or evidence authority.

## Run a complete synthetic rehearsal

Python 3.10 or newer; standard library only. From the repository root:

```sh
python -m revenue.uiowa_rfq_18649_delivery_bundle.examples /tmp/uiowa-bundle-example
python -m revenue.uiowa_rfq_18649_delivery_bundle.bundle pack \
  --report /tmp/uiowa-bundle-example/report.json \
  --handoff /tmp/uiowa-bundle-example/handoff.json \
  --output /tmp/uiowa-bundle-example/draft.zip
python -m revenue.uiowa_rfq_18649_delivery_bundle.bundle verify \
  /tmp/uiowa-bundle-example/draft.zip
```

Use a fresh directory and output filename. The generator and pack command do not
replace existing material. The example is explicitly `SYNTHETIC_UI_DEMO_NOT_COMPILER_OUTPUT`;
its fictional receipt and source digests are not compiler receipts or University evidence.
The output includes three held security cells and nine non-authoritative cells, with
all twelve analyst dispositions present. Nothing is promoted to an assessed score.

For an actual operator export, select the matching inspection report and the
`uiowa-rfq18649-analyst-handoff-draft/v1` JSON exported by
[`../uiowa_rfq_18649_workbench/`](../uiowa_rfq_18649_workbench/). The same `pack`
command accepts them. First run the parent compiler's own `verify` command for
semantic receipt integrity; this component does not reimplement or replace it.
The parent compiler's untrusted path also accepts synthetic source fixtures;
a false or absent `synthetic_demo` marker does **not** certify that input data is real.

## What the archive contains

| Member | Meaning |
|---|---|
| `report.json` | Exact report bytes, including original whitespace and Unicode. |
| `handoff.json` | Exact exported note/disposition bytes. |
| `README.txt` | Generated classification and verification limits. |
| `manifest.json` | Versioned schema, report binding, explicit authority ceiling, byte lengths, and SHA-256 of each other member. |

Members are sorted. ZIP storage is uncompressed, with a fixed 1980 timestamp,
regular-file metadata, no ZIP64 and no extra files. Identical inputs produce
identical archives; JSON whitespace changes intentionally change the archive digest.
Verification does not extract files, invoke a browser, execute contents, or access a network.
The format rejects duplicate/unknown/missing members, noncanonical metadata,
trailing bytes, compression, oversized input, malformed JSON, duplicate JSON keys,
non-finite numbers, and unpaired Unicode surrogates. Inputs are limited to 1 MiB each.

The draft must retain the report receipt, mode, aggregate state, UI-demo marker,
and all twelve ESS/RIS/IAM-by-assessment-area identities and statuses. Cell order
may vary; cell identity may not. Unsupported disposition values and any missing,
truthy or non-boolean authority flag fail with a stable error code.

## Verification is deliberately narrow

`PACKAGING_INTEGRITY_VERIFIED` means **byte integrity and handoff cross-references**.
It does not mean an authentic source, accurate finding, defensible rating, complete
report, confidentiality approval, current evidence, buyer/prime acceptance,
submission permission, contract, invoice, payment, or recognized revenue.
The returned receipt explicitly records `parent_compiler_receipt_recomputed: false`
and keeps the seven workbench authority flags false.

Self-contained hashes can be recomputed by someone replacing an entire bundle.
An independent digest detects that replacement:

```sh
python -m revenue.uiowa_rfq_18649_delivery_bundle.bundle verify draft.zip \
  --expected-sha256 YOUR_INDEPENDENTLY_RETAINED_64_CHARACTER_LOWERCASE_SHA256
```

Obtain that expected hash separately through a trusted channel, not from the same
untrusted archive. Without it, `independent_digest_match` is `null`, not `true`.
A legitimate new draft requires a new independently retained archive digest.
Neither path establishes source authenticity or an approval signature.

The CLI reads ordinary local files and exclusively creates its output. It is not
a hardened shared-host custody service: it does not claim descriptor-relative
no-follow protection against concurrent hostile filesystem mutation. Use a
private analyst working directory with appropriate filesystem permissions.
Never place real University, prime, credential or other private evidence in the
public repository or public demonstration. This program does not provide redaction,
classification approval, encryption, or a distribution service.

## Acceptance and CI

```sh
python -m unittest -v test_uiowa_delivery_bundle.py
python -O -m unittest -v test_uiowa_delivery_bundle.py
python -W error::ResourceWarning -m unittest -v test_uiowa_delivery_bundle.py
```

The root shim enrolls the 43-case suite in the existing root test battery without
modifying any workflow. Tests exercise exact-byte preservation, deterministic builds
under different Python hash seeds, a separate-directory recipient round trip,
receipt/cell mismatches, all authority flags, strict JSON, corrupt archives,
manifest tampering, independently anchored whole-bundle replacement, and no overwrite.
Normal and optimized interpreters use the same explicit validation, not `assert`.
These are transport tests, not a claim of browser acceptance or parent-compiler execution.

## Integration boundary and next assembly step

This is the transport foundation for UIOWA-040, **not the complete report-bundle
assembly work order**. Evidence-register documents, findings, roadmap, source
locators and review-to-finding dispositions must be assembled and resolved by
their existing producers before the complete delivery is declared ready.
Do not append those files to this v1 ZIP: its exact member set is intentional.
A versioned higher-level assembler can embed this verified transport object while
preserving the distinct evidence and review schemas. The workbench and compiler
remain the authoritative interfaces for their own outputs.

Source interface references inspected during implementation:
[`workbench/app.js`](../uiowa_rfq_18649_workbench/app.js),
[`workbench/index.html`](../uiowa_rfq_18649_workbench/index.html), and
[`workshare/compiler.py`](../uiowa_rfq_18649_workshare/compiler.py).
Operation: `uiowa-delivery-bundle-kestrel73-20260919`; seat ZZ-KESTREL-73 / GPT-6 Astra Pro.
