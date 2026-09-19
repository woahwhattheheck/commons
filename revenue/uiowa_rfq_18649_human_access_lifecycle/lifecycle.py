"""UIOWA-053: offline, evidence-bounded lifecycle review; never changes access."""
from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

META = ("schema_version", "provenance", "as_of")
TARGET = ("target_id", "case_id", "group", "scenario", "role", "system", "entitlement", "desired_state", "effective_at", "review_required")
EVIDENCE = ("evidence_id", "target_id", "kind", "observed_at", "state", "source_ref", "note")
KINDS = ("POLICY", "REQUESTED", "APPROVED", "APPLIED", "VERIFIED", "REVIEWED", "EMERGENCY_REVIEWED")
STATES = ("PRESENT", "ABSENT")
SCENARIOS = ("JOINER", "MOVER", "LEAVER", "EMERGENCY")
ESCAPE = "'=+-@\t\r\n"


class InputError(ValueError):
    """A named input problem, not an assessment finding."""


def keys(value, expected, where):
    if type(value) is not dict or set(value) != set(expected):
        raise InputError(f"{where}: expected exactly {', '.join(expected)}")


def text(value, where, allow_empty=False):
    if type(value) is not str or (not allow_empty and not value.strip()):
        raise InputError(f"{where}: nonempty text required")
    if len(value) > 10000:
        raise InputError(f"{where}: text exceeds 10000 characters")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise InputError(f"{where}: invalid Unicode") from exc
    return value


def instant(value, where):
    text(value, where)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("offset required")
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise InputError(f"{where}: valid offset-aware ISO datetime required") from exc


def validate(packet):
    keys(packet, (*META, "targets", "evidence"), "packet")
    if type(packet["schema_version"]) is not int or packet["schema_version"] != 1:
        raise InputError("schema_version: expected integer 1")
    text(packet["provenance"], "provenance")
    instant(packet["as_of"], "as_of")
    if type(packet["targets"]) is not list or not 1 <= len(packet["targets"]) <= 10000:
        raise InputError("targets: expected 1..10000 rows")
    if type(packet["evidence"]) is not list or len(packet["evidence"]) > 100000:
        raise InputError("evidence: expected a list of at most 100000 rows")
    ids, cases, logical_targets = {}, {}, set()
    for row in packet["targets"]:
        keys(row, TARGET, "target")
        for name in TARGET:
            if name != "review_required":
                text(row[name], f"target.{name}")
        if row["target_id"] in ids:
            raise InputError(f"duplicate target_id: {row['target_id']}")
        if row["group"] not in ("ESS", "RIS", "IAM") or row["scenario"] not in SCENARIOS:
            raise InputError("target: unknown group or scenario")
        if row["desired_state"] not in STATES or type(row["review_required"]) is not bool:
            raise InputError("target: invalid desired_state or review_required")
        checkpoint = instant(row["effective_at"], "effective_at")
        logical_target = (row["case_id"], row["system"], row["entitlement"], checkpoint)
        if logical_target in logical_targets:
            raise InputError("duplicate case/system/entitlement/checkpoint target")
        logical_targets.add(logical_target)
        identity = (row["group"], row["scenario"], row["role"])
        if row["case_id"] in cases and cases[row["case_id"]] != identity:
            raise InputError("case_id: inconsistent group, scenario or role")
        cases[row["case_id"]] = identity
        ids[row["target_id"]] = row
    seen = set()
    for row in packet["evidence"]:
        keys(row, EVIDENCE, "evidence")
        for name in EVIDENCE:
            text(row[name], f"evidence.{name}", allow_empty=(name == "note"))
        if row["evidence_id"] in seen:
            raise InputError(f"duplicate evidence_id: {row['evidence_id']}")
        seen.add(row["evidence_id"])
        if row["target_id"] not in ids:
            raise InputError(f"evidence: unresolved target {row['target_id']}")
        if row["kind"] not in KINDS:
            raise InputError("evidence: unknown kind")
        expected = STATES if row["kind"] in ("APPLIED", "VERIFIED") else ("N/A",)
        if row["state"] not in expected:
            raise InputError(f"evidence {row['evidence_id']}: invalid state for kind")
        instant(row["observed_at"], "observed_at")
    return packet


def loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise InputError(f"non-JSON constant: {value}")

    try:
        return validate(json.loads(raw, object_pairs_hook=pairs, parse_constant=constant))
    except (json.JSONDecodeError, RecursionError, UnicodeError) as exc:
        raise InputError(f"invalid JSON: {exc}") from exc


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def assess(packet):
    """Return a snapshot at the supplied as_of, not a live-account certification."""
    validate(packet)
    as_of = instant(packet["as_of"], "as_of")
    by_target = {t["target_id"]: [] for t in packet["targets"]}
    for evidence in packet["evidence"]:
        by_target[evidence["target_id"]].append(evidence)
    rows = []
    for target in sorted(packet["targets"], key=lambda r: r["target_id"]):
        events = sorted(by_target[target["target_id"]], key=lambda e: (instant(e["observed_at"], "observed_at"), e["evidence_id"]))
        usable = [e for e in events if instant(e["observed_at"], "observed_at") <= as_of]
        future = [e["evidence_id"] for e in events if instant(e["observed_at"], "observed_at") > as_of]
        effective = instant(target["effective_at"], "effective_at")
        kind_rows = {kind: [e for e in usable if e["kind"] == kind] for kind in KINDS}
        latest = {kind: values[-1] if values else None for kind, values in kind_rows.items()}
        applied, verified = latest["APPLIED"], latest["VERIFIED"]
        findings, questions = [], []
        tied_conflict = False
        for kind in ("APPLIED", "VERIFIED"):
            last = latest[kind]
            if last:
                timestamp = instant(last["observed_at"], "observed_at")
                states = {e["state"] for e in kind_rows[kind] if instant(e["observed_at"], "observed_at") == timestamp}
                if len(states) > 1:
                    tied_conflict = True
        observed = [e for e in usable if e["kind"] in ("APPLIED", "VERIFIED")]
        # A same-time disagreement across change and verification is also unresolved.
        newest = observed[-1] if observed else None
        if newest:
            newest_at = instant(newest["observed_at"], "observed_at")
            tied_conflict |= len({e["state"] for e in observed if instant(e["observed_at"], "observed_at") == newest_at}) > 1
        fresh_verification = bool(verified and instant(verified["observed_at"], "observed_at") >= effective and (not applied or instant(verified["observed_at"], "observed_at") >= instant(applied["observed_at"], "observed_at")))
        if effective > as_of:
            status = "NOT_DUE"
        elif tied_conflict:
            status = "CONFLICTING"
        elif newest and newest["state"] != target["desired_state"]:
            status = "CONTRADICTED"
        elif fresh_verification:
            status = "VERIFIED"
        elif applied:
            status = "APPLIED_UNVERIFIED"
        elif latest["APPROVED"]:
            status = "APPROVED_ONLY"
        elif latest["REQUESTED"]:
            status = "REQUESTED_ONLY"
        else:
            status = "UNKNOWN"
        required = ["REQUESTED", "APPROVED", "APPLIED", "VERIFIED"]
        if target["review_required"]:
            required.append("REVIEWED")
        if target["scenario"] == "EMERGENCY":
            required.append("EMERGENCY_REVIEWED")
        missing = [kind for kind in required if latest[kind] is None]
        if missing:
            findings.append("MISSING_" + ",".join(missing))
            questions.append("Supply target-specific records for: " + ", ".join(missing) + ".")
        ordered = all(latest[kind] for kind in required[:4])
        if ordered:
            times = [instant(latest[kind]["observed_at"], "observed_at") for kind in required[:4]]
            ordered = times == sorted(times)
            if not ordered:
                findings.append("CHRONOLOGY_GAP")
                questions.append("Explain request/approval/change/verification ordering; do not discard the out-of-order record.")
        if applied and applied["state"] != target["desired_state"]:
            findings.append("CHANGE_DOES_NOT_MATCH_TARGET")
            questions.append("Supply the change record for the intended entitlement state, or revise the stated target.")
        if status in ("CONTRADICTED", "CONFLICTING"):
            findings.append(status)
            questions.append("Reconcile the observed state with the intended change using a new system observation; retain both accounts.")
        if verified and not fresh_verification:
            findings.append("VERIFICATION_PREDATES_CHANGE_OR_CHECKPOINT")
            questions.append("Obtain verification after the latest change and the effective checkpoint.")
        for kind in required[4:]:
            if latest[kind] and instant(latest[kind]["observed_at"], "observed_at") < effective:
                findings.append(kind + "_PREDATES_CHECKPOINT")
                questions.append("Supply a " + kind.lower() + " record covering this role change, not an earlier review.")
        if future:
            findings.append("FUTURE_EVIDENCE_EXCLUDED")
            questions.append("Check timestamps of future-dated records; they are excluded from this snapshot.")
        blocking = [finding for finding in findings if finding != "FUTURE_EVIDENCE_EXCLUDED"]
        complete = bool(status == "VERIFIED" and ordered and not missing and not blocking)
        row = dict(target)
        row.update(status=status, chain_complete=complete, evidence_ids=[e["evidence_id"] for e in usable], future_evidence_ids=future,
                   policy_ids=[e["evidence_id"] for e in kind_rows["POLICY"]], observed_state=newest["state"] if newest else "UNKNOWN",
                   findings=findings, follow_up=questions, source_refs=list(dict.fromkeys(e["source_ref"] for e in usable)))
        rows.append(row)
    cases = []
    for case_id in sorted({r["case_id"] for r in rows}):
        members = [r for r in rows if r["case_id"] == case_id]
        complete = sum(r["chain_complete"] for r in members)
        cases.append({"case_id": case_id, "declared_targets": len(members), "complete_targets": complete,
                      "status": "ALL_DECLARED_CHAINS_EVIDENCED" if complete == len(members) else "FOLLOW_UP_REQUIRED",
                      "unresolved_target_ids": [r["target_id"] for r in members if not r["chain_complete"]]})
    return {"schema_version": 1, "provenance": packet["provenance"], "as_of": packet["as_of"],
            "scope_limit": "Only declared targets and supplied records; no live account checks, policy compliance, individual rating or completeness claim for the system estate.",
            "rows": rows, "cases": cases}


