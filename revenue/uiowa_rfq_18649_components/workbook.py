"""Optional artifact_tool XLSX view; core assessment and CSV exports need only Python.

Run: python workbook.py sample.json --out component-maintenance.xlsx
Blue decision cells are human preparation notes; they do not authorize changes.
"""
from __future__ import annotations
import argparse
import hashlib
from datetime import datetime
from pathlib import Path

from components import assess, json_bytes, load, safe_cell, InputError


def make_workbook(doc: dict):
    from artifact_tool import Workbook
    report = assess(doc)
    wb = Workbook.create()
    cover = wb.worksheets.add("Overview")
    cover.get_range("A1:H25").format.column_width = 13
    cover.get_range("A1:H25").format.row_height = 23
    cover.get_range("A1:H25").format.wrap_text = True
    cover.merge_cells("A1:H2")
    cover.get_range("A1").values = [["COMPONENT MAINTENANCE | FICTIONAL REHEARSAL"]]
    cover.get_range("A1:H2").format = {"fill": "#16324F", "font": {"bold": True, "color": "#FFFFFF"}}
    cover.merge_cells("A3:H4")
    cover.get_range("A3").values = [["UIOWA-056 | Supplied-record assessment as of " + report["as_of"] + ". No real University data, product recommendations, live probes, or authority to change systems."]]

    specs = {
        "Components": ("components", "component_id name groups service_ids support_state support_evidence_quality support_ends_on owner_role inventory_evidence_quality last_update_on review_due_on evidence_ids"),
        "Advisories": ("advisories", "component_id advisory_id qualified_applicability qualified_reported_exposure record_disposition overdue owner_role due_on exception_until applicability_evidence_quality exposure_evidence_quality disposition_evidence_quality evidence_ids reported_applicability reported_exposure"),
        "Roadmap": ("roadmap", "maintenance_id component_id priority service_ids owner_role change effort_low_days effort_high_days reasons coordination_notes"),
        "Evidence": ("evidence", "id kind observed_on locator component_ids advisory_id"),
        "Services": ("services", "id name group"),
    }
    sheets = {}
    ends = {}
    for name, (key, names) in specs.items():
        columns = names.split()
        rows = report[key]
        sheet = wb.worksheets.add(name)
        sheets[name] = sheet
        ends[name] = max(4, len(rows) + 3)
        sheet.get_range_by_indexes(0, 0, ends[name], len(columns)).format.column_width = 20
        sheet.get_range_by_indexes(0, 0, ends[name], len(columns)).format.row_height = 42
        sheet.get_range_by_indexes(0, 0, ends[name], len(columns)).format.wrap_text = True
        sheet.get_range_by_indexes(0, 0, 1, len(columns)).merge()
        sheet.get_range("A1").values = [[name + " | Generated snapshot; retain evidence IDs"]]
        sheet.get_range_by_indexes(0, 0, 1, len(columns)).format = {"fill": "#16324F", "font": {"bold": True, "color": "#FFFFFF"}}
        sheet.get_range_by_indexes(1, 0, 1, len(columns)).merge()
        sheet.get_range("A2").values = [["Fictional supplied records. UNKNOWN or blank is not a low maturity score or a clean bill of health. Modify canonical input and regenerate to change assessed states."]]
        sheet.get_range_by_indexes(2, 0, 1, len(columns)).values = [[c.replace("_", " ") for c in columns]]
        sheet.get_range_by_indexes(2, 0, 1, len(columns)).format = {"fill": "#DCE6F1", "font": {"bold": True}}
        values = []
        for row in rows:
            values.append([datetime.fromisoformat(row[c]) if c.endswith(("_on", "_until")) and row[c]
                           else safe_cell(row[c]) for c in columns])
        if values:
            sheet.get_range_by_indexes(3, 0, len(values), len(columns)).values = values
            sheet.tables.add(sheet.get_range_by_indexes(2, 0, len(values) + 1, len(columns)), True, "T" + name)
        for col, key_name in enumerate(columns):
            rng = sheet.get_range_by_indexes(3, col, max(1, len(values)), 1)
            if key_name.endswith(("_on", "_until")):
                rng.set_number_format("yyyy-mm-dd")
            if key_name.startswith("effort_"):
                rng.set_number_format("0.0")
            if key_name in ("evidence_ids", "reasons", "coordination_notes", "change", "locator"):
                rng.format.column_width = 38
                rng.format.row_height = 90
        sheet.freeze_panes.freeze_rows(3)
    comp_end, road_end = ends["Components"], ends["Roadmap"]
    cover.get_range("A6:D6").values = [["Recorded components", None, "Maintenance items", None]]
    cover.merge_cells("A6:B6")
    cover.merge_cells("C6:D6")
    cover.merge_cells("E6:F6")
    cover.merge_cells("G6:H6")
    cover.get_range("E6").values = [["Unestimated items"]]
    cover.get_range("G6").values = [["Known effort range"]]
    for start, end in (("A7", "B8"), ("C7", "D8"), ("E7", "F8"), ("G7", "H8")):
        cover.merge_cells(start + ":" + end)
    cover.get_range("A7").formulas = [[f"=COUNTA(Components!A4:A{comp_end})"]]
    cover.get_range("C7").formulas = [[f"=COUNTA(Roadmap!A4:A{road_end})"]]
    cover.get_range("E7").formulas = [[f"=COUNTA(Roadmap!A4:A{road_end})-COUNT(Roadmap!G4:G{road_end})"]]
    cover.get_range("G7").formulas = [[f'=SUM(Roadmap!G4:G{road_end})&" to "&SUM(Roadmap!H4:H{road_end})&" days"']]
    cover.get_range("A6:H8").format.fill = "#E7F0F8"
    cover.get_range("A6:H8").format.font.bold = True
    cover.get_range("A10:B14").values = [["Support state", "Components"], ["supported", None], ["ending_soon", None], ["unsupported", None], ["unknown", None]]
    cover.get_range("A10:B10").format = {"fill": "#DCE6F1", "font": {"bold": True}}
    for row in range(11, 15):
        cover.get_range(f"B{row}").formulas = [[f'=COUNTIF(Components!E4:E{comp_end},A{row})']]
    for r, note in ((10, "READING THE WORKBOOK"),
        (11, "Components: version, service scope, support and inventory evidence."),
        (12, "Advisories: applicability, reported exposure and disposition stay separate."),
        (13, "Roadmap: one row per shared component; effort is not multiplied by services."),
        (14, "Decisions: editable preparation notes only. Evidence: source IDs and dates.")):
        cover.merge_cells(f"D{r}:H{r}")
        cover.get_range(f"D{r}").values = [[note]]
    cover.get_range("D10:H10").format.font.bold = True
    cover.merge_cells("A16:H18")
    cover.get_range("A16").values = [[report["limitations"]]]
    cover.merge_cells("A20:H21")
    cover.get_range("A20").values = [["Practice-reference context: https://csrc.nist.gov/projects/ssdf — outcome-based secure-development guidance, not a certification checklist. The thresholds in this instrument are configurable preparation assumptions, not NIST requirements."]]
    cover.merge_cells("A23:H24")
    cover.get_range("A23").values = [["Canonical input SHA-256: " + hashlib.sha256(json_bytes(doc)).hexdigest()]]
    cover.get_range("A1:H24").format.vertical_alignment = "center"
    cover.get_range("A6:H8").format.horizontal_alignment = "center"
    cover.freeze_panes.freeze_rows(4)
    decisions = wb.worksheets.add("Decisions")
    headers = ["Component", "Owner role", "Proposed decision", "Rationale / constraints", "Evidence reference", "Next review date"]
    decision_rows = [[safe_cell(r["component_id"]), safe_cell(r["owner_role"]), "Investigate", "", "", None] for r in report["roadmap"]]
    decisions.get_range("A1:F1").values = [headers]
    decisions.get_range("A1:F1").format = {"fill": "#16324F", "font": {"bold": True, "color": "#FFFFFF"}}
    if decision_rows:
        decisions.get_range_by_indexes(1, 0, len(decision_rows), 6).values = decision_rows
        decisions.tables.add(decisions.get_range_by_indexes(0, 0, len(decision_rows)+1, 6), True, "TDecisions")
        decisions.get_range_by_indexes(1, 2, len(decision_rows), 1).data_validation = {"rule": {"type": "list", "values": ["Investigate", "Plan", "Defer", "No change"]}}
    decisions.get_range("A1:F30").format.column_width = 24
    decisions.get_range("D1:E30").format.column_width = 38
    decisions.get_range("A1:F30").format.wrap_text = True
    decisions.get_range("A1:F30").format.row_height = 42
    decisions.get_range("B2:F30").format.font.color = "#1D4ED8"
    decisions.get_range("F2:F30").set_number_format("yyyy-mm-dd")
    decisions.freeze_panes.freeze_rows(1)
    return wb, report


def main(argv=None):
    from artifact_tool import SpreadsheetFile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise InputError("workbook exists; select a new output path")
    wb, _ = make_workbook(load(args.input))
    SpreadsheetFile.export_xlsx(wb).save(str(args.out))


if __name__ == "__main__":
    main()
