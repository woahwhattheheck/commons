# Layout Revision-to-Print Evidence Gate

A read-only, standard-library evidence compiler for BIM/CAD-to-field layout jobs. It joins eight evidence classes into deterministic packets and emits exact reason-coded exceptions when evidence is stale or mismatched.

Evidence classes: BIM/CAD hash + released revision; trade signoffs; unit/scale metadata; control-point survey version; station-verification result; Portal preview/QR checksum; printer/app versions; final job report.

It deliberately exposes **no control surface**: no robot navigation/motion/printing, tracker setup, obstacle handling, file deletion, model approval, survey/layout certification, or field release.

## Frozen acceptance

```bash
python3 -m unittest discover -s tests -v
python3 synthetic_acceptance.py /tmp/layout-120.json
python3 compiler.py /tmp/layout-120.json --out /tmp/layout-out || test $? -eq 2
```

The corpus has 120 jobs: 96 clean and 24 unique faulty jobs, exactly three faults in each of eight evidence classes. Required result: 96 complete packets + 24 job/reason exceptions, exact field-level source lineage, deterministic output, zero control commands.

## Commercial pilot boundary

A paid pilot can map three redacted completed layout jobs into the same evidence contract, deliver three reproducible packets plus exception/owner mapping, and estimate integration. It does not require robot credentials or any ability to command field hardware.
