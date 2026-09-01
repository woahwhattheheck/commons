"""Load versioned peer prompt templates from disk."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

_TEMPLATES = Path(__file__).resolve().parent / "templates"


def list_prompt_ids() -> List[str]:
    return sorted(p.stem for p in _TEMPLATES.glob("*.md"))


def load_prompt(prompt_id: str) -> str:
    path = _TEMPLATES / f"{prompt_id}.md"
    if not path.is_file():
        raise FileNotFoundError(f"unknown prompt template: {prompt_id}")
    return path.read_text(encoding="utf-8")


def load_prompt_library() -> Dict[str, str]:
    return {pid: load_prompt(pid) for pid in list_prompt_ids()}
