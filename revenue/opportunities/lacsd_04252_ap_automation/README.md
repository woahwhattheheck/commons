# LACSD 04252 — AP Automation Acceptance Evidence

This carrier turns the public buyer requirements for Los Angeles County Sanitation Districts project **04252 — AUTOMATED ACCOUNTS PAYABLE INVOICE PROCESSING SYSTEM** into a deterministic, buyer-neutral acceptance/UAT evidence package for a qualified AP-automation / Oracle prime.

## Public buyer facts bound here

The official LACSD detail page describes a replacement for manual, template-dependent and decentralized invoice handling. The stated target shape includes:

- AI-based **zero-template** invoice extraction;
- automated invoice matching and approval routing;
- real-time Oracle Enterprise Business Suite integration;
- **99% data accuracy** target;
- invoice processing cycle time reduced from more than ten days to **under 48 hours**;
- centralized processing;
- a complete audit trail; and
- real-time BI visibility.

Sources:

- Detail: <https://www.lacsd.org/Home/Components/RFP/RFP/954/488?selsta=4>
- Current procurement list: <https://www.lacsd.org/opportunities/bids-purchasing/purchasing-section-projects/-sortn-RFPTitle>

### Deadline conflict is deliberately fail-closed

At source capture on 2026-09-16, the detail page showed **2026-10-15 11:00 PT**, while the procurement list still showed **2026-09-30 11:00 PT**. The code does not pick the more convenient date. It emits `HOLD_PACKET_REQUIRED` until the authorized QuestCDN packet/addenda resolves the conflict.

The public procurement page also states that only bidders who properly download the authorized bid documents through QuestCDN appear on the planholders list and may submit, and that paper/email submission is not accepted. This repository does **not** represent Token Junkie Labs as a planholder, bidder of record, Oracle product vendor, or qualified prime.

## What the implementation proves

`lacsd_04252.py` provides strict JSON parsing and deterministic semantic recomputation for two connected surfaces.

### 1. Pursuit/source contract

The manifest binds the exact solicitation identity, both official source surfaces, the conflicting public deadlines, the buyer-stated acceptance targets, and an explicit authority ceiling. Source drift, future source timestamps, target dilution, price-state promotion, or any attempt to authorize buyer contact/submission/Oracle writes fails closed.

### 2. Invoice acceptance matrix

Each synthetic invoice case is evaluated against measurable evidence:

- extraction accuracy in exact integer basis points;
- elapsed cycle time in seconds;
- PO presence and amount tolerance;
- vendor identity match;
- duplicate detection;
- approval evidence;
- Oracle synchronization evidence without Oracle mutation;
- audit-trail completeness; and
- dashboard freshness.

The shipped hostile matrix covers every terminal disposition:

`ACCEPT_EVIDENCE_READY`, `REJECT_DUPLICATE`, `HOLD_EXTRACTION_ACCURACY`, `HOLD_MISSING_PO`, `HOLD_VENDOR_MISMATCH`, `HOLD_AMOUNT_VARIANCE`, `HOLD_APPROVAL`, `HOLD_CYCLE_TIME`, `HOLD_ORACLE_SYNC`, `HOLD_AUDIT_TRAIL`, and `HOLD_DASHBOARD_FRESHNESS`.

The buyer says **under** 48 hours; therefore exactly 48:00:00 is a HOLD, while 47:59:59 remains admissible. The 99% accuracy boundary is exact integer arithmetic, avoiding floating-point threshold drift.

Every result and aggregate bundle carries a deterministic SHA-256 receipt. `verify_evidence()` recompiles the complete bundle rather than trusting a caller-supplied status.

## Commercial wedge

Reference specialist workshare:

**AP Automation Validation/UAT Evidence Workshare — $5,000 fixed — PROPOSED_NOT_ACCEPTED**

A qualified prime supplies the agreed AP workflow, source/target evidence and Oracle integration contract. TJLabs returns the deterministic requirement-to-evidence matrix, hostile acceptance cases, observed accuracy/cycle metrics, exception register, and owner-review handoff.

This price is a commercial hypothesis, not a sale. No buyer acceptance, partner acceptance, cash, receivable, payment, award, savings, recovered cash, or recognized revenue is asserted.

## Authority ceiling

All compiled evidence preserves these as `false`:

- `oracle_write_authorized`
- `payment_authorized`
- `buyer_contact_authorized`
- `prime_contact_authorized`
- `submission_authorized`
- `contract_acceptance_authorized`
- `revenue_recognized`

No production Oracle connection, buyer portal action, QuestCDN registration/download, submission, signature, accounting mutation, invoice payment, or external outreach occurs here. Any future prime outreach is a separate action requiring a fresh collision fence and Muse single-writer arbitration.

## Verification

From this directory:

```bash
python -m py_compile lacsd_04252.py test_lacsd_04252.py
python -m unittest -v test_lacsd_04252.py
python -O -m unittest -v test_lacsd_04252.py
```

The GitHub workflow runs the same semantic suite on Python 3.11 and 3.13, normal and optimized mode. A queued or absent hosted run is `UNKNOWN`, never represented as green.

Operation: `LACSD-04252-AP-AUTOMATION-ACCEPTANCE-SOLZ-20260916`  
Owner/finalizer: **Sol-Z / GPT-5.6 Sol**  
Commercial state: **PROPOSED_NOT_ACCEPTED**
