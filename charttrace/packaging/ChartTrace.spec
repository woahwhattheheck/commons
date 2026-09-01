# PyInstaller specification for the native Windows executable.
from pathlib import Path

ROOT = Path(SPECPATH).parents[1]

a = Analysis(
    [str(ROOT / "charttrace" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (
            str(ROOT / "charttrace" / "packaging" / "build_manifest.json"),
            "charttrace/packaging",
        ),
    ],
    hiddenimports=["tkinter", "tkinter.ttk"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "http.server",
        "pydoc",
        "webbrowser",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ChartTrace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest=str(ROOT / "charttrace" / "packaging" / "charttrace.manifest"),
)
