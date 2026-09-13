from __future__ import annotations

import argparse
from datetime import datetime, timezone

from revenue.streaming_rendition_qa_pilot import PilotError, build_report, verify_report
from revenue.streaming_rendition_qa_pilot.artifacts import read_json_regular, write_artifacts


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bundle(raw):
    if not isinstance(raw, dict) or set(raw) != {"scope", "prospects"}:
        raise PilotError("bundle keys must be exactly scope/prospects")
    if not isinstance(raw["scope"], dict) or not isinstance(raw["prospects"], list):
        raise PilotError("bundle scope/prospects types invalid")
    return raw["scope"], raw["prospects"]


def main(argv=None):
    p = argparse.ArgumentParser(description="Streaming Rendition QA Pilot offline commercialization pack")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluate"); e.add_argument("bundle"); e.add_argument("--out-dir", required=True)
    v = sub.add_parser("verify"); v.add_argument("bundle"); v.add_argument("report")
    ns = p.parse_args(argv)
    try:
        scope, prospects = _bundle(read_json_regular(ns.bundle))
        if ns.cmd == "evaluate":
            report = build_report(scope, prospects, evaluated_at_utc=_now())
            write_artifacts(report, ns.out_dir)
            print(report["receipt_sha256"])
            return 0
        report = read_json_regular(ns.report)
        ok = verify_report(report, scope, prospects)
        print("VALID" if ok else "INVALID")
        return 0 if ok else 2
    except (PilotError, OSError, TypeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
