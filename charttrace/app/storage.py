"""Atomic local persistence for ChartTrace application state."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping


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
        return value

    def save(self, value: Mapping[str, Any]) -> None:
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
            # Windows ACLs are controlled by the containing user profile.
            pass
        os.replace(temporary, self.state_path)
