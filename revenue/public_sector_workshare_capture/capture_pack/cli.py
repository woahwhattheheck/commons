from __future__ import annotations
import argparse, json
from pathlib import Path
from .core import CaptureError, build_target_packet, compile_pack, verify_packet


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="public-sector-workshare")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("manifest", type=Path)
    c.add_argument("--as-of", required=True)
    c.add_argument("--freshness-days", type=int, default=7)
    v = sub.add_parser("verify")
    v.add_argument("packet", type=Path)
    t = sub.add_parser("target")
    t.add_argument("packet", type=Path)
    t.add_argument("--opportunity", required=True)
    t.add_argument("--target-company", required=True)
    t.add_argument("--channel", required=True)
    t.add_argument("--address", required=True)
    t.add_argument("--relationship-checked", action="store_true")
    t.add_argument("--lease-acquired", action="store_true")
    t.add_argument("--provider-history-rechecked", action="store_true")
    t.add_argument("--opportunity-facts-revalidated", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.cmd == "compile":
            raw = json.loads(args.manifest.read_text(encoding="utf-8"))
            out = compile_pack(raw, as_of=args.as_of, freshness_days=args.freshness_days)
            print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
            return 0
        if args.cmd == "verify":
            raw = json.loads(args.packet.read_text(encoding="utf-8"))
            ok = verify_packet(raw)
            print(json.dumps({"valid": ok}))
            return 0 if ok else 2
        raw = json.loads(args.packet.read_text(encoding="utf-8"))
        out = build_target_packet(
            raw, opportunity_id=args.opportunity, target_company=args.target_company,
            channel=args.channel, address=args.address,
            relationship_checked=args.relationship_checked,
            lease_acquired=args.lease_acquired,
            provider_history_rechecked=args.provider_history_rechecked,
            opportunity_facts_revalidated=args.opportunity_facts_revalidated,
        )
        print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if out["ready_for_owner_transport_review"] else 2
    except (CaptureError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc), "state": "HOLD"}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
