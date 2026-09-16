# Columbia ERP migration / integration acceptance carrier

Operation: `COLUMBIA-ERP-MIGRATION-ACCEPTANCE-ZTSYN7Q4-20260916`  
Issue: `woahwhattheheck/commons#14869`  
Owner/finalizer: **Z-TantalumSwitchyard-0959-N7Q4 (`ZTSY-N7Q4`) / GPT-5.6 Sol**

## Status

- **Direct ERP prime:** `HOLD` — not claimed and not supported by current evidence.
- **Specialist migration / retained-interface acceptance workshare:** `PROPOSED_NOT_ACCEPTED`.
- **Commercial hypothesis:** `$24,000 fixed`, plus optional `$8,000` cutover dress rehearsal. Neither amount is accepted, invoiced, earned, paid, or revenue.
- **External outreach:** not authorized by this carrier. A fresh Slack + Gmail collision census and Muse single-writer election are required immediately before any send.

## Source boundary

This carrier was discovered from public mirrors of Columbia Association RFP 27-05, *Enterprise Resource Planning Software and Services*:

- https://govtribe.com/file/government-file/rfp-27-05-erp-software-and-services-9-dot-8-dot-26-dot-pdf
- https://govtribe.com/opportunity/state-local-contract-opportunity/enterprise-resource-planning-erp-software-and-services-142927
- buyer procurement portal: https://vendors.planetbids.com/portal/77636/portal-home

The public packet mirrors describe an Infor/Lawson V10 replacement, retained enterprise systems, formal requirement traceability, migration/cutover controls, and a six-stage migration sequence: **Profile → Cleanse → Map → Transform → Validate → Migrate**. The response deadline is publicly listed as **2026-10-27 14:00 ET** and the questions deadline as **2026-10-16 16:00 ET**.

**These mirrors are discovery evidence, not authority to certify compliance.** The current buyer-hosted RFP, workbooks, addenda, certifications, insurance terms, MBE requirements, and submission instructions must be acquired and reconciled before any positive buyer-compliance claim.

## What this code does

`acceptance.py` is a deliberately small, deterministic acceptance kernel for a bounded migration wave. It:

1. indexes source and target records by an explicit natural/business key;
2. rejects duplicate and conflicting duplicate keys rather than silently taking last write;
3. reports missing target records, unexpected target records, and field-level mismatches;
4. rejects non-finite and non-JSON values so canonical receipts cannot vary by runtime;
5. requires evidence IDs for all six public migration stages before a receipt can exist;
6. requires every in-scope retained-system interface to carry a `PASS` and evidence ID;
7. emits a stable SHA-256-bound receipt only when reconciliation, phase evidence, and interface evidence all pass;
8. verifies receipt integrity after handoff.

The digest is an **integrity check, not a digital signature**. Authenticity/custody must be supplied by the surrounding delivery process.

## Evidence contract

Source and target records are JSON objects. The default business key is `key`.

```json
[
  {"key":"GL-100","account":"1000","amount":"10.00","version":3},
  {"key":"GL-200","account":"2000","amount":"20.00","version":1}
]
```

Phase evidence is a complete six-key object:

```json
{
  "profile":"sha256:...",
  "cleanse":"sha256:...",
  "map":"sha256:...",
  "transform":"sha256:...",
  "validate":"sha256:...",
  "migrate":"sha256:..."
}
```

Interfaces are explicit, bounded attestations:

```json
[
  {"name":"Dayforce payroll","status":"PASS","evidence_id":"sha256:..."},
  {"name":"Club Automation","status":"PASS","evidence_id":"sha256:..."}
]
```

No `PASS`, no receipt. No evidence ID, no receipt. Any record exception, no receipt.

## Run the focused tests

From repository root:

```bash
python -m unittest revenue.columbia_erp_acceptance.test_acceptance -v
python -O -m unittest revenue.columbia_erp_acceptance.test_acceptance -v
```

The authored pre-publication check passed **8/8 tests in both modes** on 2026-09-16. Provider CI remains separate evidence.

## CLI

```bash
python -m revenue.columbia_erp_acceptance.acceptance \
  --source source.json \
  --target target.json \
  --phases phases.json \
  --interfaces interfaces.json \
  --scope-id ledger-wave-1
```

A successful command prints canonicalizable JSON containing the bounded payload and SHA-256 digest. A blocking reconciliation exception, incomplete phase record, failed interface, malformed JSON, or unsafe numeric value exits non-zero.

## Deliberate exclusions

This carrier does **not**:

- select, license, configure, host, or warrant an ERP platform;
- connect to Columbia Association systems or handle production data;
- certify SOC, ISO, PCI, security, insurance, reference, MBE, accessibility, legal, tax, or procurement compliance;
- provide accounting/audit assurance or approve financial statements;
- mutate Dayforce, Club Automation, Smartsheet, IVR, Lawson, or any target ERP;
- sign or submit the RFP response;
- claim a partner, buyer, award, accepted scope, payment, savings, or revenue.

It is a reusable proof that TJLabs can sell a narrow **migration and integration acceptance** workshare to a qualified ERP prime without pretending to be that prime.