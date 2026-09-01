# MGA Alabama materials-program LIMS

Demand: `mga-alabama-materials-program-lims-01`

This pack points to the root synthetic engine and acceptance binary:

```sh
python mga_alabama_materials_program_lims.py
python test_mga_alabama_materials_program_lims.py
```

The frozen 100-program fixture binds request, specimen/coupon, and
conditioning-window evidence to lab/method/version/fixture and
environment setpoint, then to a raw value/source hash and a staged
qualification packet. The oracle is exactly 80 `READY` and 20 HOLD:
5 duplicate specimens, 5 conditioning-window breaches, 5 method/material
mismatches, and 5 UTM/environment QC failures.

Held rows schedule no jobs and create no result, staged packet, or
release. Replay adds no jobs. Release uses an authoritative synthetic
reviewer directory and rejects automation or self-asserted reviewers.

Materials coupons and qualification metadata only. No vehicle, weapons,
propulsion, mission, or controlled-design data.

HOLD / BUILD-AND-VERIFY. Synthetic/read-only. PRE-SALE TRANSPORT: NONE.
No customer data, live integration, outreach, spend, production write,
materials interpretation, compliance decision, or automatic release.
