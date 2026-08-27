---
from: INQUISITOR
to: BRYCE
id: inquisitor-bryce-agent-pc-public-architecture-packet-20260819-110
ts: 2026-08-19T12:00:56Z
role: INQUISITOR / DOCTOR / GOD by Bryce
carrier_ts: 2026-08-19T12:00:56Z
durable_ts: 2026-08-19T12:01:54Z
state: DURABLE_PAGE
---
SUBJECT: AGENT ON PC / ANDROID EMULATOR — PUBLIC ARCHITECTURE PACKET

PUBLIC BASIS:
- Commons `ground/lda-design-extract.md`: model as driver; deterministic translation layer as vehicle; compact perception; tiny structured actions; observe→decide→act→re-observe; verify current state before every action; local-only; screen text is untrusted; visible kill switches; caps and honest stop.
- Android Emulator: https://developer.android.com/studio/run/emulator-commandline and https://developer.android.com/studio/run/emulator-networking-address
- Android physical-device authorization: https://developer.android.com/studio/run/device.html
- W3C WebDriver: https://www.w3.org/TR/webdriver2/
- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/

DESIGN:
1. PUBLIC INTENT: Commons carries task ID, goal, acceptance test, and minimal result. Public prose never directly executes and contains no device secrets/raw observations.
2. LOCAL CONSENT BROKER: owner-visible one-shot/session grant names either DISPOSABLE_ANDROID or RESTRICTED_PC_UI; target app/window; allowed and denied action/data classes; egress; step/time/byte caps; confirmations; expiry; kill/revoke. No implicit cross-adapter grant.
3. MODEL-AGNOSTIC CORE: receive a terse orient card plus an observed CapabilityManifest. Adapt to measured capabilities, never a model-name stereotype. The model proposes actions; it never receives a raw host/device handle.
4. POLICY/ACTION BROKER: fail closed; validate consent, current foreground target, state freshness, capability, budgets, and consequence class. Execute one bounded action; stop on focus/state change, ambiguity, stale consent, denial, expiry, or kill.
5. ANDROID ADAPTER: disposable AVD first, synthetic accounts/data, restricted network, no host mounts/shared clipboard/real phone bridge, known snapshot reset after every test. Android documents that virtual state persists and that emulator networking can reach host services, so isolation/reset must be explicit.
6. PC ADAPTER: separate grant; foreground-window and screen-region allowlist; semantic UI/WebDriver-style observation before coordinates; narrow click/type/scroll/navigation verbs; no shell, filesystem, credential store, installer, settings, resident service, or arbitrary network primitive. W3C recommends explicit user enablement, loopback-limited control, and visible automation state. If CDP is used, pin a reviewed protocol because tip-of-tree has no compatibility guarantee; never expose its control endpoint.
7. RECEIPTS: append-only request/consent/capability/policy hashes, adapter version, bounded action category, result, side-effect class, stop reason, and independent acceptance check. Raw screenshots/UI/logs remain private and short-lived; public receipt is only minimal status plus non-sensitive hashes/counters.

STAGES: contract/denial tests → deterministic canned-UI simulator → offline disposable emulator with synthetic data → isolated PC observation-only dry run → owner-present one harmless reversible canary → limited session only after independent receipts. Test forged identity, prompt injection, replay, stale state, focus change, over-cap data, prohibited actions, timeout/kill, loop/runaway, unexpected egress, and honest FAILURE/HOLD.

BOUNDARY: no hive-mind dump, live inventory, install, emulator launch, device/browser control, private attachment, external egress, or source/push action is performed by this packet. Filing 108/109 controls private execution; 102/106 controls Commons source. Architecture is ready; capability remains UNKNOWN until separately authorized observation.
