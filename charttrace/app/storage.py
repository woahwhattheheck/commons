"""Atomic local persistence for the synthetic vault envelope."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping

from .vault import (
    VAULT_MODE,
    VaultError,
    envelope_contains_protected_fields,
    inspect_envelope,
)


class LocalStateStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.state_path = self.data_dir / "charttrace-state.json"

    def load(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {}
        with self.state_path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError("ChartTrace state root must be an object.")
        classification = inspect_envelope(value)
        if classification["kind"] == "legacy_plaintext":
            raise VaultError(
                "Plaintext or unverified state cannot be unlocked by the "
                f"{VAULT_MODE} stub."
            )
        protected = envelope_contains_protected_fields(value)
        if protected:
            raise VaultError(
                f"Synthetic stub refused protected field on disk: {protected}."
            )
        return value

    def save(self, value: Mapping[str, Any]) -> None:
        classification = inspect_envelope(value)
        if classification["kind"] != "synthetic_stub":
            raise VaultError("Refusing to write a non-stub vault envelope.")
        if value.get("encryption_claimed") is True:
            raise VaultError("Synthetic stub cannot claim encryption.")
        protected = envelope_contains_protected_fields(value)
        if protected:
            raise VaultError(
                f"Synthetic stub refused to persist protected field: {protected}."
            )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.state_path)
