# Frozen acceptance contract

`synthetic_acceptance.py` generates 120 deterministic synthetic layout jobs. Jobs 1–96 are complete. Jobs 97–120 contain exactly one fault each, allocated as exactly three faults in each of eight classes:

1. `design_source`
2. `trade_signoffs`
3. `unit_scale_metadata`
4. `control_point_survey`
5. `station_verification`
6. `portal_preview_qr`
7. `printer_app_version`
8. `final_job_report`

`compiler.py` must produce exactly 96 complete evidence packets and exactly 24 job+reason exceptions across 24 unique faulty jobs. Each complete packet carries JSON-path lineage values copied verbatim from its source record and a SHA-256 over canonical lineage. Tests resolve every path back to the input and assert exact equality.

All packets/exceptions expose `control_commands_emitted=0` and `field_release=null`. There are no robot navigation/motion/printing, tracker setup, obstacle handling, file deletion, model approval, survey/layout certification, or field-release operations.
