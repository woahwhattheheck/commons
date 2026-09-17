"""Deterministic visual-evidence-to-action gate for OpenCV AI Competition 2026."""

from .core import (
    GateError,
    compile_synthetic_run,
    evaluate_synthetic_suite,
    generate_synthetic_scene,
    verify_trace,
)

__all__ = [
    "GateError",
    "compile_synthetic_run",
    "evaluate_synthetic_suite",
    "generate_synthetic_scene",
    "verify_trace",
]
