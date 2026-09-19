"""Plain-text alternatives, generated from the same data that draws the figure.

Why generation rather than a hand-written caption: a hand-written alt text is
correct on the day it is written and wrong the first time the data changes.
Every function here reads the same `Matrix` the figure reads, so the two cannot
disagree. figures.py calls these to fill each SVG's <desc>, which means the
accessible description and the picture are produced from one source.

Two rules the text keeps that a careless summary would lose:
  * Never say "not assessed" in a way that implies a poor result. The phrasing
    is always about the review's evidence, not the group's performance.
  * Never state an average band or a score. Counts only.

Also produces the TABLE templates -- Markdown and plain text -- carrying the
same glyph + label redundancy as the charts, so the report's tabular version is
not a second-class citizen.

Python 3 standard library only.
"""

from __future__ import annotations

import palette

FICTION_PREFIX = "SYNTHETIC EXAMPLE - not a University finding."


def _cell_phrase(cell) -> str:
    if cell is None:
        return "no record supplied"
    b = cell.band
    if b.key == "UNASSESSED":
        return "not assessed (outside the agreed scope for this group)"
    if b.key == "INSUFFICIENT_EVIDENCE":
        return (f"insufficient evidence ({cell.evidence_total} items collected, "
                f"not enough to support a rating)")
    return f"{b.label.lower()} ({cell.evidence_total} evidence items)"


def matrix_alt(matrix) -> str:
    t = matrix.totals()
    lines = [
        f"{matrix.disclaimer}",
        f"Assessment matrix: {len(matrix.group_ids)} groups by {len(matrix.area_ids)} "
        f"assessment areas, {t['cells_expected']} cells.",
        f"{t['rated']} cells carry a rating; {t['insufficient_evidence']} had insufficient "
        f"evidence; {t['not_assessed']} were not assessed"
        + (f"; {t['cells_missing']} have no record supplied." if t["cells_missing"] else "."),
        "Unrated cells describe the evidence available to this review, not the performance "
        "of the group, and are excluded from every count of ratings.",
    ]
    for gid in matrix.group_ids:
        parts = []
        for aid in matrix.area_ids:
            parts.append(f"{matrix.area_label(aid)}: {_cell_phrase(matrix.cell(gid, aid))}")
        lines.append(f"{matrix.group_label(gid)} ({gid}) - " + "; ".join(parts) + ".")
    return " ".join(lines)


def cross_group_alt(matrix) -> str:
    lines = [
        matrix.disclaimer,
        "Comparison across groups. Each assessment area is a column; each rating is a "
        "horizontal lane, strongest at the top. Two further lanes sit below a dividing rule: "
        "insufficient evidence, and not assessed. Those two are not lower ratings - they are "
        "statements about the evidence this review holds.",
    ]
    for aid in matrix.area_ids:
        by_band: dict[str, list[str]] = {}
        for gid in matrix.group_ids:
            cell = matrix.cell(gid, aid)
            key = cell.band_key if cell is not None else "NO_RECORD"
            by_band.setdefault(key, []).append(gid)
        parts = []
        for key in palette.BAND_ORDER + ("NO_RECORD",):
            if key in by_band:
                label = ("no record supplied" if key == "NO_RECORD"
                         else palette.BANDS[key].label)
                parts.append(f"{label}: {', '.join(by_band[key])}")
        lines.append(f"{matrix.area_label(aid)} - " + "; ".join(parts) + ".")
    ctx = [f"{gid} is {matrix.group_context(gid)}" for gid in matrix.group_ids
           if matrix.group_context(gid)]
    if ctx:
        lines.append("Group context: " + "; ".join(ctx)
                     + ". Groups differ in size, funding and service model; read a difference "
                       "as a prompt for a question, not as a ranking.")
    return " ".join(lines)


def evidence_alt(matrix) -> str:
    lines = [
        matrix.disclaimer,
        "Evidence behind each group, as a stacked bar of items collected by kind: "
        + ", ".join(k["label"].lower() for k in palette.EVIDENCE_KINDS) + ".",
    ]
    for gid in matrix.group_ids:
        s = matrix.summarize_group(gid)
        breakdown = ", ".join(
            f"{palette.evidence_kind(k)['label'].lower()} {s.evidence[k]}"
            for k in palette.EVIDENCE_KEYS if s.evidence[k]
        ) or "none"
        lines.append(f"{s.label} ({gid}): {s.evidence_total} items - {breakdown}. "
                     f"{s.coverage_sentence}")
    lines.append("A longer bar means the area is better evidenced, not that the group performs "
                 "better. Areas not assessed contribute no evidence and are not shown as zero.")
    return " ".join(lines)


