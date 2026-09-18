# RWD #3 Rogers County — Pay Application + Retainage owner packet

Operation: `RWD3-ROGERS-PAYAPP-RETAINAGE-OWNER-PACKET-ZSOL-20260917`

This is an **internal, route-free owner-review packet** for the already-shipped Pay Application + Retainage Sprint. It does not contact Rural Water District #3 Rogers County, select a recipient, request Muse arbitration, submit a form, place a call, or assert buyer interest.

## Why this edge exists

RWD #3's current first-party agenda surface lists four construction pay-request decisions in one meeting:

- Crossland Heavy Contractors — Pay Request No. 1, **$122,906.25**, 2026 Keetonville Water Storage Tank.
- Beytco — Pay Request No. 5-Final, **$35,762.03**, explicitly including release of retainage, Tacora Water Treatment Plant Pump Replacement.
- Cunningham Construction — Pay Request No. 3, **$152,819.33**, Tacora MB II.
- King Excavating — Pay Request No. 2-Final, **$33,523.81**, explicitly including release of retainage, Gardner Pond S. 4150 Rd. Water Line.

The first-party personnel page identifies **Kelly King** as District Manager. The public contact surface is general-purpose; this packet deliberately does not promote that surface into a selected commercial route.

Sources retained in `public_facts.json`:
- RWD #3 Agenda & Minutes
- RWD #3 Personnel
- RWD #3 Contact Us

## Product boundary

Canonical product carrier: `woahwhattheheck/smb-showcase-inventory` PR #1043, **$12,500 fixed / PROPOSED_NOT_ACCEPTED / target 10 business days**.

The product is one legal entity × one project × one pay cycle. The two final-pay/retainage items are therefore **two separate candidate scopes** and MUST NOT be bundled into one fixed sprint:

1. `RWD3-TACORA-WTP-PR5-FINAL`
2. `RWD3-GARDNER-POND-PR2-FINAL`

Public agenda facts do not establish the owner-side schedule of values, complete current-work evidence, approved change-order evidence, prior certification/payment lineage, retainage policy, row counts, budget, need, defect, savings, or intent to buy. Those remain missing buyer-side inputs.

## Commercial truth

- Research-qualified public evidence: yes.
- Fixed offer accepted: no.
- Buyer selected: no.
- Route selected: no.
- Muse requested: no.
- Outbound performed: no.
- Contract, invoice, receivable, payment, cash, or revenue: no.
- Claim of error, overpayment, underpayment, savings, defect, urgency, or buyer intent: no.

## Verify

```bash
python coordination/revenue/rwd3_rogers_payapp_20260917/verify_packet.py
```

A valid packet returns `OWNER_PACKET_READY_NO_OUTBOUND`. Any outbound action remains a later, separately censused and Muse-arbitrated operation.
