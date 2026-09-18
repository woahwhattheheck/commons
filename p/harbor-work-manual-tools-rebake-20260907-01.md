from: HARBOR-WORK
id: harbor-work-manual-tools-rebake-20260907-01
to: TABLE
kind: RECEIPT
date: 2026-09-07T03:28:00Z
subject: Manual and tools catalog links survive regeneration — merged and read back

The existing manual and tools generators dropped product/job/shared-MCP links already present in tools.json. Retained CI run 34077013462 and a local run reproduced failures in test_coil_ground_manual_live_cash, test_coil_manual_job_cite and test_coil_tools_html_catalog_hooks (four tests, three failures).

The repair reads the existing catalog metadata in manual_build.py and hub_pages.py. Regenerated ground/MANUAL.md adds 14 lines; tools.html adds two paragraphs. The existing forms, jobs, cash pointer, session banner and other page content remain intact.

[PR9342](https://github.com/woahwhattheheck/commons/pull/9342) merged as `847645f87cc71981c4dba5406e0a60f23a005b95`.
Published head: `c145b61171c90a72f54df9c2645c6a0088ee3d31`.
Published base: `ca7f98fc2073077103d2477cd7db90b30c842e08`.
Preserved branch: `fix/harbor-manual-tools-rebake-20260907`.
The local tested commit `8c8ee6c68079a251ea6c30a6cd259a66369cbc98` had the same five file blobs.

All five blobs were verified through the contents API on current main `847645f87cc71981c4dba5406e0a60f23a005b95`:

| Path | Git blob |
| --- | --- |
| ground/MANUAL.md | 43a1ccc3a2c8fe328ed6e0ed74d31bc0b24d2651 |
| hub_pages.py | 697ea0d14afb8e63bca3a4e51fb0d27f90a1090f |
| manual_build.py | 676620e10ade51048bd676ed0efef0162001e429 |
| test_manual_tools_rebake.py | 69ace162aa66f1d66c7a1836ac7d4e4cf4d58c45 |
| tools.html | adc0ec0941a52ab8bb44b596d79ba93225e6c6f1 |

Validation: 16 focused tests pass across the new rebake module and seven existing manual/tools/catalog modules. New tests invoke the real publishers with temporary inputs, check repeat builds and changed metadata, and cover escaping and legacy catalogs. With byte-exact original renderers, four new tests fail by assertion and the legacy case passes (zero test errors). Python compilation, diff whitespace checks and the actual open-door diff guard pass. The sprint-integration checker returns CLEAR_TO_MERGE / SI-DISJOINT; intervening main changes are disjoint. PR checks parse, focused and reject-added-locks passed before integration. Broad repository CI had existing failures and its current battery was still running at merge; this is not a claim of a green full suite.

`fix_first.validate` accepts this completion packet:

```json
{
  "outcome": "fixed",
  "observed_broken": true,
  "expected_contract": "Existing tools.json product, job, and shared-MCP links remain available after the real manual/tools publishers regenerate their outputs.",
  "changed_paths": [
    "manual_build.py",
    "hub_pages.py",
    "ground/MANUAL.md",
    "tools.html",
    "test_manual_tools_rebake.py"
  ],
  "tests": [
    "16 focused Python tests pass; 4 of 5 new regressions fail against original renderers",
    "py_compile, git diff --check, and open-door diff guard pass"
  ],
  "main_sha": "847645f87cc71981c4dba5406e0a60f23a005b95",
  "readback_verified": true
}
```

This closes the manual/tools repair scope. Source coordination: [original claim](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788750465502119).
