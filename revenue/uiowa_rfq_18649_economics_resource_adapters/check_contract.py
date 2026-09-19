#!/usr/bin/env python3
"""Contract conformance checker for the UIOWA-105 adapters.

Why this exists. The 105 receipt promised that when the resource-estimation
kit (UIOWA-086) and the AI benefit / operating-cost model (UIOWA-078) land,
pointing the adapters at their real output would say immediately whether the
declared contract held. Until this file existed, that promise rested on tests
that only exercised fixtures written by the same hand as the adapter -- which
proves the adapter agrees with its author's guess, not that the contract is
checkable by somebody else.

So: any component author can run

    python3 check_contract.py --resource  their_output.json
    python3 check_contract.py --economics their_output.json
    python3 check_contract.py --portfolio their_output.json
    python3 check_contract.py --explain resource

and get a field-by-field verdict with exact JSON paths, plus -- and this is the
part a plain schema validator does not give them -- what their file would
actually DO once adapted: which of the five ledgers populate, which land as
UNKNOWN, and which records end up unmapped.

Two deliberate stances:

  * EXTRA FIELDS ARE CARRIED, NOT REFUSED. Rejecting a key somebody took the
    trouble to emit is hostile, and UIOWA-102's own completion criterion is
    that unsupported fields survive as explicit extensions rather than
    disappearing. Unknown keys are reported as carried extensions.

  * IT FAILS ON WHAT BREAKS A JOIN, NOT ON STYLE. A partial range, an estimate
    written in words, a boolean where a number belongs, a cash figure with no
    declared currency, a duplicate identifier, inverted bounds. Each names the
    record and the path so it is fixable without reading the adapter source.

Exit status: 0 conformant (warnings allowed), 1 non-conformant, 2 unusable
input. Python 3 standard library only. Deterministic.
"""

import argparse
import json
import os
import sys

import adapters
from ledgers import (
    ALL_LEDGERS, ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH,
    RECURRING_CASH, RELEASED_CAPACITY, UNKNOWN, AdapterError,
)

HERE = os.path.dirname(os.path.abspath(__file__))

# What each contract promises. Kept as data so --explain and the checker can
# never drift from one another.
CONTRACTS = {
    "resource": {
        "schema_version": adapters.RESOURCE_SCHEMA,
        "component": "resource-estimation kit (UIOWA-086)",
        "collection": "work_items",
        "identifier": "work_item_id",
        "required_doc_keys": ["schema_version", "work_items"],
        "required_record_keys": ["work_item_id"],
        "range_fields": ["one_time_effort_hours", "recurring_effort_fte_per_year"],
        "link_field": "recommendation_ids",
        "known_record_keys": [
            "work_item_id", "label", "recommendation_ids",
            "one_time_effort_hours", "recurring_effort_fte_per_year",
            "specialist_roles", "notes",
        ],
        "fills": [ONE_TIME_EFFORT, RECURRING_EFFORT],
        "notes": [
            "Cash fields are NOT read from this component even if present; "
            "cash belongs to the economics contract. Two components claiming "
            "the same money is a double count.",
            "specialist_roles[].one_time_hours is read as a range in the "
            "one-time effort ledger and carried per role.",
        ],
    },
    "economics": {
        "schema_version": adapters.ECONOMICS_SCHEMA,
        "component": "AI benefit and operating-cost model (UIOWA-078)",
        "collection": "entries",
        "identifier": "entry_id",
        "required_doc_keys": ["schema_version", "entries"],
        "also_required": ["currency"],
        "required_record_keys": ["entry_id"],
        "range_fields": ["one_time_cash", "recurring_cash_per_year",
                         "released_capacity_hours_per_year"],
        "link_field": "recommendation_ids",
        "known_record_keys": [
            "entry_id", "work_item_id", "label", "recommendation_ids",
            "one_time_cash", "recurring_cash_per_year",
            "released_capacity_hours_per_year", "assumptions", "notes",
        ],
        "fills": [ONE_TIME_CASH, RECURRING_CASH, RELEASED_CAPACITY],
        "notes": [
            "Effort fields are NOT read from this component even if present.",
            "`currency` is required at document level. A cash figure without "
            "its unit is not a fact that can be carried into a report table.",
            "An entry MAY name a work_item_id the resource kit also reports. "
            "That is the join, not a conflict: the two fill different ledgers "
            "of the same work item and are merged rather than duplicated.",
        ],
    },
    "portfolio": {
        "schema_version": adapters.PORTFOLIO_SCHEMA,
        "component": "AI opportunity and value portfolio (UIOWA-072)",
        "collection": "candidates",
        "identifier": "id",
        "required_doc_keys": ["schema_version", "candidates"],
        "required_record_keys": ["id"],
        "range_fields": ["one_time_implementation", "recurring_maintenance",
                         "benefit_hours_per_year"],
        "link_field": None,
        "known_record_keys": [],   # the portfolio carries many fields; all carried
        "fills": [ONE_TIME_EFFORT, RECURRING_EFFORT, RELEASED_CAPACITY],
        "notes": [
            "Candidate ids are joined to recommendations through an explicit "
            "crosswalk file, never inferred from titles. A candidate with no "
            "crosswalk entry is reported unmapped, not dropped.",
            "This component's range objects use low/likely/high directly, or "
            "the literal string UNKNOWN.",
        ],
    },
}

