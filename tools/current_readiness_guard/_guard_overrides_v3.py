from __future__ import annotations

from ._guard_overrides import analyze_source as _analyze_source_v2, read_source
from ._model import Finding
from ._review_closure_v3 import additional_findings


def analyze_source(source: str | bytes, *, path: str = "<memory>") -> list[Finding]:
    return sorted(
        set(
            [
                *_analyze_source_v2(source, path=path),
                *additional_findings(source, path=path),
            ]
        )
    )


__all__ = ["analyze_source", "read_source"]
