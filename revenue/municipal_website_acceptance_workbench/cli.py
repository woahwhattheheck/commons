from __future__ import annotations

import argparse
from pathlib import Path

from .fixture import AS_OF, build_synthetic_case
from .gate import build_gate_artifacts, verify_gate_artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build municipal website acceptance evidence fixture")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    rows, _ = build_synthetic_case()
    artifacts = build_gate_artifacts(rows, as_of=AS_OF)
    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / "acceptance-manifest.json"
    md_path = args.out / "acceptance-packet.md"
    sha_path = args.out / "SHA256SUMS"
    json_path.write_bytes(artifacts.json_bytes)
    md_path.write_bytes(artifacts.markdown_bytes)
    sha_path.write_text(
        f"{artifacts.manifest_sha256}  {json_path.name}\n"
        f"{artifacts.markdown_sha256}  {md_path.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    valid = verify_gate_artifacts(
        artifacts.json_bytes,
        artifacts.markdown_bytes,
        manifest_sha256=artifacts.manifest_sha256,
        markdown_sha256=artifacts.markdown_sha256,
    )
    summary = artifacts.manifest["summary"]
    print(
        f"VALID={str(valid).lower()} checks={summary['check_count']} "
        f"pass={summary['pass_count']} hold={summary['hold_count']} "
        f"state={summary['release_state']} manifest_sha256={artifacts.manifest_sha256}"
    )
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
