# Local validation evidence

Builder and separate source-review pass: **Z-Cairn-6F42 / GPT-6 Astra Pro**. This record is local execution evidence, not an independent review or hosted-CI receipt. Publication, reviewer and merge states must be read from the actual pull request.

## Runtime and commands

Observed on 2026-09-18 in this isolated cloud container: Python **3.13.5**, Linux **6.18.44 x86_64**, glibc **2.41**. No owner-laptop execution, bank calls, external data, new packages or new compute spend was involved.

From repository root:

```sh
python -B -m unittest revenue.camt_statement_workbench.test_workbench -v
python -O -B -m unittest revenue.camt_statement_workbench.test_workbench -v
python -B -m revenue.camt_statement_workbench.benchmark --entries 5000
```

Observed focused suite: **59 tests passed normally; 59 passed under actual `python -O`**. The suite includes 200 seeded integer-money oracle cases, real CLI subprocess builds/verification, and optimized-runtime rejection. Coverage includes .02/.08 differences, batch/detail separation, sign/reversal behavior, exact decimal context isolation, dates including nanosecond ordering, pending/proprietary status, currency and balance ambiguity, page/copy/reissue indicators, duplicate bytes/identities/references, raw-source retention, malformed XML/DTD/namespace/choice/singleton rejection, limits, deterministic ordering, output tampering, forged rehashes, manifest/path/symlink/file-set rejection, CSV formulas and escaped HTML.

An initial test assertion about JSON quote escaping was corrected; the implementation preserved the hostile remittance text and escaped its HTML presentation. A later separate review caught datetime's microsecond truncation during nanosecond ordering; exact fractional ordering and a regression test were added before publication. These are repaired local findings, not an assertion that no further defects remain.

## Synthetic scale measurement

`benchmark.py --entries 5000` generated a **1,719,082-byte** source and **9,777,219-byte** review bundle. Observed build time **0.419857 seconds**, verification time **0.521792 seconds**, process peak RSS **158,736 KiB** (Linux `ru_maxrss`). Integer oracle: 5,000 booked entries, net GBP 2,500, matching synthetic closing balance; result PASS. These are one local observation, not a service-level promise, cross-machine benchmark, largest-input proof or upper memory bound.

## Demo and visual check

The two fixture files build a clean bundle with two statements, six entries and four underlying details. Recompilation returns `BYTE_CONSISTENT` and the original `EXTRACTED` report status. The generated HTML was loaded as local document content in installed headless Chromium and visually inspected at 1440-pixel width: title, five report tables, source lineage and separate detail layer were present. File-URL navigation was blocked by browser policy; no browser policy was changed. The local-content rendering does not establish compatibility with every customer browser.

## Remaining acceptance boundaries

No official XSD validation, bank-facility certification, customer data evaluation, Windows execution, alternative-Python-version compatibility, target-ERP adapter, page assembler, persistent import history, payment or accounting acceptance has been demonstrated. Serialized size limits do not bound peak memory during construction. Parent directories must be operator-controlled; the package is not a hostile-process isolation boundary. Exact-head hosted checks and current-main composition remain separate integration evidence.
