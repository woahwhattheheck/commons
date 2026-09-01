"""Compatibility boundary for the audited synthetic-vault contract."""

import json
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .controller import ChartTraceController as _BaseController
from .paths import validate_local_output_path
from .storage import VAULT_FORMAT
from .vault import (
    SYNTHETIC_RELEASED,
    VAULT_MODE,
    VaultError,
    assert_synthetic_stub,
    persistable_case_stub,
)


def _inspect_existing_state(data_dir: Path) -> None:
    state_path = data_dir / "charttrace-state.json"
    if not state_path.exists():
        return
    try:
        envelope = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VaultError("State is not a valid synthetic vault.") from error
    if not isinstance(envelope, dict) or envelope.get("format") != VAULT_FORMAT:
        raise VaultError("Legacy plaintext state is rejected.")
    assert_synthetic_stub(envelope)


class ChartTraceController(_BaseController):
    """Base policy controller with pre-unlock synthetic-vault inspection."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        persist: bool = True,
    ):
        default_dir = Path.home() / "AppData" / "Local" / "ChartTrace"
        selected_dir = Path(data_dir) if data_dir else default_dir
        if persist:
            _inspect_existing_state(selected_dir)
        super().__init__(data_dir=selected_dir, persist=persist)

    def _save(self) -> None:
        super()._save()
        if not self.persist:
            return
        state_path = self.store.state_path
        envelope = json.loads(state_path.read_text(encoding="utf-8"))
        envelope.update(
            {
                "schema_version": 2,
                "vault_mode": VAULT_MODE,
                "encryption_claimed": False,
                "protected_data_present": False,
                "can_unlock_protected_data": False,
                "synthetic_released": SYNTHETIC_RELEASED,
                "cases": [
                    persistable_case_stub(case.to_dict())
                    for case in self.cases.values()
                ],
            }
        )
        temporary = state_path.with_name(
            f".charttrace-envelope-{uuid4().hex}.tmp"
        )
        temporary.write_text(
            json.dumps(envelope, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, state_path)

    def build_release(self, case_id: str, destination: Path) -> Path:
        validate_local_output_path(destination)
        return super().build_release(case_id, destination)
