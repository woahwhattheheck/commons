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

The outputs are `dist\ChartTrace.exe` and
`dist\installer\ChartTrace-1.1-UNSIGNED_SYNTHETIC-Setup.exe`. Both are
deliberately labeled `UNSIGNED_SYNTHETIC` with `signing_state=unsigned`.
Code-signing must be a separate controlled release process; this script does
not imply or fabricate a signature.

ChartTrace opens no public listener. Optional same-device launcher handoff uses
a Windows named pipe (and an `AF_UNIX` socket only on non-Windows test hosts).
The application includes no Commons login, telemetry, analytics, external
scripts, or external fonts.
