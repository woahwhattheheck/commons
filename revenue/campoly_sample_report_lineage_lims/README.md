# Cambridge Polymer sample-to-report lineage LIMS

Demand: `campoly-sample-report-lineage-lims-01`

This pack points to the root synthetic engine and acceptance binary:

```sh
python campoly_sample_report_lineage_lims.py
python test_campoly_sample_report_lineage_lims.py
```

The frozen 100-shipment fixture reconciles quote, purchase order, request
form, required SDS, sample bag, package, controlled method/version, raw
result, and staged analytical-report provenance. The oracle is exactly 80
`READY` and 20 HOLD: 8 missing quote links, 4 required-SDS failures, 4
duplicate IDs, and 4 bag/form mismatches.

Held rows create no accession, work order, result, staged report, or release.
Replay adds no records. Release uses an authoritative synthetic reviewer
directory and rejects automation or self-asserted reviewers.

HOLD / BUILD-AND-VERIFY. Synthetic/read-only. PRE-SALE TRANSPORT: NONE.
No customer data, live integration, outreach, spend, production write,
analytical interpretation, compliance decision, or automatic release.
