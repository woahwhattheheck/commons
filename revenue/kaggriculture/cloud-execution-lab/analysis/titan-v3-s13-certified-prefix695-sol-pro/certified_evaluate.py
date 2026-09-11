#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
'''Run the shared evaluator while retaining certified-candidate diagnostics.'''
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from activation_capture import DIAGNOSTIC_NAME, DIAGNOSTIC_SCHEMA, MARKER_NAME

MAX_DIAGNOSTIC_BYTES = 64 * 1024


class CertifiedEvaluateError(RuntimeError):
    pass


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def strict_json(data: bytes) -> Any:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate diagnostic JSON key: {key!r}")
            out[key] = value
        return out
    def reject(value):
        raise ValueError(f"non-finite diagnostic JSON constant: {value}")
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)


def load_evaluator(path: Path):
    spec = importlib.util.spec_from_file_location("s13_activation_evaluator", path)
    if spec is None or spec.loader is None:
        raise CertifiedEvaluateError(f"cannot load evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(spec.name)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if previous is None:
            sys.modules.pop(spec.name, None)
        else:
            sys.modules[spec.name] = previous
        raise
    return module


def install_capture(module) -> None:
    original_init = module.Actor.__init__
    original_close = module.Actor.close

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            Path(self.directory.name, MARKER_NAME).write_text(
                DIAGNOSTIC_SCHEMA + "\n", encoding="utf-8"
            )
        except OSError as exc:
            self.stats["candidate_diagnostics_capture_setup_error"] = (
                f"{type(exc).__name__}: {exc}"[:1000]
            )

    def close(self):
        if not getattr(self, "_s13_activation_captured", False):
            self._s13_activation_captured = True
            path = Path(self.directory.name, DIAGNOSTIC_NAME)
            self.stats["candidate_diagnostics"] = None
            if path.is_file():
                try:
                    data = path.read_bytes()
                    if len(data) > MAX_DIAGNOSTIC_BYTES:
                        raise ValueError(
                            f"diagnostic file exceeds {MAX_DIAGNOSTIC_BYTES} bytes"
                        )
                    parsed = strict_json(data)
                    if not isinstance(parsed, dict):
                        raise ValueError("diagnostic root is not an object")
                    self.stats["candidate_diagnostics"] = parsed
                    self.stats["candidate_diagnostics_sha256"] = hashlib.sha256(
                        data
                    ).hexdigest()
                    self.stats["candidate_diagnostics_bytes"] = len(data)
                except (OSError, UnicodeError, ValueError, TypeError) as exc:
                    self.stats["candidate_diagnostics_capture_error"] = (
                        f"{type(exc).__name__}: {exc}"[:1000]
                    )
        return original_close(self)

    module.Actor.__init__ = init
    module.Actor.close = close


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--expected-evaluator-git-blob", required=True)
    known, remaining = parser.parse_known_args(argv)
    data = known.evaluator.read_bytes()
    actual_blob = git_blob_sha1(data)
    if actual_blob != known.expected_evaluator_git_blob:
        raise CertifiedEvaluateError(
            f"evaluator blob mismatch: expected={known.expected_evaluator_git_blob} actual={actual_blob}"
        )
    module = load_evaluator(known.evaluator.resolve(strict=True))
    install_capture(module)
    sys.argv = [str(known.evaluator)] + remaining
    return int(module.main())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CertifiedEvaluateError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
