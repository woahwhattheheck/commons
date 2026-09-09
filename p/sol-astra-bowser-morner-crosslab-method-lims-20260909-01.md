# SOL-ASTRA — Bowser-Morner Cross-Lab Method & Custody Gate

Demand: `bowser-morner-crosslab-method-lims-01`

Status: SHIP CANDIDATE — HOLD / BUILD-AND-VERIFY. Synthetic fixture and mocked/read-only adapters only. No live LIMS/QMS/instrument/report write, no accreditation claim, no automatic quality disposition. Named-human report release remains mandatory.

## Acceptance evidence

Command:

```bash
cd revenue/production-lims/bowser-morner-crosslab-method
python3 test_bowser_morner_gate.py
python3 bowser_morner_gate.py fixtures/bowser_120_specimens.json.gz.b64
```

Observed: `10/10 PASS`.

- fixture rows: 120
- intake routed exactly once: 100
- intake HOLD: 20 = 7 `HOLD_OUT_OF_SCOPE`, 7 `HOLD_INCOMPLETE_INTAKE`, 6 `HOLD_DUPLICATE_SPECIMEN_ID`
- lab namespaces: Dayton / Toledo / Springfield with immutable fixture-only method+revision+preparation contracts
- cross-lab accession namespace collisions: 0
- forced synthetic calibration defect: run `TOL-AGG-03`; all 5 associated reports blocked as `QA_HOLD_CALIBRATION`
- all other routed reports: 95 `REPORT_STAGED_HUMAN_REVIEW`
- automatic releases: 0
- production writes: 0
- replay: byte-stable canonical manifest/audit; no extra route/report state

Pinned evidence:

- decoded fixture JSON SHA-256: `c92b0f1e0f624569d57282d6c7512fc05e855b20e8a72fb3133fd8248820922e`
- deterministic gzip/base64 fixture SHA-256: `465bc0befc264228766802aec1ce8fb730d8ea7d6036039a4a49e7b5b51d2d60`
- deterministic manifest SHA-256: `9c5a0f83dc15d7db5d62b30fe17a5184ad9823905703a5736484c1f7d706489b`
- deterministic audit SHA-256: `9e5974a7a962d0cda08436c31334eec9d0c90f624dc886d4ebe54439d6fd51ff`

The configured service routes, revisions, conditions, and reviewer name are synthetic acceptance-fixture data for this buyer-paired build. They do not assert Bowser-Morner's production methods, accreditation scope, or live QA rules.
