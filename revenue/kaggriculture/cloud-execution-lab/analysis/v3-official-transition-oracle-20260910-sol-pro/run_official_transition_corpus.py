#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from official_transition_corpus import run_corpus
from official_transition_oracle import canonical_bytes, write_json_atomic


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)

    def retain(name, envelope):
        write_json_atomic(output / f"{name}.json", envelope)

    evidence, _envelopes = run_corpus(
        engine_path=args.engine,
        worker_path=args.worker,
        on_result=retain,
    )
    write_json_atomic(output / "EVIDENCE.json", evidence)
    files = sorted(path for path in output.iterdir() if path.is_file())
    manifest = "".join(
        f"{sha256_file(path)}  {path.name}\n"
        for path in files
    ).encode("utf-8")
    (output / "SHA256SUMS").write_bytes(manifest)
    print((canonical_bytes({
        "evidence_sha256": evidence["evidence_sha256"],
        "files": len(files) + 1,
        "output_dir": output.name,
    }) + b"\n").decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
