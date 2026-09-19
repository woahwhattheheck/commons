"""Renderers: the leadership document, the traceability matrix, the compile report.

Three outputs because they have three different readers, and collapsing them is how
traceability dies. Leadership reads the summary. A reviewer challenging a sentence
reads the matrix. The author fixing a rejected sentence reads the compile report.
"""

import csv
import io

from evidence import STRENGTH_MEANING

STRENGTH_BADGE = {
    "SETTLED": "established",
    "INDICATED": "indicated",
    "SINGLE_SOURCE": "single source",
}


def render_executive_summary(result):
    """The leadership document. Contains ONLY statements that passed every check."""
    out = [f"# {result['title']}", "",
           f"Source register: {result['source_label']}", ""]
    stats = result["stats"]
    out += [f"> Compiled from {stats['findings_total']} findings. "
            f"{stats['statements_accepted']} of {stats['statements_submitted']} "
            f"drafted statements are rendered below; "
            f"{stats['statements_rejected']} were rejected and are listed with "
            f"reasons in the compile report. Every sentence below carries the "
            f"finding ID that establishes it.", ""]

    for section in result["sections"]:
        if not section["statement_ids"]:
            continue
        out += [f"## {section['heading']}", ""]
        for statement_id in section["statement_ids"]:
            entry = result["accepted"][statement_id]
            citations = ", ".join(f"`{f.finding_id}`" for f in entry["findings"])
            badge = STRENGTH_BADGE.get(entry["supported_strength"], "")
            out.append(f"- {entry['statement'].text} [{citations} - {badge}]")
        out.append("")

    if result["unresolved"]:
        out += ["## Open questions - not resolved by this assessment", "",
                "These are recorded as UNKNOWN. None of them is a finding of "
                "absence, and none is summarized above.", ""]
        for item in result["unresolved"]:
            out.append(f"- ({item['area']}, `{item['finding_id']}`) {item['item']}")
        out.append("")

    dropped = [sid for section in result["sections"]
               for sid in section["dropped_statement_ids"]]
    if dropped:
        out += ["## Statements withheld from this summary", "",
                f"{len(dropped)} drafted statement(s) did not survive compilation and "
                f"are NOT rendered above: " +
                ", ".join(f"`{sid}`" for sid in dropped) +
                ". See the compile report for the reason and the remedy for each.", ""]
    return "\n".join(out).rstrip() + "\n"


def render_traceability_matrix_csv(result):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["statement_id", "statement_text", "finding_id", "finding_title",
                     "basis", "confidence", "max_assertable_strength", "scope",
                     "severity", "evidence_id", "evidence_kind", "evidence_locator",
                     "collected_on"])
    for statement_id in sorted(result["accepted"]):
        entry = result["accepted"][statement_id]
        for finding in entry["findings"]:
            if not finding.evidence:
                writer.writerow([statement_id, entry["statement"].text,
                                 finding.finding_id, finding.title, finding.basis,
                                 finding.confidence, finding.max_strength,
                                 finding.scope_label, finding.severity,
                                 "", "", "NO EVIDENCE ATTACHED", ""])
                continue
            for item in finding.evidence:
                writer.writerow([statement_id, entry["statement"].text,
                                 finding.finding_id, finding.title, finding.basis,
                                 finding.confidence, finding.max_strength,
                                 finding.scope_label, finding.severity,
                                 item.evidence_id, item.kind, item.locator,
                                 item.collected_on])
    return buffer.getvalue()


def render_compile_report(result, rejected_findings):
    out = ["# Compile report", "",
           f"Source register: {result['source_label']}", ""]
    stats = result["stats"]
    out += ["| Metric | Value |", "|---|---|"]
    for key in ("statements_submitted", "statements_accepted", "statements_rejected",
                "findings_total", "findings_cited", "findings_uncited"):
        out.append(f"| {key.replace('_', ' ')} | {stats[key]} |")
    out.append("")

    if rejected_findings:
        out += ["## Findings rejected at load", "",
                "Malformed records are named and excluded. They are NOT repaired with "
                "defaults, because a repaired finding becomes citable by a leadership "
                "statement.", ""]
        for item in rejected_findings:
            out.append(f"- `{item['raw_id']}` - {item['error']}")
        out.append("")

    if result["rejected"]:
        out += ["## Statements rejected", "",
                "Each rejection names the check, the reason, and the remedy. The "
                "author fixes the sentence; the compiler does not soften it for them.",
                ""]
        for item in result["rejected"]:
            out += [f"### `{item['statement_id']}`", "",
                    f"> {item['text']}", "",
                    f"Cites: " + (", ".join(f"`{c}`" for c in item["cites"])
                                  or "*nothing*"), ""]
            for problem in item["problems"]:
                out += [f"- **{problem['code']}** - {problem['reason']}",
                        f"  - *Remedy:* {problem['remedy']}"]
            out.append("")

    # The quiet failure of an executive summary is the finding that got dropped,
    # not the one that got overstated. Split the two very different reasons a
    # finding can be uncited.
    droppable = [f for f in result["uncited_findings"]
                 if f.max_strength != "NOT_ESTABLISHED"]
    not_assertable = [f for f in result["uncited_findings"]
                      if f.max_strength == "NOT_ESTABLISHED"]

    out += ["## Coverage: findings not represented in the summary", ""]
    if droppable:
        out += ["**Assertable but uncited.** These findings COULD have been stated and "
                "were not. Each one is either a deliberate editorial choice or a "
                "finding that fell out of the summary unnoticed.", "",
                "| Finding | Severity | Strength | Scope | Title |", "|---|---|---|---|---|"]
        for finding in droppable:
            out.append(f"| `{finding.finding_id}` | **{finding.severity}** | "
                       f"{finding.max_strength} | {finding.scope_label} | "
                       f"{finding.title} |")
        out.append("")
    if not_assertable:
        out += ["**Not assertable, correctly absent.** These are uncited because "
                "nothing may be asserted from them. They belong in the open-questions "
                "section of the summary, and they are there.", ""]
        for finding in not_assertable:
            out.append(f"- `{finding.finding_id}` ({finding.severity}) - "
                       f"{finding.title}. {STRENGTH_MEANING['NOT_ESTABLISHED']}")
        out.append("")
    if not result["uncited_findings"]:
        out += ["Every finding in the register is represented in the summary.", ""]
    return "\n".join(out).rstrip() + "\n"
