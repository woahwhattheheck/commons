"""Content hashes bound to Lane B prompts, policy, runtime, and authority packs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

from charttrace.grounding.loader import authority_library_bytes, load_pack_library
from charttrace.prompts.loader import load_prompt_library
from charttrace.peers.scope import GLOBAL_SCOPE_STATEMENT


_PEERS_DIR = Path(__file__).resolve().parent


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def prompt_content_sha256() -> str:
    library = load_prompt_library()
    blob = "\n".join(f"{pid}\n{library[pid]}" for pid in sorted(library))
    return sha256_text(blob)


def policy_content_sha256() -> str:
    return sha256_text(GLOBAL_SCOPE_STATEMENT)


def runtime_content_sha256() -> str:
    parts = []
    for name in ("contracts.py", "isolation.py", "runner.py", "validate.py"):
        parts.append((_PEERS_DIR / name).read_bytes())
    return sha256_bytes(b"\n".join(parts))


def authority_content_sha256() -> str:
    return sha256_bytes(authority_library_bytes())


def bound_content_hashes() -> Dict[str, str]:
    load_pack_library()
    load_prompt_library()
    return {
        "prompt_content_sha256": prompt_content_sha256(),
        "policy_content_sha256": policy_content_sha256(),
        "runtime_content_sha256": runtime_content_sha256(),
        "authority_content_sha256": authority_content_sha256(),
    }
