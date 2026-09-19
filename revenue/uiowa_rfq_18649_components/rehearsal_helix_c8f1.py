"""One-shot fictional reviewer rehearsal; does not modify the published assessor."""
from __future__ import annotations
import copy
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from components import assess, bundle, json_bytes
from example import example

PINS = {
    "components.py": "57cf8a1c720eeb967d39cea4d7f92c405cd27ec4",
    "example.py": "339da836e34e620061d00961979dc4b0c538ef9e",
    "verify_bundle.py": "60de56241554f459e6cd6966892fee7ec4de9588",
    "test_components.py": "1f353d937b6ce0612be3a938f53aabfd87bc6797",
    "test_verifier.py": "6a280501e7f89e1d7346c56ca4d9ef1694834cc0",
}
SOURCE = "59d94dfa2d1441aa05bfe89a9bd6d8256bbf6f36"
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def component(doc, cid):
    return next(x for x in doc["components"] if x["id"] == cid)


def evidence(doc, cid, kind, label, advisory_id=None):
    eid = f"HELIX-{cid}-{label}"
    doc["evidence"].append({"id": eid, "kind": kind, "observed_on": "2026-09-19",
        "locator": "fictional://helix-c8f1/" + eid,
        "component_ids": [cid], "advisory_id": advisory_id})
    return [eid]


def scenarios():
    baseline = example()
    cases = {"B0": baseline}
    d = copy.deepcopy(baseline); c = component(d, "C03")
    c["support"].update(state="supported", ends_on="2027-12-31",
        evidence=evidence(d, "C03", "support", "support"))
    cases["S1"] = d
    d = copy.deepcopy(baseline)
    component(d, "C03")["maintenance"].update(effort_low_days=3, effort_high_days=5)
    cases["E1"] = d
    d = copy.deepcopy(baseline); a = component(d, "C06")["advisories"][0]
    a["exception_until"] = "2027-03-01"
    a["disposition_evidence"] = evidence(d, "C06", "exception", "extension", a["id"])
    cases["X1"] = d
    d = copy.deepcopy(baseline)
    component(d, "C06")["advisories"][0]["disposition_evidence"] = []
    cases["X2"] = d
    d = copy.deepcopy(baseline); a = component(d, "C03")["advisories"][0]
    a["applicability_evidence"] = evidence(d, "C03", "advisory", "applicability", a["id"])
    a["exposure_evidence"] = evidence(d, "C03", "exposure", "exposure", a["id"])
    cases["C1"] = d
    d = copy.deepcopy(baseline); a = component(d, "C04")["advisories"][0]
    a["disposition_evidence"] = evidence(d, "C04", "closure", "closure", a["id"])
    cases["V1"] = d
    d = copy.deepcopy(baseline); c = component(d, "C02"); a = c["advisories"][0]
    c["support"].update(state="supported", ends_on="2027-12-31",
        evidence=evidence(d, "C02", "support", "support"))
    c["owner_role"] = "Fictional shared-service maintenance lead"
    c["review_due_on"] = "2026-10-15"
    a["applicability"] = "not_affected"
    a["applicability_evidence"] = evidence(d, "C02", "advisory", "applicability", a["id"])
    a["exposure"] = "not_observed"
    a["exposure_evidence"] = evidence(d, "C02", "exposure", "exposure", a["id"])
    a["disposition"] = "resolved"
    a["disposition_evidence"] = evidence(d, "C02", "closure", "closure", a["id"])
    cases["R1"] = d
    return cases


def row(report, collection, cid):
    return next((x for x in report[collection] if x["component_id"] == cid), None)


def files(path):
    return {p.name: p.read_bytes() for p in path.iterdir() if p.is_file()}


