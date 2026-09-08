# RENEW episodeSteps reader repair — 2026-09-08

Operation: `astra-renew-panel-episode-steps-20260908-01`.

The panel source-binding preflight indexed `configuration.episodeSteps` as a schema object. The pinned official engine encodes it as the scalar integer 720, so the preflight raised `TypeError: 'int' object is not subscriptable` before launching an evaluator.

The reader now accepts either a scalar or the existing object `default`. Its exact integer and >= 2 checks are preserved. No change to source hashes, requested cells, report reuse, failed-report retention, command limits, policies, or engine bytes.

Validation: the unchanged actual official JSON SHA256 `a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867` reproduced the old failure and returns 720 after the fix. Added scalar report-reuse, scalar/object boundary, and invalid-type cases. All 33 focused report-reuse tests pass; the separate synthetic-engine execution test is excluded from this reader-only check. Zero official games or policy calls. Open-door guard PASS. Both changed paths matched the validated baseline byte-for-byte on current main `320bfc25002d4836c13fa772d8e82de7d7cb8054` before branch construction.

Runner SHA256 `07ba03459b46867ab536a81f4314096aff21cdb5a1b0f2c6f4d7177030e56e00` (16634 bytes); tests SHA256 `7e06aac94343e4902e3a728641720fe8658d7956e2797aa69e64a76a03ef3c46` (20963 bytes). Baseline `ebf4d09b485ca5df9a1129e75a8eea86af95cf6e`; private batch source/setup remains private. Merge and exact-main readback will be recorded in the PR.
