# Windows packaging

ChartTrace is a native per-user Windows desktop application. It is not a web
site, browser tab, TCP service, or background agent. The unused filesystem
mailbox is retired, excluded from the frozen program, and reported as
`transport=none`.

## Pinned unsigned build

The committed build contract requires CPython 3.12 with Tcl/Tk and
PyInstaller 6.22.2. Keep the build dependency in an isolated environment:

```powershell
python -m venv .venv-charttrace-build
.\.venv-charttrace-build\Scripts\python.exe -m pip install PyInstaller==6.22.2
.\charttrace\packaging\build_windows.ps1 \
  -PythonExe .\.venv-charttrace-build\Scripts\python.exe \
  -OutputRoot .\dist\charttrace-unsigned \
  -SkipInstaller
```

The script refuses a nonempty output directory and never uses the old
synthetic PE helper. It freezes `charttrace/launcher.py` from
`ChartTrace.spec`, launches that exact `ChartTrace.exe` with
`--headless --startup-receipt`, requires `frozen=true` and an executable
path match, then emits:

- the actual unsigned frozen executable;
- a portable ZIP containing that executable;
- a frozen-startup receipt;
- a CycloneDX-format SBOM;
- the complete PyInstaller log;
- SHA-256 hashes for the executable, ZIP, SBOM, startup receipt, build log,
  and every product/build input.

Inno Setup 6 is optional for a later installer exercise. The current build
must remain `UNSIGNED_SYNTHETIC`, `production=false`, and
`synthetic_released=false`. A same-host frozen smoke is not a clean-VM
receipt. Clean non-development Windows install/relaunch/uninstall,
keyboard/contrast/DPI usability evidence, external Authenticode signing,
and owner authorization for production distribution remain release gates.

