# Model-native headless layer

TITAN Hands removes pixels from the model's normal computer-use loop without pretending that applications
have stopped maintaining their own UI state.

```text
model
  -> one MCP tool surface
      -> target=windows -> UI Automation semantic tree -> UIA/native action
      -> target=android -> UIAutomator XML tree        -> ADB action
      -> hands_capture  -> pixels only when requested
```

## What is headless now

- The Android colony device runs an AVD with `-no-window`; models operate it entirely through semantic
  UIAutomator deltas and ADB actions.
- Windows observations contain UI Automation roles, names, state, bounds, stable IDs, and available actions.
  The model receives no framebuffer unless it explicitly calls `hands_capture`.
- Repeated observations return only added, updated, and removed nodes.
- The MCP process is local STDIO. It does not depend on a carrier screenshot/coordinate hook and contains no
  confirmation dialogue.

## Honest boundary

Windows applications still run inside the user's interactive Windows session, and Android applications still
maintain surfaces inside the emulator. TITAN removes rendering from the **model-facing information path**; it
does not claim to replace the Windows compositor or Android framework. This preserves compatibility with
ordinary apps while achieving the useful part of the model-native design: semantic state by default and pixels
only as an explicit fallback.

Future Linux support should be another adapter for the same protocol (AT-SPI first, compositor capture only on
request), not a separate agent or tool surface.
