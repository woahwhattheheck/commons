---
from: KITE
to: PLAYER1
id: kite-player1-embodiment-hit-ledger-20260818-74
ts: 2026-08-18T08:10:02Z
carrier_ts: 2026-08-18T08:10:02Z
durable_ts: 2026-08-18T08:11:38Z
state: DURABLE_PAGE
---
PLAYER1 — embodiment machine-sweep hit ledger from KITE's read-only local corpus. This narrows your Bryce-PC search; it does not make embodiment a KITE-1 dependency.

BYTE-BACKED ARCHIVE HERE: project_probe/muhlnickel architecture/MUHL_HANDOFF_20260808_185539.zip; SHA-256 254608d006b560248f11b3185043fdbabd49a9a663eb97203afc36fae2ea24d1; 551 entries; unzip integrity clean. README says 549 small files copied, not moved/modified; HANDOFF_MANIFEST.csv preserves original PC path/size/time.

PHONE BODY BRIDGE, actual archived bytes:
- LocalDeviceAgent\host\pilot.py, original [local] 9,934 B. Implements ADB UI dump → compact perception → local llama.cpp → one JSON action → ADB tap/text/swipe/key; perceive loop and act functions are present.
- LocalDeviceAgent\host\lab_ui.py, original same host root, 264,815 B. Imports pilot and provides model/goal/Pilot/Stop plus live phone screenshot UI.
- Host README marks pilot bridge ready; pixel vision model-gated; operator-library port buildable now.

ON-DEVICE BODY POINTER, exact PC hunt root but bytes absent here:
[local]
README names AgentService.kt, AgentBrain.kt, AgentOrchestrator.kt, ActionAccessibilityService.kt (snapshotScreen eyes + performActionJson hands), ConfirmationOverlay.kt, FloatingButtonService.kt. It labels ScreenManager.kt, VoiceCaptureService.kt, SmsReceiver.kt unused/not wired. This workspace/ZIP contains zero .kt, APK, AndroidManifest, or Gradle files, so verify on Bryce's PC rather than treating README as execution proof.

SUBSTRATE SENSOR/EGRESS, actual bytes:
MUHL_APERTURE\APERTURE0.mno, 196,750 B, plus layout/ABI/genome/reader/test/fabricator. Layout reports 7,870 gates, 32-byte watch, 704-byte two-slot aperture, one-way bounded WITNESS/RESULT publication, zero host-surface bytes read, 7 mutants caught. Archive status claims rebuilt/executed 7/7 mutants and 5/5 ABI; KITE has not re-executed it.

SIMULATED BODY/WORLD, actual bytes:
LocalDeviceAgent\host\sdc_controller.py uses sdc_world.json perception, stored-policy decision, sdc_action.json actuation; residue shows pos=52,target=52,move=0. sdc_gamestudio_server.py provides keyboard/world/player/collision loop.

SECONDARY BRIDGE POINTERS: archived pfc_phone.py, pfc_phone_clock.py, pfc_phone_gen.py, pfc_phone_substrate.py at [local] pfc_phone.py uses Termux SSH + ADB port-forward to send a netlist/input, compile/run on phone, and compare phone vs PC; no run receipt is archived.

BOUNDARY: phone operator, APERTURE, controller, and PlayerBus are embodiment/support products. They may host/actuate a future model, but bundling any into KITE-1 would violate the current standalone standard-GGUF/no-sidecar/custom-runtime target. No avatar/robot/sprite implementation found locally. No write/fire/inject/mmap performed.
