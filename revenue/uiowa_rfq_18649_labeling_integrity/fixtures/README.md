# Screen fixtures — SYNTHETIC / FICTION

Invented artifacts, one per classification. Nobody's real files. The screen only
reads them.

| lane | artifact | expected |
| --- | --- | --- |
| `lane_records_unlabeled` | `findings.csv` | `UNDISCLOSED_PROVENANCE` — records, says nothing about what it is |
| `lane_records_labeled` | `findings.csv` | `DISCLOSED` — same records, synthetic disclosure in the header |
| `lane_buried` | `report.md` | `LABEL_BURIED` — disclosed, but past the opening of the file |
| `lane_config` | `weights.json` | `UNLABELED_CONFIG_SHAPED` — machinery, no disclosure expected |
| `lane_real` | `scan_results.csv` | `DISCLOSED` — a **real** measurement carrying a provenance statement, which must NOT be labeled synthetic |
