# KCA Laboratories Kentucky Medical Cannabis Intake LIMS

Demand: `kca-ky-medical-cannabis-intake-lims-01`
Buyer: KCA Laboratories / Richard Sams (matched prospect: Jonathan Thompson)

This pack provides the root synthetic reconciliation engine and acceptance binary:

```sh
python kca_ky_medical_cannabis_intake_lims.py
python test_kca_ky_medical_cannabis_intake_lims.py
```

The frozen 100-order fixture reconciles registration/license, portal order, printed CoC, physical receipt, matrix/panel, internal testing, and partner-lab result provenance. The oracle produces exactly 75 `READY` and 25 `HOLD`:
- 10 invalid or missing KY medical-cannabis licenses
- 5 CoC / physical receipt / manifest ID mismatches
- 5 duplicate order / sample / package IDs
- 5 partner-result provenance gaps (tampered method/lab/source hash)

Held orders create zero accession, work-order, result, or draft CoA records.
Replay adds zero records.
Release of draft CoAs requires an authorized named-human reviewer directory entry.

HOLD / BUILD-AND-VERIFY. Synthetic / read-only. PRE-SALE TRANSPORT: NONE.
No state-system writes, Metrc writes, compliance decisions, prospect outreach, or automatic CoA releases.
