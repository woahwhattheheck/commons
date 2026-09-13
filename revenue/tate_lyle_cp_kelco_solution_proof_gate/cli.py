from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .gate import compile_artifacts, strict_json_loads, verify_artifacts, write_artifacts_exclusive
except ImportError:
    from gate import compile_artifacts, strict_json_loads, verify_artifacts, write_artifacts_exclusive


def _load_packet(path: str):
    return strict_json_loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Offline portfolio integration solution-proof gate")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compile")
    c.add_argument("source")
    c.add_argument("output_dir")
    c.add_argument("--expected-snapshot-sha256", required=True)
    c.add_argument("--expected-policy-sha256", required=True)
    c.add_argument("--evaluation-time", required=True)
    v = sub.add_parser("verify")
    v.add_argument("source")
    v.add_argument("output_dir")
    v.add_argument("--expected-snapshot-sha256", required=True)
    v.add_argument("--expected-policy-sha256", required=True)
    v.add_argument("--evaluation-time", required=True)
    args = p.parse_args(argv)
    packet = _load_packet(args.source)
    kwargs = dict(
        expected_snapshot_sha256=args.expected_snapshot_sha256,
        expected_policy_sha256=args.expected_policy_sha256,
        evaluation_time=args.evaluation_time,
    )
    if args.command == "compile":
        artifacts = compile_artifacts(packet, **kwargs)
        write_artifacts_exclusive(args.output_dir, artifacts)
        print(json.dumps({"written": sorted(artifacts), "output_dir": args.output_dir}, sort_keys=True))
        return 0
    artifacts = {}
    for name in ("result.json", "evidence_manifest.json", "report.md", "receipt.json"):
        artifacts[name] = (Path(args.output_dir) / name).read_bytes()
    ok = verify_artifacts(packet, artifacts, **kwargs)
    print(json.dumps({"verified": ok}, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
