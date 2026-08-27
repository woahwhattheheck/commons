# Model-native headless layer

TITAN Hands removes pixels from the model's normal computer-use loop without pretending that applications
have stopped maintaining their own UI state.

```text
model
  -> one MCP tool surface
      -> target=windows -> UI Automation semantic tree -> UIA/native action
      -> target=android -> ADB transport -> LDA Kotlin world-model + executor
                                      \-> UIAutomator fallback if LDA is absent
      -> target=android-lan -> physical Commons APK host (pairing on the device)
      -> target=linux   -> AT-SPI semantic tree -> native AT-SPI / xdotool action
                                      \-> compositor capture only when op=capture
      -> target=pay     -> live Stripe Payment Links + Checkout Session
                                      \-> PAY_UNCONFIGURED when STRIPE_SECRET_KEY is empty
      -> target=wireless -> LAN bind + debug APK helper after a paid session
      -> hands_capture  -> pixels only when requested
                           Android+LDA returns Set-of-Marks, not ADB framebuffer
```

## What is headless now

- The Android colony device runs an AVD with `-no-window`; models operate it through the owner's real LDA
  Kotlin perception/action layer. The Python process is transport and protocol normalization, not a second
  handset operator.
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

Linux is another adapter for the same protocol (AT-SPI first, compositor capture only on
request), not a separate agent or tool surface. Missing bus or libraries return
`TRANSPORT_UNCONFIGURED` with a measured probe; the adapter does not invent a desktop.

`target=pay` is the money path on the same one-tool contract. Live Payment Links already
on HEAD take money without a secret. Checkout Sessions are created only when
`STRIPE_SECRET_KEY` is in the process environment. A missing key returns
`PAY_UNCONFIGURED` with a measured probe. No charge is minted in that state.
Local windows/android/linux and the Commons lanes stay open. Remote/wireless bind
measures a paid checkout session when the key is present.