def roadmap_alt(matrix) -> str:
    lines = [matrix.disclaimer,
             "Phased roadmap in three planning horizons: "
             + ", ".join(f"phase {p['badge']} {p['label']}" for p in palette.PHASES) + "."]
    if not matrix.roadmap:
        lines.append("No roadmap items supplied.")
        return " ".join(lines)
    for p in palette.PHASES:
        items = [i for i in matrix.roadmap if i["phase"] == p["key"]]
        if not items:
            lines.append(f"Phase {p['badge']} ({p['label']}): no items.")
            continue
        described = []
        for item in items:
            bits = [f"{item['id']} {item['title']}, from {item['recommendation']}"]
            bits.append(f"effort {item['effort']}" if item.get("effort")
                        else "effort not estimated")
            deps = item.get("depends_on") or []
            if deps:
                bits.append("after " + ", ".join(deps))
            described.append("; ".join(bits))
        lines.append(f"Phase {p['badge']} ({p['label']}): " + ". ".join(described) + ".")
    lines.append("Phase windows are planning horizons, not commitments. Items with no effort "
                 "estimate are marked as such and not scheduled by guesswork.")
    return " ".join(lines)


ALT_BUILDERS = {
    "matrix": matrix_alt,
    "cross-group": cross_group_alt,
    "evidence-coverage": evidence_alt,
    "roadmap": roadmap_alt,
}


# --------------------------------------------------------------------------
# Table templates. Same redundancy contract: glyph + written label, never a
# colour swatch on its own, and never a number standing in for a band.
# --------------------------------------------------------------------------
def matrix_markdown(matrix) -> str:
    out = [f"### {matrix.title}: assessment matrix", "", f"*{matrix.disclaimer}*", ""]
    header = "| Group | " + " | ".join(matrix.area_label(a) for a in matrix.area_ids) + " |"
    out.append(header)
    out.append("|---" * (len(matrix.area_ids) + 1) + "|")
    for gid in matrix.group_ids:
        cells = []
        for aid in matrix.area_ids:
            cell = matrix.cell(gid, aid)
            if cell is None:
                cells.append("`??` No record supplied")
                continue
            b = cell.band
            cells.append(f"{b.glyph} **{b.label}**")
        out.append(f"| **{gid}** {matrix.group_label(gid)} | " + " | ".join(cells) + " |")
    out += ["", "**Key**", ""]
    out.append("| Mark | Band | What it means |")
    out.append("|---|---|---|")
    for key in palette.ORDINAL_KEYS:
        b = palette.BANDS[key]
        out.append(f"| {b.glyph} | **{b.label}** | {b.meaning} |")
    out.append("| | | *Below: not ratings.* |")
    for key in palette.NON_RATING_KEYS:
        b = palette.BANDS[key]
        out.append(f"| {b.glyph} | **{b.label}** | {b.meaning} |")
    out += ["", "Unrated cells describe the evidence available to this review, not the "
                "performance of the group. They are excluded from every count of ratings.", ""]
    return "\n".join(out)


def coverage_markdown(matrix) -> str:
    out = [f"### {matrix.title}: evidence coverage", "", f"*{matrix.disclaimer}*", ""]
    out.append("| Group | " + " | ".join(k["label"] for k in palette.EVIDENCE_KINDS)
               + " | Total | Coverage |")
    out.append("|---" * (len(palette.EVIDENCE_KINDS) + 3) + "|")
    for gid in matrix.group_ids:
        s = matrix.summarize_group(gid)
        counts = " | ".join(str(s.evidence[k]) for k in palette.EVIDENCE_KEYS)
        out.append(f"| **{gid}** {s.label} | {counts} | **{s.evidence_total}** | "
                   f"{s.coverage_sentence} |")
    out += ["", "A larger total means the area is better evidenced, not that the group "
                "performs better.", ""]
    return "\n".join(out)


def roadmap_markdown(matrix) -> str:
    out = [f"### {matrix.title}: phased roadmap", "", f"*{matrix.disclaimer}*", ""]
    out.append("| Phase | Window | Item | From | Effort | Prerequisite |")
    out.append("|---|---|---|---|---|---|")
    for p in palette.PHASES:
        for item in [i for i in matrix.roadmap if i["phase"] == p["key"]]:
            effort = item.get("effort") or "_not estimated_"
            deps = ", ".join(item.get("depends_on") or []) or "-"
            out.append(f"| {p['badge']} | {p['label']} | **{item['id']}** {item['title']} "
                       f"| {item['recommendation']} | {effort} | {deps} |")
    out += ["", "Phase windows are planning horizons, not commitments. Items with no effort "
                "estimate are shown as *not estimated* and are never given a guessed value.", ""]
    return "\n".join(out)


def alt_text_bundle(matrix) -> str:
    """One document carrying the text alternative for every figure."""
    out = [f"# {matrix.title} - text alternatives for every figure", "",
           f"{matrix.disclaimer}", "",
           "Each block below is the exact text embedded in the matching SVG's <desc> "
           "element. A reader using a screen reader, a plain-text export or a printed "
           "black-and-white copy receives the same content as a reader seeing colour.", ""]
    titles = {
        "matrix": "Figure 1 - Assessment matrix",
        "cross-group": "Figure 2 - Comparison across groups",
        "evidence-coverage": "Figure 3 - Evidence behind each group",
        "roadmap": "Figure 4 - Phased roadmap",
    }
    for key in ("matrix", "cross-group", "evidence-coverage", "roadmap"):
        out += [f"## {titles[key]}", "", ALT_BUILDERS[key](matrix), ""]
    out += ["## Tables", "", matrix_markdown(matrix), "", coverage_markdown(matrix), "",
            roadmap_markdown(matrix), ""]
    return "\n".join(out)