def csv_escape(value):
    value = str(value)
    return "'" + value if value and (value[0] in ESCAPE or value[0].isspace()) else value


def csv_unescape(value):
    return value[1:] if len(value) > 1 and value[0] == "'" and (value[1] in ESCAPE or value[1].isspace()) else value


def export_csv(packet):
    validate(packet)
    outputs = []
    for key, fields in (("targets", TARGET), ("evidence", EVIDENCE)):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=(*META, *fields), lineterminator="\n")
        writer.writeheader()
        for row in packet[key]:
            values = {**{name: packet[name] for name in META}, **row}
            if "review_required" in values:
                values["review_required"] = "true" if values["review_required"] else "false"
            writer.writerow({k: csv_escape(v) for k, v in values.items()})
        outputs.append(stream.getvalue())
    return tuple(outputs)


def import_csv(targets_text, evidence_text):
    packet = {"targets": [], "evidence": []}
    meta = None
    for raw, key, fields in ((targets_text, "targets", TARGET), (evidence_text, "evidence", EVIDENCE)):
        reader = csv.reader(io.StringIO(raw, newline=""), strict=True)
        try:
            if next(reader, None) != [*META, *fields]:
                raise InputError(f"{key}: exact CSV header required")
            for line, values in enumerate(reader, 2):
                if len(values) != len(META) + len(fields):
                    raise InputError(f"{key}:{line}: wrong number of cells")
                row = dict(zip((*META, *fields), map(csv_unescape, values)))
                incoming = {name: row.pop(name) for name in META}
                if incoming["schema_version"] != "1":
                    raise InputError("CSV schema_version must be 1")
                incoming["schema_version"] = 1
                if meta is not None and meta != incoming:
                    raise InputError(f"{key}:{line}: mixed snapshot metadata")
                meta = incoming
                if key == "targets":
                    if row["review_required"] not in ("true", "false"):
                        raise InputError("review_required: expected true or false")
                    row["review_required"] = row["review_required"] == "true"
                packet[key].append(row)
        except csv.Error as exc:
            raise InputError(f"invalid CSV: {exc}") from exc
    if meta is None:
        raise InputError("CSV contains no targets")
    packet.update(meta)
    return validate(packet)


