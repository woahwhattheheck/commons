# Grok handoff: TITAN Hands inherits LDA

## Owner ruling

The Android hand is the owner's existing LDA build, not reference material for a parallel executor. TITAN adds
the MCP/ADB transport, Windows adapter, headless emulator, and cross-target delta surface. New Android behavior
belongs in the Kotlin translation layer first.

## Governing design inherited from the handset-operator patent

- The model is the driver; deterministic code translates perception and actuation without choosing the goal.
- The normal path is compact structured perception; pixels/vision are an explicit slower path.
- Actions remain broadly available and model-chosen; malformed actions become useful corrective feedback.
- Perceive -> decide -> one action -> re-perceive is the loop, with change detection and honest verification.
- Operator/world-model learning credits mechanisms that cause measured progress.

These are already concrete in the owner's Kotlin. Do not reimplement them in Python.

## Exact inherited seams

| Capability | Owner implementation TITAN calls |
|---|---|
| Compact numbered perception, paging, exact values, marks | `ActionAccessibilityService.snapshotScreen()` |
| Forgiving native action language and retargeting | `ActionAccessibilityService.performActionJson()` |
| Reliable text targeting | `set_text` branch and `setInputText()` |
| Semantic click/scroll plus gesture fallback | `click()`, `scroll()`, `tapAtPoint()`, gesture helpers |
| Pixel change signal | `PixelMap` |
| Learned actuator preference | `ShellInput.noteA11yRefusal()` / `preferShell()` |
| Observe-decide-act, verification, useful failure | `AgentOrchestrator` |
| World-model/operator learning | `WorldModel`, `ReasoningOperators`, `MechanismRouter` |

`TitanHandsReceiver.kt` is intentionally thin: base64 JSON over an explicit ADB broadcast, then direct calls to
the two owner seams above. `host/titan_hands/lda_bridge.py` only transports and normalizes that result for MCP.
`host/titan_hands/android.py` selects `lda-kotlin` first and retains the prior UIAutomator road as fallback.

## Build and proof

### Current source-tree status

The TITAN transport and host tests are ready, but the checked-in LDA source export does **not yet compile into
an APK**. A full `:app:assembleDebug` reaches `compileDebugKotlin`, then fails on pre-existing gaps across the
owner tree rather than in the thin TITAN receiver. Do not replace LDA to get around this; repair the inherited
source in place.

The first repair pass should cover:

- missing `SettingsManager` APIs referenced throughout the service/orchestrator/brain, including agent-language,
  Gemini-block, shell-input, self-evolve, thinking-log, continuous-stream, prompt-layout, and online settings;
- missing owner-model/operator helpers such as `distilledOperators`, `failureHintFor`, `valuesBlock`, and
  `timeContext` referenced by `AgentBrain`, `AgentOrchestrator`, `WorldModel`, and related classes;
- the absent Shizuku dependency used by `ShellInput` (`rikka.shizuku.Shizuku`);
- the remaining unresolved symbols/syntax mismatches reported in `MainActivity`, `MechanismRouter`, and
  `ScoreboardActivity`.

After each repair, run the exact build below. Success means an APK exists and the installer can perform the
emulator proof; Python unit success alone is not an Android live proof.

```powershell
powershell -File host/titan_hands/setup_android_headless.ps1 -AcceptSdkLicenses
powershell -File host/titan_hands/start_android_headless.ps1
powershell -File host/titan_hands/install_lda_emulator.ps1
powershell -File host/titan_hands/register_codex.ps1
py -3 -m unittest discover -s host\titan_hands\tests -t .
```

Then start a fresh Codex task, call `hands_capabilities(target="android")`, and require
`implementation=lda-kotlin` before testing native actions. Observe first; use the `[N]` element from the LDA
screen; act; observe again; require exact semantic evidence rather than trusting an action-return boolean.

## Useful next work

1. Add a receiver operation for the LDA's optional marked screenshot so `hands_capture` can return the same
   Set-of-Marks visual rather than a raw ADB framebuffer.
2. Carry the LDA world-model transition credit into the shared TITAN delta receipt so Android and Windows learn
   from the same screen -> action -> screen evidence.
3. Port LDA target-retargeting and post-action verification patterns into the Windows adapter without narrowing
   either platform's action space.

Do not create another Android executor, do not make UIAutomator primary again, and do not attach a personal phone
unless the operator supplies its exact serial. Purchased colony devices are explicit targets.
