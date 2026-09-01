# Windows packaging

ChartTrace is a native, per-user Windows desktop application. It is not a web
site, browser tab, phone download, or TCP service.

Build prerequisites:

- Windows with Python 3 and Tcl/Tk
- Current PyInstaller (`py -m pip install --upgrade pyinstaller`)
- Inno Setup 6 on `PATH` for the installer step

From the repository root:

```powershell
.\charttrace\packaging\build_windows.ps1
```

On a Windows build host the outputs are `dist\ChartTrace.exe` and
`dist\installer\ChartTrace-1.1-UNSIGNED_SYNTHETIC-Setup.exe`. Both are
deliberately labeled `UNSIGNED_SYNTHETIC` with `signing_state=unsigned`.
`unsigned_artifact.py` always writes a hash-receipt zip, a headless
launcher smoke, and a deterministic unsigned PE32 stub. `windows_pe_built`
is true for that stub; `windows_clean_vm` stays
`NOT_AVAILABLE_ON_THIS_HOST` unless this host is Windows or a wine smoke
actually ran. Code-signing must be a separate controlled release process;
these scripts do not imply or fabricate a signature. `SYNTHETIC_RELEASED`
remains false.

ChartTrace opens no public listener. Optional same-device launcher handoff
uses an authenticated filesystem mailbox with typed JSON frames. The
application includes no Commons login, telemetry, analytics, external
scripts, or external fonts.