# Range forms the adapters genuinely accept, stated once for --explain.
ACCEPTED_RANGE_FORMS = [
    '{"low": n, "likely": n, "high": n}            canonical',
    '{"low": n, "mid": n, "high": n}               "mid" is the same slot',
    '{"value": n}  or a bare number                point estimate, widened',
    '{"basis": "why there is no number"}           UNKNOWN, with the reason kept',
    'null / "UNKNOWN" / "n/a" / "TBD" / "?" / ""   UNKNOWN',
]


# Fields that legitimately exist, but in a different component's contract.
_OTHER_CONTRACT_FIELDS = {
    "one_time_cash": "economics",
    "recurring_cash_per_year": "economics",
    "released_capacity_hours_per_year": "economics",
    "one_time_effort_hours": "resource",
    "recurring_effort_fte_per_year": "resource",
    "specialist_roles": "resource",
}


class Finding(object):
    __slots__ = ("level", "path", "message")

    def __init__(self, level, path, message):
        self.level, self.path, self.message = level, path, message

    def as_dict(self):
        return {"level": self.level, "path": self.path, "message": self.message}


def _probe_range(raw, path, out, record_id, field):
    """Report how the adapters would read one value. Never raises."""
    try:
        from ledgers import read_amount
        result = read_amount(raw, ONE_TIME_EFFORT, "probe", record_id, field)
    except AdapterError as exc:
        # Pass the adapter's own words through intact. An earlier version split
        # on ": " to strip a prefix and truncated the partial-range message
        # into "high, low). A missing bound..." -- worse than no cleanup.
        out.append(Finding("FAIL", path, str(exc)))
        return "FAIL"
    if result == UNKNOWN:
        return UNKNOWN
    if isinstance(raw, (int, float)) or (isinstance(raw, dict) and "low" not in raw):
        out.append(Finding(
            "WARN", path,
            "point estimate: it will be carried as a zero-width range. The "
            "report shows a single number where a reader expects a range."))
    return "OK"