def md(value):
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;").replace("\r", " ").replace("\n", "<br>")


def render(report):
    lines = ["# Human-access lifecycle evidence review", "", report["provenance"], "", "Snapshot: " + report["as_of"], "", report["scope_limit"], "",
             "A verified system state and a complete lifecycle record are different results. Policy documents never establish application or verification.", "",
             "| Case | Declared targets | Complete chains | Disposition |", "|---|---:|---:|---|"]
    for case in report["cases"]:
        lines.append(f"| {md(case['case_id'])} | {case['declared_targets']} | {case['complete_targets']} | {case['status']} |")
    lines += ["", "## Editable review matrix", "", "| Target / case | System / entitlement | Desired | Latest observed | Implementation evidence | Complete chain |", "|---|---|---|---|---|---|"]
    for row in report["rows"]:
        lines.append("| " + " | ".join(md(v) for v in (row['target_id'] + ' / ' + row['case_id'], row['system'] + ' / ' + row['entitlement'], row['desired_state'], row['observed_state'], row['status'], 'YES' if row['chain_complete'] else 'NO')) + " |")
    for row in report["rows"]:
        lines += ["", "### " + md(row["target_id"]), "", "Evidence: " + (", ".join(row["evidence_ids"]) or "NONE SUPPLIED"),
                  "", "Source locators: " + ("; ".join(md(s) for s in row["source_refs"]) or "UNKNOWN"),
                  "", "Findings: " + ("; ".join(row["findings"]) or "No gap detected in the declared chain.")]
        lines += ["", "Follow-up: " + " ".join(row["follow_up"])] if row["follow_up"] else []
        if row["future_evidence_ids"]:
            lines += ["", "Excluded future evidence: " + ", ".join(row["future_evidence_ids"])]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="create a new review folder")
    inspect.add_argument("packet", type=Path)
    inspect.add_argument("--out", type=Path, required=True)
    restore = commands.add_parser("import", help="reconstruct JSON from the two editable CSVs")
    restore.add_argument("targets", type=Path)
    restore.add_argument("evidence", type=Path)
    restore.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            packet = import_csv(args.targets.read_text(encoding="utf-8"), args.evidence.read_text(encoding="utf-8"))
            with args.out.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(canonical(packet))
            print("IMPORTED snapshot; no access changed")
        else:
            packet = loads(args.packet.read_text(encoding="utf-8"))
            report = assess(packet)
            targets, evidence = export_csv(packet)
            args.out.mkdir()  # New directory only. Existing data is never deleted.
            for name, contents in (("targets.csv", targets), ("evidence.csv", evidence), ("report.json", canonical(report)), ("report.md", render(report))):
                with (args.out / name).open("x", encoding="utf-8", newline="") as handle:
                    handle.write(contents)
            print(f"REVIEW_WRITTEN declared_targets={len(report['rows'])} complete_chains={sum(r['chain_complete'] for r in report['rows'])}; no access changed")
        return 0
    except (InputError, OSError, UnicodeError) as exc:
        parser.exit(2, f"INPUT_OR_OUTPUT_ERROR: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
