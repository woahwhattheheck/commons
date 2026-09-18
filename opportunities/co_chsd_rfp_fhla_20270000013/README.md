# Colorado Health Systems Directory — partner-first pursuit

Operation: `CO-CHSD-RFPFHLA20270000013-PARTNER-FIRST-ZSOL-20260917`

This package is an **internal qualification and response-production boundary** for the Colorado Department of Public Health and Environment Colorado Health Systems Directory procurement reported as `RFPFHLA20270000013 / RFP 2027000001`.

## Current truth

- Commercial state: **PARTNER-FIRST / PRIME-HOLD / $0 booked**.
- Buyer source state: **official current BidNet solicitation/addenda are not yet source-pinned in this package**.
- Outbound state: **no partner or buyer contact is authorized by this package**.
- Submission/sign/payment/revenue authority: **hard false**.
- Customer/public-facing Commons backlink authority: **hard false**.

Public procurement mirrors currently report an October 1, 2026 proposal deadline, a five-year funding shape totaling $3.5M, and a Microsoft/Azure/BizTalk/SQL/.NET health-data integration and managed-service scope. Those are discovery facts only until exact controlling buyer bytes are retained and source-pinned.

## Why partner-first

Reported mandatory minimums include a Microsoft BizTalk certification, three years of relevant experience, three similar projects in the last five years, two references, Colorado VSS registration, SOC 2 Type II, health-data/security obligations, accessibility, insurance, and operational staffing. This package does not invent or self-assert any of those facts for TJLabs.

A credible prime must independently prove the buyer-required facts. A bounded TJLabs paid specialist role may cover deterministic integration validation, ETL/data-quality acceptance, reconciliation, evidence/change-control tooling, reporting validation, and other truthful technical work accepted by the prime and buyer.

## Authority model

`qualification.py` deliberately separates:

1. **Discovery input** — useful for research, never controlling buyer authority.
2. **Source-owned buyer roots** — exact buyer descriptor generations whose full identity, authority class, artifact SHA-256, effective time, deadline, and solicitation identity are pinned by reviewed source code.
3. **Source-owned qualification evidence** — exact evidence descriptor generations whose id, party, gate, and artifact SHA-256 are pinned by reviewed source code.
4. **Untrusted runtime packet** — may point at evidence but cannot relabel a trusted SHA into a different deadline, party, gate, or authority class.

Production trusted roots intentionally start empty. The first safe state is therefore `HOLD_MISSING_BUYER_SOURCE`. Future positive evidence requires a reviewed source mutation that pins the **entire** source/evidence descriptor generation, not merely an id→hash association.

The production engine captures a real UTC process clock at import-time generation construction; runtime packets cannot backdate evaluation to evade the deadline. The Python process is trusted. Untrusted JSON/runtime input, descriptor transplant/relabeling, caller-selected time, and self-authored authority labels are inside the threat boundary.

## Public-surface rule

Do **not** put links to `woahwhattheheck/commons`, Commons Pages, raw/API/codeload/clone URLs, badges, or internal provenance pointers in partner/customer emails, proposals, public repositories, demos, storefronts, docs, issues/PRs, sites, or competition surfaces. Historical receipts remain evidence. A future exact-surface exception requires explicit owner authorization.

## Next source generation

Before any READY state:

- retain the current official BidNet solicitation, SOW, addenda, submission instructions, budget template, contract/security/insurance exhibits, and Q&A if any;
- hash exact bytes and add their reviewed source-owned full descriptor generations;
- bind the exact current deadline and supersession generation;
- qualify a real prime/team using retained evidence;
- bind commercial terms and owner/signatory facts;
- use Muse arbitration before any partner outreach;
- perform independent exact-head review, terminal CI, and fresh-main topology fencing before merge/finalization.