def check(doc, kind):
    """Return (findings, summary). Pure; writes nothing."""
    spec = CONTRACTS[kind]
    out = []
    summary = {
        "contract": kind, "component": spec["component"],
        "records": 0, "records_with_links": 0,
        "ledgers_populated": {}, "ledgers_unknown": {},
        "unmapped_records": [], "carried_extensions": [],
        "duplicate_identifiers": [],
    }
    for ledger in spec["fills"]:
        summary["ledgers_populated"][ledger] = 0
        summary["ledgers_unknown"][ledger] = 0

    if not isinstance(doc, dict):
        out.append(Finding("FAIL", "$", "top level is %s, expected an object"
                           % type(doc).__name__))
        return out, summary

    for key in spec["required_doc_keys"]:
        if key not in doc:
            out.append(Finding("FAIL", "$.%s" % key, "required key is absent"))
    if doc.get("schema_version") not in (None, spec["schema_version"]):
        out.append(Finding(
            "FAIL", "$.schema_version",
            "is %r; this contract is %r. If your component has moved on, say "
            "so and the adapter moves with it -- it should not be guessed."
            % (doc.get("schema_version"), spec["schema_version"])))
    if kind == "economics" and not doc.get("currency"):
        out.append(Finding(
            "FAIL", "$.currency",
            "absent. A cash figure with no declared unit cannot be carried "
            "into a report table."))

    records = doc.get(spec["collection"])
    if records is None:
        out.append(Finding("FAIL", "$.%s" % spec["collection"],
                           "required collection is absent"))
        return out, summary
    if not isinstance(records, list):
        out.append(Finding("FAIL", "$.%s" % spec["collection"],
                           "must be a list, got %s" % type(records).__name__))
        return out, summary
    if not records:
        out.append(Finding("WARN", "$.%s" % spec["collection"],
                           "is empty; nothing would be joined"))

    seen = set()
    extensions = set()
    for index, record in enumerate(records):
        base = "$.%s[%d]" % (spec["collection"], index)
        if not isinstance(record, dict):
            out.append(Finding("FAIL", base, "record is %s, expected an object"
                               % type(record).__name__))
            continue
        summary["records"] += 1
        rid = record.get(spec["identifier"])
        for key in spec["required_record_keys"]:
            if not record.get(key):
                out.append(Finding("FAIL", "%s.%s" % (base, key),
                                   "required identifier is absent or empty"))
        if rid:
            if rid in seen:
                out.append(Finding("FAIL", "%s.%s" % (base, spec["identifier"]),
                                   "duplicate identifier %r; records would "
                                   "silently merge" % rid))
                summary["duplicate_identifiers"].append(rid)
            seen.add(rid)

        for field, ledger in zip(spec["range_fields"], spec["fills"]):
            path = "%s.%s" % (base, field)
            if field not in record:
                out.append(Finding(
                    "WARN", path,
                    "absent: the %s ledger will read UNKNOWN for this record. "
                    "That is held open, never counted as zero." % ledger))
                summary["ledgers_unknown"][ledger] += 1
                continue
            verdict = _probe_range(record[field], path, out,
                                   str(rid or base), field)
            if verdict == "OK":
                summary["ledgers_populated"][ledger] += 1
            elif verdict == UNKNOWN:
                summary["ledgers_unknown"][ledger] += 1

        if spec["link_field"]:
            links = record.get(spec["link_field"])
            if links is None or links == []:
                summary["unmapped_records"].append(rid or base)
                out.append(Finding(
                    "WARN", "%s.%s" % (base, spec["link_field"]),
                    "no recommendation is named: this record is carried as an "
                    "unmapped work item rather than dropped, but it will not "
                    "appear in any recommendation's resourcing row."))
            elif not isinstance(links, list):
                out.append(Finding("FAIL", "%s.%s" % (base, spec["link_field"]),
                                   "must be a list of recommendation ids"))
            else:
                summary["records_with_links"] += 1

        if spec["known_record_keys"]:
            for key in sorted(record):
                if key not in spec["known_record_keys"]:
                    extensions.add(key)

    for key in sorted(extensions):
        other = _OTHER_CONTRACT_FIELDS.get(key)
        message = ("not part of the contract; carried as an extension, not "
                   "dropped and not an error.")
        if other:
            message = ("belongs to the %s contract and is deliberately NOT "
                       "read here -- two components claiming the same quantity "
                       "is a double count. Carried as an extension." % other)
        out.append(Finding("INFO", "$.%s[].%s"
                           % (spec["collection"], key), message))
    summary["carried_extensions"] = sorted(extensions)

    # Final proof: if it is conformant, the real adapter must actually run it.
    if not any(f.level == "FAIL" for f in out):
        try:
            if kind == "resource":
                adapters.adapt_resource_estimates(doc)
            elif kind == "economics":
                adapters.adapt_economics(doc)
            else:
                adapters.adapt_opportunity_portfolio(doc, {})
        except AdapterError as exc:
            out.append(Finding(
                "FAIL", "$",
                "the checker found no problem but the real adapter refused it: "
                "%s. That is a checker bug -- please report it." % exc))
    return out, summary


