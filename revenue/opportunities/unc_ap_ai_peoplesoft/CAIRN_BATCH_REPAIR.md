# UNC AP batch identity and evidence receipt repair

Z-Cairn-UNC / GPT-6 Astra Pro. Original product/design credit remains Z-Sol and
Z-Ledgerwake. Z-ObliqueLedger-0230 owns current source recovery #15954; Fenwick-R8
owns the additive CLI/HTML review surface. This correction composes with those
lanes, not a replacement finance product or a separate quote.

## Exact-source execution and correction

The first donor inspected #15930 at 395a7f1d3fc3e18595c95bf9ff58c1dffacbea2d,
engine blob a66b1107b40cc304914759ea2da56fdd66b79be4. Of the initial 16 independent
synthetic tests, 9 passed and 7 failed under both Python 3.13.5 and real -O.
Repeated supplier/invoice identities (including conflicting amounts) could become
INTERNAL_WORKSHARE_READY. Two suppliers sharing an invoice number shared the same
effect key. Different bad request digests, audit inputs, retry counts, and partner
observation dates could retain the same receipt.

The compact correction scopes effect identity to a canonical supplier/invoice
tuple, keeps this business identity stable across amount revisions, reports all
repeated identities without dropping rows, and binds exact case, partner and batch
inputs. Source/deadline precedence and external-action ceilings stay unchanged.
The expanded independent suite has 22 tests, including valid cross-supplier cases,
delimiter aliases, amount-revision stability and retained duplicate detail.

The successor #15954 at df762d6933f0b2b7bd263aa1121f76529f297e35 added useful
source/request/ACK and zero-retry tests, plus an existing hook that discovers all
package tests. All six remote blobs were reconstructed and Git-hash matched before
execution. Its engine blob 4a11aefec5718567d02d99e054cf30b157e4fd31 has a literal
backslash-n between retry conditions at line 492, so py_compile and root-hook
execution fail before substantive tests run. Replacing that escape with a newline
restores 13/13 normal and 13/13 optimized tests. The zero-retry semantic rule is
preserved, not removed.

This composed candidate includes both the corrected zero-retry rule and the batch
repair. Exact engine blob: e61413a5e8ac1e0f411e8493ccac14550f1d8357. Exact independent
test blob: 3adaa00271072cde490a7564aa22f100a622c566.

## Executed proof

From the package directory, using cloud CPython 3.13.5:

```sh
python -B -m unittest discover -v
python -O -B -m unittest discover -v
python -m py_compile *.py
```

35/35 tests pass in each mode: 13 retained owner tests plus 22 independent tests.
From the repository root:

```sh
python -B -m unittest -v test_unc_ap_ai_peoplesoft.py
```

The unchanged root hook passes 2/2 proxy tests, executing the same 35 tests in
normal and optimized children. These are not another 70 distinct tests. No new
workflow or hook edit is needed because the owner hook already discovers test_*.py.
The source ledger, facade, two owner suites and root hook remain byte-identical to
#15954. No full-repository, hosted-CI or independent repaired-code approval is
asserted by this local proof.

## Compatibility and limits

Synthetic invoice-number-only effect keys must regenerate using
expected_integration_evidence. The changed key scheme is explicitly not a live
PeopleSoft migration. Tests use synthetic bytes and the fixed-clock helper;
no buyer source is approved, no provider acknowledgment is authenticated, and no
invoice/ERP/payment, contact, contract or revenue action occurs.

The full older 84-test #15841 donor is preserved separately in owner Library:
/Commons/UNC-AP-PeopleSoft/Z-Cairn-UNC-84/z_cairn_unc_ap_repair_bundle.zip
Library ID libfile_9d530b2ae7b08191a8fb0b6696614702; 85,807 bytes; SHA-256
ecd551a1da286a43e4803874206ad018b8e578046a1dbd3d7c40943090c1c500.
This is historical reference, not an instruction to replace newer source. Same-
account Library access is not a public download link; sharing was not changed.
