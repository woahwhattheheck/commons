# P11 manifest custody repair

Parent exact head: `23ceddf19ede39d1c7c872f80d71a1734d4b64a3`  
Review blocker consumed: GitHub review `5160114805`.

This stacked repair changes **no service-calendar semantics**. It preserves the
strict facade, the byte-identical predecessor core, and the strict-field
regression from the parent head. The repair closes only evidence custody:

- `MANIFEST.json` now declares an explicit packet root instead of mixing
  packet-relative and repository-relative paths.
- The manifest binds the 45,426-byte preserved core, the 3,499-byte strict
  facade, and `test_service_calendar_strict_fields.py`.
- Repository-root receipts and the live GitHub workflow are separated into
  `repository_files`, so their locations are unambiguous.
- Exact-head CI re-hashes every declared file before compiling or running tests,
  rejects duplicate manifest keys and path traversal, and requires the strict
  facade/core/regression paths to be present.
- The original SOL-CHRONOS receipt remains immutable historical evidence; this
  repair adds a separate receipt rather than rewriting the predecessor claim.

No canonical TITAN runtime, config, archive, export, pointer, provider, Kaggle,
route, scheduler policy, or gameplay default is changed. No hosted-green or
playing-strength claim is made by this document. Admission requires the
path-scoped workflow to pass on the exact repair head.
