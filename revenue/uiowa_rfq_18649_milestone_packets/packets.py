"""Build the three milestone packet folders and render their documents.

Every byte this module writes goes through `write_output`, which refuses any
destination outside the run's output directory. Nothing else in the package
opens a file for writing, and nothing anywhere removes, renames, moves, or
truncates a path. `test_milestone_packets.py` asserts both halves of that --
statically against this source, and dynamically by hashing an input tree before
and after a full run.

The renderer also refuses to emit the strings that would turn a draft into a
false assertion (PAID, INVOICE_ISSUED, ACCEPTED as a status, ...). That check
runs on the finished text, after templating, because the risk is not that
someone sets a bad enum -- it is that a free-text transmittal note says "as
accepted on the 14th".
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from typing import Any

import schedule
from schema import (
    DRAFT_STAMP,
    FORBIDDEN_CLAIM_STATES,
    SYNTHETIC_BANNER,
    UNKNOWN,
    AcceptanceRecord,
    ForbiddenClaimError,
)

INDEX_COLUMNS = [
    "item_id", "title", "path", "declared_version", "content_sha256",
    "size_bytes", "resolution_state", "source", "custodian",
    "storage_location", "disposition", "criteria_ids",
]

# Claims this tool may never make about a payment, in any packet, ever. It has
# no authority to issue an invoice or observe a payment, so these are absolute.
_NEVER = (
    r"\bpaid\b",
    r"\binvoice\s+issued\b",
    r"\bapproved\s+for\s+payment\b",
    r"\bpayment\s+received\b",
)

# Acceptance is different, and the first version of this guard got it wrong by
# treating it the same: it refused to render M-1's genuine, dated client
# acceptance record. Reporting a real acceptance record is correct; ASSERTING
# acceptance with no record behind it is the actual failure mode. So the
# acceptance claim is gated on the record existing, not banned outright.
_ONLY_WITH_RECORD = (
    r"\baccepted\b",
    r"\bacceptance\s+recorded\b",
)


def assert_no_forbidden_claim(text, where, acceptance_on_record=False):
    """Refuse rendered prose that asserts something this tool cannot know.

    Runs on the finished text rather than on enum values, because the risk is
    not a bad status field -- it is a free-text transmittal note that says
    "as accepted on the 14th" or "invoice issued".
    """
    haystack = text.replace("_", " ").lower()
    patterns = list(_NEVER)
    if not acceptance_on_record:
        patterns += list(_ONLY_WITH_RECORD)
    for pattern in patterns:
        match = re.search(pattern, haystack)
        if match:
            raise ForbiddenClaimError(
                f"{where}: refusing to render the claim {match.group(0)!r}. This "
                "tool produces drafts; it cannot assert an issued invoice or a "
                "payment, and it cannot assert acceptance without a dated "
                "acceptance record."
            )


def write_output(output_dir: str, relative_path: str, text: str) -> str:
    """The only writer in the package.

    Refuses any target that resolves outside `output_dir`, so a crafted
    milestone_id or filename cannot reach the rest of the filesystem. Creates
    directories; never deletes or replaces anything outside its own tree.
    """
    if os.path.isabs(relative_path):
        raise ValueError(f"refusing absolute output path {relative_path!r}")
    root = os.path.realpath(output_dir)
    target = os.path.realpath(os.path.join(root, relative_path))
    if target != root and not target.startswith(root + os.sep):
        raise ValueError(
            f"refusing to write outside the output directory: {relative_path!r}"
        )
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return target


def _slug(value: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in value]
    return "".join(keep).strip("-").lower() or "milestone"


def _fmt(value: Any) -> str:
    return "UNKNOWN" if value is UNKNOWN else str(value)


def index_rows(milestone, resolutions: dict) -> list:
    rows = []
    for item in milestone.index_items:
        res = resolutions.get(item.item_id)
        rows.append(
            {
                "item_id": item.item_id,
                "title": item.title,
                "path": item.path,
                "declared_version": _fmt(item.declared_version),
                "content_sha256": _fmt(res.sha256) if res else "UNKNOWN",
                "size_bytes": _fmt(res.size_bytes) if res else "UNKNOWN",
                "resolution_state": res.state if res else "UNRESOLVED_MISSING",
                "source": _fmt(item.source),
                "custodian": _fmt(item.custodian),
                "storage_location": _fmt(item.storage_location),
                "disposition": _fmt(item.disposition),
                "criteria_ids": ";".join(item.criteria_ids),
            }
        )
    return rows


def render_index_csv(milestone, resolutions: dict) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=INDEX_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in index_rows(milestone, resolutions):
        writer.writerow(row)
    return buf.getvalue()


def render_transmittal(engagement, milestone, resolutions: dict) -> str:
    resolved = [r for r in (resolutions.get(i.item_id) for i in milestone.index_items) if r and r.opens]
    lines = [
        f"# Transmittal - {milestone.milestone_id} {milestone.name}",
        "",
        f"> {DRAFT_STAMP}",
        f"> {SYNTHETIC_BANNER}",
        "",
        f"Engagement: {engagement.title} ({engagement.engagement_id})",
        f"Milestone: {milestone.milestone_id} - {milestone.name} [{milestone.kind}]",
        f"Submission state: {milestone.submission_state}",
        f"Delivered on: {_fmt(milestone.delivered_on)}",
        f"Acceptance state: {milestone.acceptance_state}",
        "",
        milestone.transmittal_note or "(transmittal note not drafted)",
        "",
        f"Files transmitted: {len(resolved)} of {len(milestone.index_items)} cited "
        "artifacts opened and were digested at packet build time.",
        "",
    ]
    for item in milestone.index_items:
        res = resolutions.get(item.item_id)
        digest = res.sha256[:16] + "..." if (res and res.opens) else "NOT VERIFIED"
        lines.append(
            f"- {item.item_id} {item.title} "
            f"(version {_fmt(item.declared_version)}, sha256 {digest})"
        )
    lines += [
        "",
        "This transmittal records what was sent and when. It does not record, "
        "request, or imply the recipient's acceptance.",
    ]
    return "\n".join(lines) + "\n"


def render_invoice_description(engagement, milestone) -> str:
    """A description a person could paste into an invoice -- not an invoice."""
    lines = [
        f"# Draft invoice description - {milestone.milestone_id}",
        "",
        f"> {DRAFT_STAMP}",
        f"> {SYNTHETIC_BANNER}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Engagement | {engagement.title} ({engagement.engagement_id}) |",
        f"| Milestone | {milestone.milestone_id} - {milestone.name} |",
        f"| Milestone kind | {milestone.kind} |",
        f"| Amount | {milestone.amount.dollars()} |",
        f"| Billing state | {milestone.billing_state} |",
        f"| Acceptance state | {milestone.acceptance_state} |",
        "",
        "Description line:",
        "",
        f"    {milestone.invoice_description or '(invoice description not drafted)'}",
        "",
        "Billing readiness is not asserted here. This file is a description a "
        "person may use when raising an invoice through the normal process; no "
        "invoice number is assigned, nothing is submitted, and no payment "
        "status is represented.",
    ]
    return "\n".join(lines) + "\n"


def render_packet_markdown(engagement, milestone, resolutions, result, as_of) -> str:
    lines = [
        f"# Milestone packet - {milestone.milestone_id} {milestone.name}",
        "",
        f"> {DRAFT_STAMP}",
        f"> {SYNTHETIC_BANNER}",
        "",
        f"Packet status: **{result.status}** "
        f"({len(result.errors)} error(s), {len(result.warnings)} warning(s)), "
        f"as of {as_of}",
        "",
        "## Milestone",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Milestone | {milestone.milestone_id} |",
        f"| Kind | {milestone.kind} |",
        f"| Amount | {milestone.amount.dollars()} |",
        f"| Due date | {_fmt(milestone.due_date)} |",
        f"| Submission state | {milestone.submission_state} |",
        f"| Delivered on | {_fmt(milestone.delivered_on)} |",
        f"| Acceptance state | {milestone.acceptance_state} |",
        f"| Billing state | {milestone.billing_state} |",
        "",
    ]
    if isinstance(milestone.acceptance, AcceptanceRecord):
        lines += [
            f"Acceptance record: {milestone.acceptance.recorded_on}, "
            f"{milestone.acceptance.recorded_by}, ref {milestone.acceptance.reference}.",
            "",
        ]
    else:
        lines += [
            "No acceptance record supplied. Delivery does not imply acceptance, so "
            "the acceptance state above is derived from the absence of a record.",
            "",
        ]

    lines += ["## Applicable criteria", ""]
    if milestone.criteria:
        for crit in milestone.criteria:
            cited = ", ".join(crit.evidence_item_ids) or "none cited"
            lines.append(f"- **{crit.criterion_id}** {crit.text}")
            lines.append(f"  - evidence cited: {cited}")
    else:
        lines.append("- (no criteria recorded for this milestone)")
    lines += [
        "",
        "Evidence cited above means an index row exists and its artifact opened. "
        "It does not mean the criterion was judged met; that is the reviewer's "
        "call, not this tool's.",
        "",
        "## Delivered-file index",
        "",
        "| Item | Title | Version | sha256 | State | Source | Custodian | Location | Disposition |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in index_rows(milestone, resolutions):
        digest = row["content_sha256"]
        digest = digest[:12] + "..." if digest != "UNKNOWN" else "UNKNOWN"
        lines.append(
            f"| {row['item_id']} | {row['title']} | {row['declared_version']} | "
            f"{digest} | {row['resolution_state']} | {row['source']} | "
            f"{row['custodian']} | {row['storage_location']} | {row['disposition']} |"
        )

    lines += ["", "## Open dependencies", ""]
    open_deps = [d for d in milestone.dependencies if d.state == "OPEN"]
    if not open_deps:
        lines.append("None recorded.")
    for dep in open_deps:
        status = schedule.classify_due(dep.needed_by, as_of, closed=False)
        lines.append(
            f"- **{dep.dependency_id}** {dep.description} - owner "
            f"{_fmt(dep.owner)}, needed by {_fmt(dep.needed_by)} - "
            f"**{status.state}** ({status.note})"
        )

    lines += ["", "## Packet findings", ""]
    if not result.findings:
        lines.append("No findings.")
    for f in result.findings:
        target = f" [{f.item_id}]" if f.item_id is not UNKNOWN else ""
        lines.append(f"- `{f.severity}` **{f.code}**{target} - {f.message}")

    lines += [
        "",
        "## Transmittal",
        "",
        milestone.transmittal_note or "(transmittal note not drafted)",
        "",
        "## Draft invoice description",
        "",
        f"    {milestone.invoice_description or '(invoice description not drafted)'}",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_completeness_markdown(engagement, report) -> str:
    lines = [
        "# Milestone packet completeness report",
        "",
        f"> {SYNTHETIC_BANNER}",
        "",
        f"Engagement: {engagement.title} ({engagement.engagement_id})",
        f"As of: {report.as_of}",
        f"Contract total: {engagement.contract_total.dollars()} "
        f"({engagement.contract_total.cents} cents)",
        f"Milestone amounts total: {engagement.milestone_total().dollars()} "
        f"({engagement.milestone_total().cents} cents)",
        "",
        f"**Overall: {'PASS' if report.passed else 'FAIL'}** - "
        f"{report.error_count} error(s), {report.warning_count} warning(s)",
        "",
        "| Milestone | Kind | Amount | Submitted | Acceptance | Billing | Status | Errors | Warnings |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for mr in report.milestone_results:
        lines.append(
            f"| {mr.milestone_id} | {mr.kind} | {mr.amount_display} | "
            f"{mr.submission_state} | {mr.acceptance_state} | {mr.billing_state} | "
            f"{mr.status} | {len(mr.errors)} | {len(mr.warnings)} |"
        )
    lines += ["", "## Engagement-level findings", ""]
    if not report.engagement_findings:
        lines.append("None.")
    for f in report.engagement_findings:
        lines.append(f"- `{f.severity}` **{f.code}** - {f.message}")

    for mr in report.milestone_results:
        lines += ["", f"## {mr.milestone_id} - {mr.name}", ""]
        if not mr.findings:
            lines.append("No findings.")
        for f in mr.findings:
            target = f" [{f.item_id}]" if f.item_id is not UNKNOWN else ""
            lines.append(f"- `{f.severity}` **{f.code}**{target} - {f.message}")

    lines += [
        "",
        "## What this report does and does not say",
        "",
        "- `READY_TO_SUBMIT_AS_DRAFT` means the packet has no unverifiable "
        "citation and no unmade disposition decision. It is not an approval, "
        "an acceptance, or a billing authorization.",
        "- An `UNKNOWN` field is reported as UNKNOWN. It is never defaulted, "
        "zeroed, or counted as satisfied.",
        "- A cited artifact that did not open is an ERROR. It is never "
        "represented as delivered.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build(engagement, resolutions, report, output_dir, as_of) -> list:
    """Write three packet folders plus the completeness report. Returns paths."""
    written = []
    results = {mr.milestone_id: mr for mr in report.milestone_results}
    for ms in engagement.milestones:
        folder = f"packets/{ms.sequence:02d}-{_slug(ms.milestone_id)}-{_slug(ms.kind)}"
        result = results[ms.milestone_id]

        docs = {
            f"{folder}/PACKET.md": render_packet_markdown(
                engagement, ms, resolutions, result, as_of
            ),
            f"{folder}/TRANSMITTAL.md": render_transmittal(engagement, ms, resolutions),
            f"{folder}/INVOICE_DESCRIPTION_DRAFT.md": render_invoice_description(
                engagement, ms
            ),
            f"{folder}/delivered_file_index.csv": render_index_csv(ms, resolutions),
            f"{folder}/packet.json": json.dumps(
                {
                    "engagement_id": engagement.engagement_id,
                    "milestone_id": ms.milestone_id,
                    "kind": ms.kind,
                    "amount_cents": ms.amount.cents,
                    "amount_display": ms.amount.dollars(),
                    "submission_state": ms.submission_state,
                    "acceptance_state": ms.acceptance_state,
                    "billing_state": ms.billing_state,
                    "draft_stamp": DRAFT_STAMP,
                    "synthetic": engagement.synthetic,
                    "as_of": as_of,
                    "status": result.status,
                    "index": index_rows(ms, resolutions),
                    "findings": [f.to_json() for f in result.findings],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        }
        for rel, text in docs.items():
            if rel.endswith((".md", ".json")):
                assert_no_forbidden_claim(
                    text, rel,
                    acceptance_on_record=isinstance(ms.acceptance, AcceptanceRecord),
                )
            written.append(write_output(output_dir, rel, text))

    completeness_md = render_completeness_markdown(engagement, report)
    any_record = any(
        isinstance(m.acceptance, AcceptanceRecord) for m in engagement.milestones
    )
    assert_no_forbidden_claim(
        completeness_md, "COMPLETENESS_REPORT.md", acceptance_on_record=any_record
    )
    written.append(write_output(output_dir, "COMPLETENESS_REPORT.md", completeness_md))
    written.append(
        write_output(
            output_dir,
            "completeness_report.json",
            json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n",
        )
    )
    return written