def run(out: Path, optimized: bool):
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        check(actual == expected, "Source mismatch: " + name)
    out.mkdir(exist_ok=False)
    commands = []
    python = [sys.executable] + (["-O"] if optimized else [])

    def command(args, expected=0):
        argv = python + [str(HERE / args[0])] + [str(x) for x in args[1:]]
        start = time.monotonic()
        result = subprocess.run(argv, cwd=HERE, capture_output=True, text=True, timeout=20)
        commands.append({"argv": argv, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
            "elapsed_seconds": round(time.monotonic() - start, 6)})
        check(result.returncode == expected, str(commands[-1]))
        return result

    cases = scenarios(); baseline = assess(cases["B0"]); results = {}; reports = {}
    targets = {"S1": "C03", "E1": "C03", "X1": "C06", "X2": "C06",
               "C1": "C03", "V1": "C04", "R1": "C02"}
    for case, doc in cases.items():
        raw = json_bytes(doc); input_path = out / (case + ".json"); input_path.write_bytes(raw)
        output_path = out / case
        command(["components.py", input_path, "--out", output_path])
        command(["verify_bundle.py", input_path, output_path])
        observed = files(output_path)
        check(observed == bundle(doc), case + ": complete output differs from the public API")
        check(input_path.read_bytes() == raw, case + ": input changed")
        report = json.loads(observed["assessment.json"]); reports[case] = report
        check(report["summary"]["component_count"] == 7, case + ": lost an inventory record")
        check(report["summary"]["service_count"] == 3, case + ": lost a service")
        check(report["summary"]["advisory_record_count"] == 5, case + ": lost an advisory")
        check(report["services"] == baseline["services"], case + ": changed service definitions")
        cid = targets.get(case)
        changes = {}
        if cid:
            for collection in ("components", "advisories", "roadmap"):
                old = {x["component_id"]: x for x in baseline[collection]}
                new = {x["component_id"]: x for x in report[collection]}
                check({k: v for k, v in old.items() if k != cid} ==
                      {k: v for k, v in new.items() if k != cid}, case + ": unrelated row changed")
                before, after = old.get(cid), new.get(cid)
                if before != after:
                    keys = set(before or {}) | set(after or {})
                    changes[collection] = {k: {"before": (before or {}).get(k), "after": (after or {}).get(k)}
                        for k in sorted(keys) if (before or {}).get(k) != (after or {}).get(k)}
        results[case] = {"target": cid, "input_sha256": sha(raw),
            "file_sha256": {n: sha(b) for n, b in sorted(observed.items())},
            "summary": report["summary"], "changed_fields": changes}

    check(row(reports["S1"], "components", "C03")["support_state"] == "supported", "S1 support")
    check(reports["S1"]["advisories"] == baseline["advisories"], "S1 must not settle advisories")
    check(reports["S1"]["summary"]["unestimated_item_count"] == 1, "S1 must not estimate effort")
    check(reports["E1"]["components"] == baseline["components"] and
          reports["E1"]["advisories"] == baseline["advisories"], "E1 must not change evidence-qualified states")
    check((reports["E1"]["summary"]["known_effort_low_days"], reports["E1"]["summary"]["known_effort_high_days"],
           reports["E1"]["summary"]["unestimated_item_count"]) == (12, 21, 0), "E1 total")
    for key in ("X1", "X2"):
        check(row(reports[key], "advisories", "C06")["qualified_reported_exposure"] == "confirmed", key + ": exposure erased")
    check(row(reports["X1"], "roadmap", "C06")["reasons"] == ["establish_support_horizon"], "X1 reasons")
    check(row(reports["X1"], "roadmap", "C06")["priority"] == 3, "X1 priority")
    check(row(reports["X2"], "advisories", "C06")["record_disposition"] == "unverified_exception", "X2 disposition")
    check(row(reports["X2"], "roadmap", "C06")["priority"] == 1, "X2 priority")
    check(row(reports["C1"], "advisories", "C03")["conflicting_records"] is True, "C1 conflict")
    check(row(reports["C1"], "roadmap", "C03")["priority"] == 1, "C1 priority")
    check(row(reports["V1"], "advisories", "C04")["record_disposition"] == "documented_closure", "V1 disposition")
    check(row(reports["V1"], "components", "C04")["inventory_evidence_quality"] == "stale", "V1 inventory")
    check(row(reports["V1"], "advisories", "C04")["qualified_reported_exposure"] == "unknown", "V1 exposure")
    check(row(reports["R1"], "roadmap", "C02") is None, "R1 maintenance remains")
    check(row(reports["R1"], "components", "C02")["service_ids"] == ["ESS-DEMO", "RIS-DEMO"], "R1 consumers lost")
    check((reports["R1"]["summary"]["maintenance_item_count"], reports["R1"]["summary"]["known_effort_low_days"],
           reports["R1"]["summary"]["known_effort_high_days"], reports["R1"]["summary"]["unestimated_item_count"]) == (4, 4, 7, 1), "R1 totals")

    baseline_files = files(out / "B0")
    command(["components.py", out / "B0.json", "--out", out / "B0"], 2)
    check(files(out / "B0") == baseline_files, "Existing output was changed")
    command(["verify_bundle.py", out / "S1.json", out / "B0"], 2)
    check(files(out / "B0") == baseline_files, "Failed verification changed the baseline")
    invalid = copy.deepcopy(cases["S1"])
    component(invalid, "C03")["support"]["evidence"] = component(invalid, "C03")["inventory_evidence"]
    invalid_path = out / "wrong-kind.json"; invalid_path.write_bytes(json_bytes(invalid))
    command(["components.py", invalid_path, "--out", out / "wrong-kind"], 2)
    check(not (out / "wrong-kind").exists(), "Invalid input created a result directory")
    payload = {"source_commit": SOURCE, "source_blobs": PINS, "python": platform.python_version(),
        "platform": platform.platform(), "mode": "optimized" if optimized else "normal",
        "cases": results, "commands": commands,
        "negative_controls": {"existing_output_preserved": True, "changed_input_rejects_old_bundle": True,
                              "wrong_evidence_kind_rejected_before_output": True}}
    (out / "execution.json").write_bytes(json_bytes(payload))
    print(json.dumps({"mode": payload["mode"], "scenarios": len(results), "CLI_calls": len(commands),
                     "negative_controls": payload["negative_controls"]}, indent=2))


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve(), "--optimized" in sys.argv[2:])
