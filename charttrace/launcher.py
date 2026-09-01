"""ChartTrace v1.1 native standalone launcher."""

import argparse
import json
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
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    options = build_parser().parse_args(argv)
    controller = ChartTraceController(data_dir=options.data_dir)
    window = ChartTraceWindow(controller=controller, headless=options.headless)
    if options.headless:
        print(
            json.dumps(
                {
                    "app_version": APP_VERSION,
                    "build_label": BUILD_LABEL,
                    "signing_state": SIGNING_STATE,
                    "transport": "filesystem_mailbox",
                    "startup_screen": window.screen_snapshot(ScreenId.UNLOCK),
                },
                sort_keys=True,
            )
        )
        return 0
    window.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
