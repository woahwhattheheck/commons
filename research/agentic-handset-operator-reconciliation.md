# Agentic handset operator — selective reconciliation

This is a tracked-source comparison, not a filesystem dump. Build products, model files, archives,
local properties, device state, and untracked work are outside the comparison by construction.

- Commons: `94db2d956719de86345995dcbd092bf5073ba146` under `lda/`
- Source: `4eab3d2fef8a9d44e202fcc48b874be955368db2`
- Scope: `app/build.gradle`, `app/src/main`, `app/src/test`, `build.gradle`, `gradle.properties`, `settings.gradle`
- Result: 61 same, 21 different, 7 source-only, 0 Commons-only

## Selective queue

| status | recommendation | path |
|---|---|---|
| different | review-semantic-diff | `app/build.gradle` |
| different | review-semantic-diff | `app/src/main/AndroidManifest.xml` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/AgentApp.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/AgentControl.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/AgentMemory.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/ChatActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/ConfirmationOverlay.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/DebugLogActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/DeviceStats.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/FloatingButtonService.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/MainActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/MemoryActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/PixelMap.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/SettingsActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/SettingsManager.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/TaskDetailActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/TaskHistory.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/TaskLogActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/TrainingActivity.kt` |
| different | review-semantic-diff | `app/src/main/java/com/local/deviceagent/TrainingData.kt` |
| source_only | candidate-resource | `app/src/main/res/xml/data_extraction_rules.xml` |
| different | review-semantic-diff | `app/src/main/res/xml/file_paths.xml` |
| source_only | candidate-test | `app/src/test/java/com/local/deviceagent/AgentLanguageTest.kt` |
| source_only | candidate-test | `app/src/test/java/com/local/deviceagent/MechanismRouterTest.kt` |
| source_only | candidate-test | `app/src/test/java/com/local/deviceagent/PromptBudgetTest.kt` |
| source_only | candidate-test | `app/src/test/java/com/local/deviceagent/ReasoningOperatorsOracleTest.kt` |
| source_only | candidate-test | `app/src/test/java/com/local/deviceagent/ScaleBakeNibbleTest.kt` |
| source_only | candidate-test | `app/src/test/java/com/local/deviceagent/ScreenClassTest.kt` |

## Landing rule

Review semantic diffs individually. Candidate tests and the Android data-extraction resource are the
smallest safe imports. Do not bulk-copy the source repository or its archive/build directories.
The physical phone remains outside this work; emulator integration is a later phase.
