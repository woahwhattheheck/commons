# Abbotsford RFP 1220-2026-4235 — digital waste calendar carrier

Isolated evidence carrier for the public City of Abbotsford opportunity
`RFP 1220-2026-4235`. Qualification is `HOLD_PACKET_REQUIRED` until an
authorized bid package / Appendix B is actually bound.

## Public facts

- Buyer: City of Abbotsford
- Title: Digital Waste Collection Calendar & Resident Engagement Platform
- Close: 2026-10-07 14:00 PDT
- Questions: 2026-09-24 14:00 PDT
- Detail: https://abbotsford.bidsandtenders.ca/Module/Tenders/en/Tender/Detail/254ac4d7-b135-44c6-99d9-44203c732790

CanadaBuys independently lists the same city/title. The buyer portal is the
controlling public identity used here.

## What this proves

`abbotsford_1220.py` source-binds those public facts and compiles a buyer-neutral
waste-calendar demo. Every demo surface is labeled `DEMO_CAPABILITY` and cannot
satisfy an unknown mandatory requirement.

Demo surfaces: address lookup, collection schedule/calendar, holiday/exception
override, reminder preference simulation, multilingual/accessibility metadata,
admin/content change receipts, deterministic import/export, privacy-minimized
resident identifiers, observability receipts.

## Authority

No buyer contact, portal mutation, plan-taker registration, proposal, signature,
price, award, payment, or revenue is authorized by this code.

## Checks

```bash
python -m py_compile abbotsford_1220.py test_abbotsford_1220.py
python -m unittest -v test_abbotsford_1220.py
python -O -m unittest -v test_abbotsford_1220.py
python abbotsford_1220.py --qualify
python abbotsford_1220.py --demo-fixture
```
