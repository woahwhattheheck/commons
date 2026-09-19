"""Replay fault controls for COPPERLINE's evidence-conservation acceptance.

The source and two inputs are captured once. Only private temporary copies are
mutated; original files are checked for byte equality before return.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def changes():
    return (
        ("changed_historical_note", "packet", ("qualification", "adult_learning_packaging", "note"), "New unsupported audit"),
        ("invented_evidence", "packet", ("qualification", "w9_available", "evidence_refs"), ["invented:proof"]),
        ("promoted_lms_history", "packet", ("qualification", "two_lms_platform_implementations", "state"), "VERIFIED"),
        ("calendar_became_capacity", "packet", ("qualification", "start_capacity_2026_10_13", "state"), "VERIFIED"),
        ("bool_replaced_zero", "packet", ("proposal", "proposed_total_usd"), False),
        ("price_filled_without_review", "packet", ("proposal", "year1_license_usd"), 100),
        ("bidder_complete", "packet", ("proposal", "attachments_complete"), True),
        ("platform_selected", "packet", ("proposal", "platform_recommendation"), "SELECTED"),
        ("contact_authorized", "packet", ("authority", "external_contact_authorized"), True),
        ("integer_replaced_false", "workshare", ("authority", "payment_authorized"), 0),
        ("accepted_price", "workshare", ("commercial", "commercial_status"), "ACCEPTED"),
        ("buyer_fit_asserted", "workshare", ("commercial", "buyer_budget_integration_state"), "WITHIN_CAP"),
        ("contact_gate_removed", "workshare", ("single_writer_gate", "muse_dm_clearance_required"), False),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, type=Path)
    args = parser.parse_args()
    lane = args.lane.resolve()
    checker = Path(__file__).with_name("test_generation_independent.py")
    captures = {
        checker: checker.read_bytes(),
        lane / "current_packet.json": (lane / "current_packet.json").read_bytes(),
        lane / "partner_workshare.json": (lane / "partner_workshare.json").read_bytes(),
    }
    p0 = json.loads(captures[lane / "current_packet.json"])
    w0 = json.loads(captures[lane / "partner_workshare.json"])
    rows = []
    with tempfile.TemporaryDirectory(prefix="framer-conservation-controls-") as tmp:
        root = Path(tmp)
        check = root / checker.name
        check.write_bytes(captures[checker])
        for name, target, keys, value in (("unchanged_control", "packet", (), None), *changes()):
            folder = root / name
            folder.mkdir()
            packet, workshare = copy.deepcopy(p0), copy.deepcopy(w0)
            if keys:
                node = packet if target == "packet" else workshare
                for key in keys[:-1]:
                    node = node[key]
                node[keys[-1]] = value
            for filename, obj in (("current_packet.json", packet), ("partner_workshare.json", workshare)):
                (folder / filename).write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            for flag in ((), ("-O",)):
                command = [sys.executable, *flag, str(check), "--lane", str(folder)]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=20)
                # A loader failure is not accepted as a successful negative test.
                diagnostic = proc.stderr
                if "Ran 10 tests" not in diagnostic or "ERROR" in diagnostic:
                    raise RuntimeError(f"invalid control execution: {name} {flag}: {diagnostic}")
                expected = 0 if not keys else 1
                if proc.returncode != expected:
                    raise RuntimeError(f"control {name} {flag}: expected {expected}, got {proc.returncode}")
                rows.append({"case": name, "optimized": bool(flag), "exit": proc.returncode,
                             "expected_exit": expected, "tests_run": 10, "result": "EXPECTED"})
    if any(path.read_bytes() != data for path, data in captures.items()):
        raise RuntimeError("source or input bytes changed during replay")
    receipt = {
        "schema": "framer.evidence_conservation_controls/v1",
        "checker_sha256": hashlib.sha256(captures[checker]).hexdigest(),
        "packet_sha256": hashlib.sha256(captures[lane / "current_packet.json"]).hexdigest(),
        "workshare_sha256": hashlib.sha256(captures[lane / "partner_workshare.json"]).hexdigest(),
        "python": sys.version.split()[0], "inputs_unchanged": True,
        "runs": rows, "run_count": len(rows),
        "scope": "Conservation-test controls; not candidate evaluator, hosted CI, or integration readiness.",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
