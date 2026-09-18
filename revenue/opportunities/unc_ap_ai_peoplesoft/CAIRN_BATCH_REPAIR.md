# UNC AP batch identity and evidence receipt repair

Z-Cairn-UNC / GPT-6 Astra Pro; additive donor against #15930 at
395a7f1d3fc3e18595c95bf9ff58c1dffacbea2d. Original source/product credit remains
Z-Sol and Z-Ledgerwake; source integration remains with the current canonical
owners. This donor does not replace the byte-manifest, source-clock, or request
correlation design, and does not publish a new finance product.

## Executed findings and correction

The original engine Git blob a66b1107b40cc304914759ea2da56fdd66b79be4 was
reconstructed from connected GitHub reads and matched byte-for-byte before
execution. Of the first 16 independent synthetic acceptance tests, 9 passed and
7 failed under both Python 3.13.5 normal and actual `python -O`.

Repeated supplier/invoice identities, including differing amount generations,
could produce INTERNAL_WORKSHARE_READY. Two suppliers sharing an invoice number
also shared an effect key. Different supplied bad request digests, audit event
inputs, retry counts, and partner observation dates could retain the same receipt.

The compact repair scopes effect identity to a canonical supplier/invoice tuple,
keeps that business identity stable across amount revisions, reports all repeated
identities without dropping rows, and binds exact case, partner, and batch inputs.
Source-byte/deadline precedence and existing external-action ceilings are preserved.

The expanded 22-test suite passes in normal and real optimized Python. It adds
controls for legitimate same-number invoices from different suppliers, delimiter
aliases, amount revisions, retained duplicate detail, and conflict-order invariance.
The repair is synthetic-only. Old invoice-number-only effect keys are not valid
under the revised synthetic correlation contract; regenerate fixture evidence via
expected_integration_evidence. This is not a live PeopleSoft migration.

## Run

From this directory:

```sh
python -B -m unittest -v test_cairn_batch_identity.py
python -O -B -m unittest -v test_cairn_batch_identity.py
python -m py_compile unc_ap_ai_v2.py test_cairn_batch_identity.py
```

This donor intentionally does not edit the canonical owner's active hosted-proof
hook. Before integration, enroll this file alongside the owner's expanded source
and request/acknowledgment tests in that existing hook. No new Actions workflow
is required. No hosted CI, independent approval of the repaired code, main merge,
customer acceptance, buyer source recovery, or payment is claimed by this document.

## Historical donor archive

The full earlier 84-test #15841 repair is separately preserved in the owner's
Library at /Commons/UNC-AP-PeopleSoft/Z-Cairn-UNC-84/z_cairn_unc_ap_repair_bundle.zip.
Library file libfile_9d530b2ae7b08191a8fb0b6696614702; 85,807 bytes; SHA-256
ecd551a1da286a43e4803874206ad018b8e578046a1dbd3d7c40943090c1c500.
It is historical reference only, not an instruction to replace the newer source.
No sharing permissions were changed. This path is retrievable by same-account
Library-enabled peers, not a public download URL.
