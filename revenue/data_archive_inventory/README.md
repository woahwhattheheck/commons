# Commons Data Archive Rights Inventory

Fail-closed prerequisite for the Commons **Data** offering family. It records declared archive assets and decides whether each has enough provenance, redistribution/publication rights, sensitive-data custody, redaction evidence, and freshness to proceed to the landed `revenue/data_license_desk`.

`ELIGIBLE_FOR_DATA_LICENSE_DESK` means only that the recorded asset may proceed to human-reviewed sample/offer construction. It does **not** execute a license, authorize publication/transfer/payment, scan the repository, prove a legal conclusion, or recognize revenue.

Input schema: `commons-data-archive-inventory/v1`. Every declared asset binds ID/version/path, source SHA-256, provenance SHA-256, regular-file custody, explicit rights/license evidence, permitted grants, transfer + publication flags, sensitive-data class, redaction evidence where required, and optional evidence expiry. Unknown/restricted rights or stale/ambiguous evidence HOLD.

Outputs are deterministic canonical JSON receipt + CSV inventory. Eligible rows include a `license_desk_seed` carrying only proven fields and explicitly listing the remaining `schema_fields`, `sample_rows`, and `offer` requirements.

```bash
python -m revenue.data_archive_inventory.cli build inventory.json --receipt out/receipt.json --csv out/inventory.csv --at 2026-09-13T10:00:00Z
python -m revenue.data_archive_inventory.cli verify inventory.json --receipt out/receipt.json --csv out/inventory.csv --at 2026-09-13T10:00:00Z
```

Validation:
```bash
python -m py_compile revenue/data_archive_inventory/*.py
python -m unittest -q revenue.data_archive_inventory.test_inventory
python -O -m unittest -q revenue.data_archive_inventory.test_inventory
```
