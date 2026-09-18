"""CLI, diagnostics and reproducible review bundles for retained camt XML.

Run: python workbench.py build --out NEW_DIRECTORY statement.xml [...]
     python workbench.py verify EXISTING_DIRECTORY
Exit codes: 0 extracted / verified, 1 review findings, 2 rejected source or error.
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import os
import re
import stat
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

if __package__:
    from .camt_parser import (VERSION, MAX_SOURCE_BYTES, InputError, canonical, digest,
                         extract, finding, total, difference, signed, date_order)
else:
    from camt_parser import (VERSION, MAX_SOURCE_BYTES, InputError, canonical, digest,
                        extract, finding, total, difference, signed, date_order)

MAX_SOURCES = 32
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
DATA_FILES = {"normalized.json", "entries.csv", "details.csv", "findings.csv", "review.html"}
PLACEHOLDER_REFERENCES = {"NOTPROVIDED", "NONREF", "NOREF", "NOTAVAILABLE"}
LIMITATION = ("Retained-source extraction and in-file arithmetic only. Not bank-source "
              "authentication, complete account reconciliation, XSD certification, "
              "accounting advice, or ledger-posting approval. No network or bank writes.")


FINDING_GUIDE = {
    "MULTIPAGE_NOT_ASSEMBLED": ("This source is part of a multi-page delivery.", "Obtain a complete unpaginated export or implement the bank's reviewed page-assembly profile."),
    "COPY_OR_DUPLICATE_MARKER": ("The statement is marked as a copy or duplicate.", "Compare the original statement and import history; do not post this copy automatically."),
    "ACCOUNT_SERVICER_UNSPECIFIED": ("No account-servicer identity was supplied.", "Confirm the issuing bank before matching account identifiers across files."),
    "NON_BOOK_ENTRY": ("An entry is not explicitly standard-code BOOK.", "Confirm the bank's status mapping. This entry is retained but excluded from booked totals."),
    "MIXED_ENTRY_CURRENCIES": ("Entry amounts span currencies.", "Review each currency separately; no FX conversion or mixed-currency balance check is attempted."),
    "ACCOUNT_CURRENCY_DIFFERENCE": ("Entry currency differs from the reported account currency.", "Resolve the bank export's currency semantics before reconciliation."),
    "BALANCE_ACCOUNT_CURRENCY_DIFFERENCE": ("Balance currency differs from account currency.", "Obtain a bank-specific explanation; do not combine the amounts."),
    "BOOKING_DATE_NOT_SUPPLIED": ("The bank did not supply a booking date for this entry.", "Retain the missing date; do not substitute the value date."),
    "BATCH_DETAIL_COUNT_DIFFERENCE": ("Declared batch count differs from included transaction details.", "Determine whether the bank intentionally supplied partial detail. The entry amount is retained once."),
    "REPEATED_BANK_REFERENCE_RETAINED": ("A bank reference repeats within the statement.", "Compare the original entries. Repeated references are not automatically duplicate cash movements."),
    "REPEATED_STATEMENT_IDENTITY_RETAINED": ("The reported account identifier and statement ID repeat.", "Compare bank identity, pages and reissues. Both occurrences are retained; do not sum them blindly."),
    "CROSS_STATEMENT_SERVICER_REFERENCE_RETAINED": ("An account-servicer reference repeats across statements for the same reported account ID.", "Check for overlap or a reissue against import history; no entry was silently deleted."),
    "DUPLICATE_SOURCE_COLLAPSED": ("Identical source bytes were supplied under multiple names.", "One copy was parsed and every alias retained. Separately check prior import history."),
    "BOOKED_BALANCE_PAIR_MISSING": ("No usable booked-balance currency pair was supplied.", "Request opening OPBD and closing CLBD booked balances; available balances are not substitutes."),
    "BOOKED_BALANCE_PAIR_MISSING_OR_AMBIGUOUS": ("There is not exactly one OPBD and one CLBD balance in this currency.", "Resolve the missing or multiple booked balances; no closing-balance alias is guessed."),
    "BALANCE_SUBTYPE_REQUIRES_PROFILE": ("A booked balance carries a subtype the generic profile does not interpret.", "Confirm subtype semantics using the bank's facility-specific documentation."),
    "BALANCE_DATE_ORDER_UNCHECKABLE_OR_REVERSED": ("Opening and closing balance dates cannot be ordered consistently.", "Check date types, time zones and the statement period with the provider."),
    "PERIOD_REVERSED": ("The statement period ends before it starts.", "Obtain a corrected bank export or explicit provider clarification."),
    "PERIOD_ORDER_UNCHECKABLE": ("Period timestamps have incompatible timezone information.", "Confirm the timezone instead of inventing one."),
    "BALANCE_ARITHMETIC_MISMATCH": ("Opening booked balance plus booked entries differs from closing booked balance.", "Review the displayed difference and source entries; do not insert a balancing transaction."),
    "SUMMARY_MISMATCH": ("A reported entry count or sum differs from extracted entries.", "Compare the reported-summary checks in normalized.json with the retained source."),
    "SUMMARY_NOT_CHECKED": ("The source does not support an unambiguous summary comparison.", "Resolve page, status or currency findings first."),
    "SUMMARY_NET_SIGN_MISSING": ("The reported net amount has no credit/debit indicator.", "Request the missing direction rather than infer its sign."),
    "SUPPLEMENTARY_DATA_IN_SOURCE_ONLY": ("Supplementary data is retained in XML but not interpreted.", "Review the retained XML and add a bank-specific projection when needed."),
}


def inspect_statement(statement: dict[str, Any]) -> list[dict[str, str]]:
    sid, path = statement["id"], statement["path"]
    findings: list[dict[str, str]] = []
    blockers: list[str] = []

    def note(code: str, where: str = path, block: bool = False,
             severity: str = "review") -> None:
        findings.append(finding(code, where, sid, severity))
        if block and code not in blockers:
            blockers.append(code)

    page = statement["pagination"]
    if page and (page["page"] != 1 or not page["last"]):
        note("MULTIPAGE_NOT_ASSEMBLED", block=True)
    if statement["copy_duplicate"]:
        note("COPY_OR_DUPLICATE_MARKER")
    acct = statement["account"]
    if not acct["servicer_fields"]:
        note("ACCOUNT_SERVICER_UNSPECIFIED")
    period = statement["period"]
    if period:
        ordered = date_order({"kind": "DtTm", "value": period["from"]},
                             {"kind": "DtTm", "value": period["to"]})
        if ordered is not True:
            note("PERIOD_ORDER_UNCHECKABLE" if ordered is None else "PERIOD_REVERSED", block=True)

    entries = statement["entries"]
    currencies = sorted({row["currency"] for row in entries})
    if len(currencies) > 1:
        note("MIXED_ENTRY_CURRENCIES", block=True)
    reference_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in entries:
        if not row["booked"]:
            note("NON_BOOK_ENTRY", row["path"], block=True)
        if acct["currency"] and row["currency"] != acct["currency"]:
            note("ACCOUNT_CURRENCY_DIFFERENCE", row["path"], block=True)
        if row["booking_date"] is None:
            note("BOOKING_DATE_NOT_SUPPLIED", row["path"], severity="info")
        for ref in ("entry_reference", "servicer_reference"):
            value = row[ref]
            if value and value.upper() not in PLACEHOLDER_REFERENCES:
                reference_groups[(ref, value)].append(row)
        for batch in row["batches"]:
            count = batch["declared_count"]
            if count is not None and count != batch["observed_detail_count"]:
                note("BATCH_DETAIL_COUNT_DIFFERENCE", batch["path"])
    for rows in reference_groups.values():
        if len(rows) > 1:
            for row in rows:
                note("REPEATED_BANK_REFERENCE_RETAINED", row["path"])

    statement["observed_booked_totals"] = [
        {"currency": ccy,
         "entry_count": sum(row["booked"] and row["currency"] == ccy for row in entries),
         "signed_amount": total([row["signed_amount"] for row in entries
                                  if row["booked"] and row["currency"] == ccy])}
        for ccy in currencies]

    checks = []
    relevant = [b for b in statement["balances"]
                if b["type"]["kind"] == "Cd" and b["type"]["value"] in {"OPBD", "CLBD"}]
    balance_currencies = sorted(set(currencies) | {b["currency"] for b in relevant})
    if not balance_currencies:
        note("BOOKED_BALANCE_PAIR_MISSING")
    for ccy in balance_currencies:
        opening = [b for b in relevant if b["type"]["value"] == "OPBD" and b["currency"] == ccy]
        closing = [b for b in relevant if b["type"]["value"] == "CLBD" and b["currency"] == ccy]
        reasons = list(blockers)
        if len(opening) != 1 or len(closing) != 1:
            reasons.append("BOOKED_BALANCE_PAIR_MISSING_OR_AMBIGUOUS")
        elif opening[0]["subtype"] or closing[0]["subtype"]:
            reasons.append("BALANCE_SUBTYPE_REQUIRES_PROFILE")
        elif date_order(opening[0]["date"], closing[0]["date"]) is not True:
            reasons.append("BALANCE_DATE_ORDER_UNCHECKABLE_OR_REVERSED")
        if acct["currency"] and ccy != acct["currency"]:
            reasons.append("BALANCE_ACCOUNT_CURRENCY_DIFFERENCE")
        net = total([e["signed_amount"] for e in entries if e["booked"] and e["currency"] == ccy])
        check: dict[str, Any] = {"currency": ccy, "result": "NOT_CHECKED", "reasons": reasons,
                                  "booked_entries_net": net, "opening": None,
                                  "closing": None, "expected_closing": None, "difference": None}
        if not reasons:
            check["opening"], check["closing"] = opening[0]["signed_amount"], closing[0]["signed_amount"]
            check["expected_closing"] = total([check["opening"], net])
            check["difference"] = difference(check["closing"], check["expected_closing"])
            check["result"] = "ARITHMETIC_MATCH" if check["difference"] == "0" else "ARITHMETIC_MISMATCH"
            if check["difference"] != "0":
                note("BALANCE_ARITHMETIC_MISMATCH")
        else:
            for reason in reasons:
                if reason not in blockers:
                    note(reason)
        checks.append(check)
    statement["balance_checks"] = checks

    summary_checks = []
    reported = statement["reported_summary"]
    if reported is not None:
        if blockers or len(currencies) != 1:
            note("SUMMARY_NOT_CHECKED")
        else:
            for kind, actual in reported.items():
                filtered = entries if kind == "TtlNtries" else [e for e in entries
                    if e["credit_debit"] == ("CRDT" if kind == "TtlCdtNtries" else "DBIT")]
                expected = {"NbOfNtries": len(filtered), "Sum": total([e["amount"] for e in filtered])}
                for field in ("NbOfNtries", "Sum"):
                    if field in actual:
                        ok = actual[field] == expected[field]
                        summary_checks.append({"group": kind, "field": field,
                                               "reported": actual[field], "computed": expected[field],
                                               "result": "MATCH" if ok else "MISMATCH"})
                        if not ok:
                            note("SUMMARY_MISMATCH")
                if "TtlNetNtryAmt" in actual:
                    if "CdtDbtInd" not in actual:
                        note("SUMMARY_NET_SIGN_MISSING")
                    else:
                        observed = signed(actual["TtlNetNtryAmt"], actual["CdtDbtInd"])
                        net = total([e["signed_amount"] for e in filtered])
                        ok = net == observed
                        summary_checks.append({"group": kind, "field": "signed_net",
                                               "reported": observed, "computed": net,
                                               "result": "MATCH" if ok else "MISMATCH"})
                        if not ok:
                            note("SUMMARY_MISMATCH")
    statement["summary_checks"] = summary_checks
    # Different checks may identify the same cause; retain one instance per scope/path.
    return list({tuple(f.values()): f for f in findings}.values())


def compile_sources(inputs: Mapping[str, bytes]) -> dict[str, Any]:
    if not isinstance(inputs, Mapping) or not 1 <= len(inputs) <= MAX_SOURCES:
        raise InputError("SOURCE_COUNT")
    grouped: dict[str, dict[str, Any]] = {}
    size = 0
    for name, raw in inputs.items():
        if type(name) is not str or not 1 <= len(name) <= 255 or any(
                ord(c) < 32 or c in "/\\" for c in name) or name in {".", ".."}:
            raise InputError("SOURCE_ALIAS")
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES:
            raise InputError("SOURCE_SIZE_OR_TYPE")
        size += len(raw)
        if size > MAX_TOTAL_BYTES:
            raise InputError("TOTAL_SOURCE_SIZE")
        sid = digest(raw)
        group = grouped.setdefault(sid, {"raw": raw, "aliases": []})
        group["aliases"].append(name)
    result: dict[str, Any] = {"tool_version": VERSION, "limitation": LIMITATION,
                              "sources": [], "statements": [], "findings": []}
    for sid, group in sorted(grouped.items()):
        aliases = sorted(group["aliases"])
        source: dict[str, Any] = {"sha256": sid, "aliases": aliases, "bytes": len(group["raw"]),
                                   "parse_status": "EXTRACTED", "version": None,
                                   "message_id": None, "created_at": None}
        result["sources"].append(source)
        if len(aliases) > 1:
            result["findings"].append(finding("DUPLICATE_SOURCE_COLLAPSED", "Document", sid))
        try:
            extracted = extract(group["raw"])
        except InputError as exc:
            source["parse_status"] = "REJECTED"
            result["findings"].append(finding(exc.code, exc.path, sid, "error"))
            continue
        for key in ("version", "message_id", "created_at"):
            source[key] = extracted[key]
        if extracted["supplementary_data_present"]:
            result["findings"].append(finding("SUPPLEMENTARY_DATA_IN_SOURCE_ONLY", "Document", sid))
        for stmt in extracted["statements"]:
            result["statements"].append(stmt)
            result["findings"].extend(inspect_statement(stmt))
    identities: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    servicer_refs: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for stmt in result["statements"]:
        # Conservatively flag same reported account ID + statement ID even when
        # optional bank metadata changed. A finding never deletes a record.
        acct = stmt["account"]
        identities[(acct["kind"], acct["value"], stmt["statement_reference"])].append(stmt)
        for row in stmt["entries"]:
            ref = row["servicer_reference"]
            if ref and ref.upper() not in PLACEHOLDER_REFERENCES:
                servicer_refs[(acct["kind"], acct["value"], ref)].append(row)
    for statements in identities.values():
        if len(statements) > 1:
            for stmt in statements:
                result["findings"].append(finding("REPEATED_STATEMENT_IDENTITY_RETAINED", stmt["path"], stmt["id"]))
    for rows in servicer_refs.values():
        if len({row["statement_id"] for row in rows}) > 1:
            for row in rows:
                result["findings"].append(finding("CROSS_STATEMENT_SERVICER_REFERENCE_RETAINED", row["path"], row["statement_id"]))
    result["findings"].sort(key=lambda f: (f["scope"], f["path"], f["code"], f["severity"]))
    for item in result["findings"]:
        explanation, action = FINDING_GUIDE.get(item["code"], (
            "The source was rejected at a critical extraction-profile field.",
            "Inspect the retained source at the stated path and correct the export or add an explicitly reviewed profile; no partial source ledger was accepted."))
        item.update(explanation=explanation, next_action=action)
    result["status"] = ("SOURCE_REJECTED" if any(f["severity"] == "error" for f in result["findings"])
                        else "REVIEW_REQUIRED" if any(f["severity"] == "review" for f in result["findings"])
                        else "EXTRACTED")
    result["counts"] = {"input_aliases": len(inputs), "unique_sources": len(grouped),
                         "statements": len(result["statements"]),
                         "entries": sum(len(s["entries"]) for s in result["statements"]),
                         "details": sum(len(e["details"]) for s in result["statements"] for e in s["entries"])}
    return result


def csv_bytes(fields: list[str], rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for row in rows:
        converted = {}
        for key in fields:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                value = canonical(value).decode("utf-8").strip()
            text = "" if value is None else str(value)
            # Display CSV: prefix every populated cell as text, preserving long
            # IDs/leading zeros and preventing formula interpretation. JSON is
            # the authoritative typed machine interface, not this display CSV.
            if text:
                text = "'" + text
            converted[key] = text
        writer.writerow(converted)
    return output.getvalue().encode("utf-8")


def display(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = canonical(value).decode("utf-8").strip()
    return html.escape("" if value is None else str(value), quote=True)


def table(fields: list[str], rows: list[dict[str, Any]]) -> str:
    return ("<table><thead><tr>" + "".join(f"<th>{display(f)}</th>" for f in fields) +
            "</tr></thead><tbody>" + "".join("<tr>" + "".join(
                f"<td>{display(row.get(f))}</td>" for f in fields) + "</tr>" for row in rows) +
            "</tbody></table>")


def render(report: dict[str, Any]) -> dict[str, bytes]:
    entries, details, balances = [], [], []
    for stmt in report["statements"]:
        for row in stmt["entries"]:
            entries.append({**row, "source_sha256": stmt["source_id"],
                            "account": stmt["account"]["value"],
                            "statement_reference": stmt["statement_reference"]})
            for tx in row["details"]:
                details.append({**tx, "source_sha256": stmt["source_id"]})
        for check in stmt["balance_checks"]:
            balances.append({"statement_reference": stmt["statement_reference"],
                             "account": stmt["account"]["value"], **check})
    entry_fields = ["source_sha256", "statement_id", "id", "path", "account", "statement_reference",
                    "currency", "amount", "signed_amount", "credit_debit", "reversal", "status", "booked",
                    "entry_reference", "servicer_reference", "booking_date", "value_date",
                    "transaction_code", "additional_information", "batches"]
    detail_fields = ["source_sha256", "id", "entry_id", "path", "amounts", "credit_debit",
                     "references", "remittance", "transaction_code", "additional_information", "counts_as_entry"]
    finding_fields = ["severity", "code", "explanation", "next_action", "scope", "path"]
    body = ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            "<title>Bank statement intake review</title><style>"
            "body{font:16px system-ui,sans-serif;line-height:1.5;margin:2rem;max-width:100%}"
            "h1{margin-bottom:.2rem}table{border-collapse:collapse;width:100%;font-size:.85rem}"
            "th,td{border:1px solid;padding:.45rem;text-align:left;vertical-align:top;overflow-wrap:anywhere}"
            "section{margin:2rem 0;overflow:auto}p{max-width:85ch}code{overflow-wrap:anywhere}"
            "</style><h1>Bank statement intake review</h1>"
            f"<p><strong>{display(report['status'])}</strong> · Version {display(VERSION)}</p>"
            f"<p>{display(LIMITATION)}</p><p>Confidential when built from real bank exports. "
            "Entry rows are the cash-entry layer. Transaction details are drill-down only; "
            "do not add them to entry totals. Arithmetic matches do not establish complete "
            "statement delivery or the absence of duplicate/reissued records.</p>"
            f"<p>{display(report['counts'])}</p><section><h2>Findings</h2>" +
            table(finding_fields, report["findings"]) + "</section><section><h2>In-file balance checks</h2>" +
            table(["account", "statement_reference", "currency", "result", "opening", "booked_entries_net",
                   "closing", "expected_closing", "difference", "reasons"], balances) +
            "</section><section><h2>Entry ledger</h2>" +
            table(["account", "statement_reference", "currency", "signed_amount", "booked", "reversal",
                   "booking_date", "entry_reference", "additional_information", "id"], entries) +
            "</section><section><h2>Underlying details — not additional entries</h2>" +
            table(["entry_id", "amounts", "references", "remittance", "additional_information"], details) +
            "</section><section><h2>Retained sources</h2>" +
            table(["aliases", "sha256", "bytes", "version", "parse_status"], report["sources"]) +
            "</section></html>\n")
    return {"normalized.json": canonical(report),
            "entries.csv": csv_bytes(entry_fields, entries),
            "details.csv": csv_bytes(detail_fields, details),
            "findings.csv": csv_bytes(finding_fields, report["findings"]),
            "review.html": body.encode("utf-8")}


def bundle(inputs: Mapping[str, bytes]) -> tuple[dict[str, bytes], dict[str, Any]]:
    report = compile_sources(inputs)
    files = render(report)
    for raw in inputs.values():
        files["sources/" + digest(raw) + ".xml"] = raw
    manifest = {"tool_version": VERSION,
                "sources": [{"sha256": s["sha256"], "aliases": s["aliases"]} for s in report["sources"]],
                "files": {name: {"bytes": len(raw), "sha256": digest(raw)} for name, raw in sorted(files.items())}}
    files["manifest.json"] = canonical(manifest)
    if sum(map(len, files.values())) > MAX_OUTPUT_BYTES:
        raise InputError("OUTPUT_SIZE")
    return files, report


def read_regular(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    if path.is_symlink():
        raise InputError("SYMLINK_NOT_SUPPORTED")
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise InputError("REGULAR_FILE_SIZE")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            raise InputError("REGULAR_FILE_SIZE")
        return raw
    finally:
        os.close(fd)


def write_bundle(inputs: Mapping[str, bytes], output: Path) -> dict[str, Any]:
    files, report = bundle(inputs)
    # Caller owns the parent directory. Refuse an existing target, including an
    # empty directory or symlink; never update an earlier report in place.
    os.mkdir(output, 0o700)
    os.mkdir(output / "sources", 0o700)
    for name in sorted(files, key=lambda n: (n == "manifest.json", n)):
        with (output / name).open("xb") as handle:
            handle.write(files[name])
    return report


def strict_json(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise InputError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def invalid_constant(value: str) -> None:
        raise InputError("NONFINITE_JSON")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise InputError("INVALID_MANIFEST_JSON") from None


def verify_bundle(output: Path) -> dict[str, Any]:
    if output.is_symlink() or not output.is_dir() or (output / "sources").is_symlink():
        raise InputError("BUNDLE_DIRECTORY")
    manifest = strict_json(read_regular(output / "manifest.json", 512_000))
    if type(manifest) is not dict or set(manifest) != {"tool_version", "sources", "files"}:
        raise InputError("MANIFEST_SHAPE")
    if manifest["tool_version"] != VERSION:
        raise InputError("TOOL_VERSION_MISMATCH")
    sources = manifest["sources"]
    if type(sources) is not list or not 1 <= len(sources) <= MAX_SOURCES:
        raise InputError("MANIFEST_SOURCES")
    inputs: dict[str, bytes] = {}
    seen = set()
    for source in sources:
        if type(source) is not dict or set(source) != {"sha256", "aliases"}:
            raise InputError("MANIFEST_SOURCE")
        sha, aliases = source["sha256"], source["aliases"]
        if type(sha) is not str or not re.fullmatch(r"[0-9a-f]{64}", sha) or sha in seen:
            raise InputError("MANIFEST_SOURCE_DIGEST")
        seen.add(sha)
        if type(aliases) is not list or not 1 <= len(aliases) <= MAX_SOURCES:
            raise InputError("MANIFEST_ALIASES")
        raw = read_regular(output / "sources" / (sha + ".xml"), MAX_SOURCE_BYTES)
        if digest(raw) != sha:
            raise InputError("SOURCE_DIGEST_MISMATCH")
        for alias in aliases:
            if type(alias) is not str or alias in inputs:
                raise InputError("MANIFEST_ALIAS_COLLISION")
            inputs[alias] = raw
    expected, report = bundle(inputs)
    observed_names = set()
    for path in output.rglob("*"):
        if path.is_symlink():
            raise InputError("SYMLINK_NOT_SUPPORTED")
        if path.is_dir():
            if path != output / "sources":
                raise InputError("UNEXPECTED_DIRECTORY")
        else:
            observed_names.add(path.relative_to(output).as_posix())
    if observed_names != set(expected):
        raise InputError("BUNDLE_FILE_SET_MISMATCH")
    for name, data in expected.items():
        if read_regular(output / name, len(data)) != data:
            raise InputError("BUNDLE_RECOMPILE_MISMATCH", name)
    return report


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="create a new retained-source review directory")
    build.add_argument("inputs", nargs="+", type=Path)
    build.add_argument("--out", type=Path, required=True)
    verify = commands.add_parser("verify", help="recompile and compare every retained byte")
    verify.add_argument("directory", type=Path)
    args = cli.parse_args(argv)
    try:
        if args.command == "verify":
            report = verify_bundle(args.directory)
            print(json.dumps({"verification": "BYTE_CONSISTENT", "report_status": report["status"]}))
            return 0
        inputs = {}
        if len(args.inputs) > MAX_SOURCES:
            raise InputError("SOURCE_COUNT")
        for path in args.inputs:
            if path.name in inputs:
                raise InputError("DUPLICATE_INPUT_BASENAME")
            inputs[path.name] = read_regular(path, MAX_SOURCE_BYTES)
        report = write_bundle(inputs, args.out)
        print(json.dumps({"status": report["status"], "counts": report["counts"]}, sort_keys=True))
        return {"EXTRACTED": 0, "REVIEW_REQUIRED": 1, "SOURCE_REJECTED": 2}[report["status"]]
    except (InputError, OSError) as exc:
        # Avoid echoing bank content or arbitrary OS paths into shared logs.
        print(str(exc) if isinstance(exc, InputError) else type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
