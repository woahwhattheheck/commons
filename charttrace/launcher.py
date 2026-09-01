"""ChartTrace v1.1 native standalone launcher."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from charttrace.app import APP_VERSION, BUILD_LABEL, SIGNING_STATE, ChartTraceController
from charttrace.ui import ChartTraceWindow, ScreenId


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the native ChartTrace window.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Local application state directory.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Validate startup without creating a native window.",
    )
    parser.add_argument(
        "--startup-receipt",
        type=Path,
        default=None,
        help="Write machine-readable headless startup evidence to this local file.",
    )
    return parser


def _write_startup_receipt(path: Path, payload: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError("Startup receipt destination must not already exist.")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main(argv: Optional[Sequence[str]] = None) -> int:
    options = build_parser().parse_args(argv)
    if options.startup_receipt is not None and not options.headless:
        raise ValueError("--startup-receipt requires --headless.")
    controller = ChartTraceController(data_dir=options.data_dir)
    window = ChartTraceWindow(controller=controller, headless=options.headless)
    if options.headless:
        startup = {
            "app_version": APP_VERSION,
            "build_label": BUILD_LABEL,
            "signing_state": SIGNING_STATE,
            "transport": "none",
            "ipc_enabled": False,
            "frozen": bool(getattr(sys, "frozen", False)),
            "process_executable": str(Path(sys.executable).resolve()),
            "startup_screen": window.screen_snapshot(ScreenId.UNLOCK),
        }
        if options.startup_receipt is not None:
            _write_startup_receipt(options.startup_receipt, startup)
        if sys.stdout is not None:
            print(json.dumps(startup, sort_keys=True))
        return 0
    window.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

