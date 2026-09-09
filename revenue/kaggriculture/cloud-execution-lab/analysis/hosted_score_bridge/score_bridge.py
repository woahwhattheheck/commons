#!/usr/bin/env python3
"""Fail-closed bridge between local Titan simulations and hosted score evidence."""

from __future__ import annotations

try:
    from .cli import main
    from .contracts import BridgeConfig, HostedEpisode, IntegrityError, LocalCell
    from .normalize import load_jsonl, normalize_hosted, normalize_local
    from .report import build_report, render_markdown
except ImportError:  # direct script execution
    from cli import main
    from contracts import BridgeConfig, HostedEpisode, IntegrityError, LocalCell
    from normalize import load_jsonl, normalize_hosted, normalize_local
    from report import build_report, render_markdown

__all__ = [
    "BridgeConfig",
    "HostedEpisode",
    "IntegrityError",
    "LocalCell",
    "build_report",
    "load_jsonl",
    "normalize_hosted",
    "normalize_local",
    "render_markdown",
]

if __name__ == "__main__":
    raise SystemExit(main())