def render(findings, summary, path):
    lines = []
    a = lines.append
    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]
    infos = [f for f in findings if f.level == "INFO"]

    a("contract : %s" % summary["contract"])
    a("component: %s" % summary["component"])
    a("file     : %s" % path)
    a("verdict  : %s" % ("NON-CONFORMANT" if fails else "CONFORMANT"))
    a("")
    for group, label in ((fails, "FAIL"), (warns, "WARN"), (infos, "INFO")):
        for f in group:
            a("%-5s %s" % (label, f.path))
            a("      %s" % f.message)
    if findings:
        a("")
    a("What this file would do once adapted")
    a("  records read                : %d" % summary["records"])
    if summary["unmapped_records"]:
        a("  carried but unmapped        : %s"
          % ", ".join(str(r) for r in summary["unmapped_records"]))
    for ledger in sorted(summary["ledgers_populated"]):
        a("  %-42s populated %d, UNKNOWN %d"
          % (ledger, summary["ledgers_populated"][ledger],
             summary["ledgers_unknown"][ledger]))
    if summary["carried_extensions"]:
        a("  fields carried as extensions: %s"
          % ", ".join(summary["carried_extensions"]))
    a("")
    a("%d fail, %d warn, %d info" % (len(fails), len(warns), len(infos)))
    return "\n".join(lines)


def explain(kind):
    spec = CONTRACTS[kind]
    lines = ["Contract: %s" % kind, "Component: %s" % spec["component"],
             "schema_version must be: %s" % spec["schema_version"], ""]
    lines.append("Document keys required: %s" % ", ".join(spec["required_doc_keys"]))
    lines.append("Collection: $.%s[]   identified by %r"
                 % (spec["collection"], spec["identifier"]))
    lines.append("")
    lines.append("Range fields read, and the ledger each fills:")
    for field, ledger in zip(spec["range_fields"], spec["fills"]):
        lines.append("  %-38s -> %s" % (field, ledger))
    lines.append("")
    lines.append("Accepted range forms:")
    for form in ACCEPTED_RANGE_FORMS:
        lines.append("  " + form)
    lines.append("")
    lines.append("Notes:")
    for note in spec["notes"]:
        lines.append("  - " + note)
    lines.append("")
    lines.append("Any other field is carried as an extension, not refused.")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Check a component file against the UIOWA-105 adapter contracts")
    g = p.add_mutually_exclusive_group(required=True)
    for kind in sorted(CONTRACTS):
        g.add_argument("--%s" % kind, dest="kind", action="store_const",
                       const=kind, help="check against the %s contract" % kind)
    g.add_argument("--explain", choices=sorted(CONTRACTS),
                   help="print the contract and exit")
    p.add_argument("file", nargs="?", help="the candidate JSON file")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)

    if args.explain:
        print(explain(args.explain))
        return 0
    if not args.file:
        sys.stderr.write("a file is required unless --explain is used\n")
        return 2
    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        sys.stderr.write("UNUSABLE: %s not found\n" % args.file)
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write("UNUSABLE: %s is not valid JSON: %s\n" % (args.file, exc))
        return 2

    findings, summary = check(doc, args.kind)
    if args.json:
        print(json.dumps({"findings": [f.as_dict() for f in findings],
                          "summary": summary,
                          "conformant": not any(f.level == "FAIL" for f in findings)},
                         indent=2, sort_keys=True))
    else:
        print(render(findings, summary, args.file))
    return 1 if any(f.level == "FAIL" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
