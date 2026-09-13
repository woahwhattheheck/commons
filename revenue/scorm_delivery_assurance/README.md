# SCORM Delivery Assurance

Buyer-neutral, offline release assurance for a SCORM course package.

The tool answers one narrow question: **does this exact ZIP satisfy an explicit evidence-bound package contract strongly enough to hand to an LMS sandbox for review?** It does not certify SCORM conformance, accessibility, instructional quality, buyer acceptance, or production LMS readiness.

## Checks

- bounded ZIP input with traversal, symlink, duplicate-name, and case-collision rejection;
- root `imsmanifest.xml`, local-only launch/resource hrefs, organization/resource closure, and presence of every manifest-declared file;
- SCORM 1.2 / 2004 version declaration against explicit policy;
- `course.assurance.json` binding course ID, source revision SHA-256, every organization resource to exactly one module, assessment/completion metadata, and accessibility evidence paths;
- transcript plus `.vtt`/`.srt` caption evidence presence when policy requires it;
- canonical file SHA-256 inventory, package/manifest/sidecar digests, deterministic status/reasons, and a receipt that can be fully recomputed offline;
- create-exclusive CLI output so an older receipt is never silently overwritten.

`READY_FOR_LMS_SANDBOX_REVIEW` is deliberately the strongest state. It means only that the exact supplied package passed this technical preflight. Every receipt explicitly keeps `scorm_spec_certified`, `accessibility_certified`, `instructional_quality_approved`, `lms_production_approved`, `buyer_acceptance`, and `payment_or_revenue` false.

## Evidence sidecar

The ZIP must contain `course.assurance.json`:

```json
{
  "schema": "tjlabs.scorm-course-evidence/v1",
  "course_id": "course-01",
  "source_revision_sha256": "<64 lowercase hex>",
  "modules": [
    {
      "id": "module-01",
      "resource_id": "RES1",
      "title": "Module One",
      "assessment": {"required": true, "passing_score": 80},
      "completion": {"required": true},
      "accessibility": {
        "transcript": "module-01/transcript.txt",
        "captions": ["module-01/captions.vtt"]
      }
    }
  ]
}
```

This is TJLabs release evidence layered on top of SCORM, not a replacement for the SCORM specification.

## CLI

```bash
python -m revenue.scorm_delivery_assurance.assurance compile course.zip receipt.json
python -m revenue.scorm_delivery_assurance.assurance verify course.zip receipt.json
```

An optional policy JSON can be supplied with `--policy`. The default accepts SCORM 1.2 and 2004, requires assessment/completion metadata, requires transcript+caption evidence, and bounds file count and expanded size.

## Focused validation

```bash
python -m py_compile revenue/scorm_delivery_assurance/*.py
python -m unittest revenue.scorm_delivery_assurance.test_assurance -v
python -O -m unittest revenue.scorm_delivery_assurance.test_assurance -v
```

The suite covers clean two-module packaging, missing accessibility evidence, traversal, external launch URLs, duplicate and case-colliding members, organization/resource mismatch, duplicate JSON keys, bool-as-int policy traps, policy thresholds, package tamper/reverify, deterministic exact-byte receipt generation, create-exclusive CLI publication, and explicit non-certification/payment authority.

## Commercial boundary

This component can support a full-service e-learning prime or an internal release process. It is **not** evidence that TJLabs authored a buyer's course, owns instructional-design experience, has client references, completed an accessibility audit, can supply approved voice talent, or is authorized to access/deploy to a production LMS. Those remain separate evidence gates in the parent revenue lane.
