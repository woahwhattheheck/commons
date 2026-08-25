"""Copy the 42 Kotlin files that GitHub lda/ is missing. Additive. No keystore. No weights."""
from pathlib import Path
import shutil

src = Path(r"C:\Users\lucys\Desktop\LocalDeviceAgent\app\src\main\java\com\local\deviceagent")
dst = Path(r"C:\Users\lucys\Desktop\COMMONS\lda\app\src\main\java\com\local\deviceagent")
dst.mkdir(parents=True, exist_ok=True)

on_gh = set("""
AgentApp AgentCallScreeningService AgentControl AgentLog AgentMemory AgentService
AuthGateActivity ChatActivity ChatStore ConfirmationOverlay DebugLogActivity DeviceStats
FloatingButtonService InputOverlay IntroDialog MainActivity MemoryActivity NotificationHelper
Ocr PixelMap ScreenManager SettingsActivity SettingsManager SmsReceiver TaskDetailActivity
TaskHistory TaskLogActivity TrainingActivity TrainingData Ui VoiceCaptureService VoskModelManager
""".split())

n = b = 0
for p in sorted(src.glob("*.kt")):
    if p.stem in on_gh:
        continue
    dest = dst / p.name
    shutil.copy2(p, dest)
    n += 1
    b += dest.stat().st_size
    print(f"{dest.stat().st_size:8d} {p.name}")
print(f"COPIED files={n} bytes={b} -> {dst}")
