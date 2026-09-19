#!/usr/bin/env python3
"""UIOWA-075 -- AI usefulness evaluation kit.

What this is
------------
A scorer for AI-assisted documentation, test drafting and requirements
summarization.  Tasks carry a *known answer key*, so correctness and
completeness are computed against ground truth rather than judged.  The fourth
measure -- time required to repair the output -- is the one that actually
decides whether an assisted workflow is cheaper, so it is measured separately
and never folded into the other three.

What this is NOT
----------------
* It does not call a model.  Nothing here is online, and nothing simulates a
  model.  It scores *recorded* candidate outputs supplied as fixtures.
* It does not emit a single "usefulness score".  Four measures, reported four
  ways, because a composite hides the trade the reader has to make.
* It does not score people.  The unit is a workflow, never an analyst.
* An absent input stays UNKNOWN.  Never a zero, never a pass, never a maturity
  rating.  A task with no recorded run is NOT_RUN and leaves every denominator.

The guardrail that matters most
-------------------------------
On a task whose answer is not derivable from the supplied sources, a confident
fabrication must score WORSE than an honest "this is not in the sources".  A kit
that ranks fluent invention above abstention will recommend the wrong workflow,
and it will do it convincingly.  ``test_eval_kit.py`` asserts that ordering on
all three measures.

Python 3 standard library only.  No network.  No third-party packages.
"""

import argparse
import os
import shutil
import sys
import tempfile
import unicodedata

import interchange as ix

UNKNOWN = "UNKNOWN"

CASE_CLASSES = ("ordinary", "ambiguous", "stale_context", "missing_information")

RESULT_COLUMNS = [
    ("workflow_id", "text"),
    ("task_id", "text"),
    ("family", "text"),
    ("case_class", "text"),
    ("status", "text"),
    ("matched_variant", "text"),
    ("tied_variants", "text"),
    ("required_total", "int"),
    ("required_hit", "int"),
    ("completeness", "float"),
    ("forbidden_fired", "int"),
    ("correctness", "float"),
    ("modeled_repair_minutes", "int"),
    ("measured_repair_minutes", "int"),
    ("repair_basis", "text"),
    ("generation_minutes", "int"),
    ("from_scratch_minutes", "int"),
    ("net_minutes_saved", "int"),
    ("reviewer", "text"),
    ("reviewer_note", "text"),
    ("analyst_followup", "text"),
    ("review_locator", "text"),
]


# ---------------------------------------------------------------- matching --

def normalize_for_match(text):
    """NFC + casefold + whitespace collapse.

    Deliberately not stemming or fuzzy-matching: an answer key that matches
    approximately is an answer key that can be argued with, and the point of a
    known-answer dataset is that it cannot.
    """
    folded = unicodedata.normalize("NFC", text).casefold()
    return " ".join(folded.split())


def matches(output_text, element):
    """all_of AND any_of AND (not none_of).

    ``none_of`` exists because of a real bug this kit's own tests caught: an
    ambiguous-case output that mentions BOTH defensible readings ("uses queue
    priority, not the business priority column") matched both answer variants,
    and the tie-break then silently attributed the wrong reading. A key for an
    ambiguous case has to be able to say what the output must NOT also say.
    """
    haystack = normalize_for_match(output_text)
    all_of = element.get("all_of") or []
    any_of = element.get("any_of") or []
    none_of = element.get("none_of") or []
    if not all_of and not any_of:
        raise ValueError(f"element {element.get('element_id')} has no positive match terms")
    if all_of and not all(normalize_for_match(t) in haystack for t in all_of):
        return False
    if any_of and not any(normalize_for_match(t) in haystack for t in any_of):
        return False
    if none_of and any(normalize_for_match(t) in haystack for t in none_of):
        return False
    return True


# ---------------------------------------------------------------- scoring ---

def score_variant(output_text, variant):
    required = variant.get("required") or []
    forbidden = variant.get("forbidden") or []
    hit = [e for e in required if matches(output_text, e)]
    miss = [e for e in required if e not in hit]
    fired = [f for f in forbidden if matches(output_text, f)]

    completeness = len(hit) / len(required) if required else None
    asserted = len(hit) + len(fired)
    # Precision of what the output actually asserted.  An output that asserts
    # nothing scorable gets 0.0, not a free pass -- it produced nothing we can
    # verify, which is a real outcome, not a missing measurement.
    correctness = (1.0 - len(fired) / asserted) if asserted else 0.0

    repair = sum(e.get("repair_minutes", 0) for e in miss)
    repair += sum(f.get("repair_minutes", 0) for f in fired)
    return {
        "variant_id": variant["variant_id"],
        "variant_label": variant.get("label", ""),
        "required_total": len(required),
        "required_hit": len(hit),
        "hit_ids": [e["element_id"] for e in hit],
        "missed_ids": [e["element_id"] for e in miss],
        "forbidden_fired": len(fired),
        "forbidden_ids": [f["element_id"] for f in fired],
        "forbidden_reasons": [f.get("reason", "") for f in fired],
        "completeness": completeness,
        "correctness": correctness,
        "modeled_repair_minutes": repair,
    }


def score_task(task, run):
    """Score one task for one workflow.  ``run`` may be None (NOT_RUN)."""
    base = {
        "task_id": task["task_id"],
        "family": task["family"],
        "case_class": task["case_class"],
        "from_scratch_minutes": task.get("from_scratch_minutes"),
    }
    if run is None:
        # No record exists.  That is absence of evidence about the workflow,
        # not evidence of a bad result.  It leaves every denominator.
        base.update({
            "status": "NOT_RUN",
            "matched_variant": None, "variant_label": None, "tied_variants": [],
            "tied_variants_text": None,
            "required_total": None, "required_hit": None,
            "completeness": None, "forbidden_fired": None, "correctness": None,
            "modeled_repair_minutes": None, "measured_repair_minutes": None,
            "repair_basis": UNKNOWN, "repair_minutes_used": None,
            "generation_minutes": None, "net_minutes_saved": None,
            "time_basis": UNKNOWN,
            "hit_ids": [], "missed_ids": [], "forbidden_ids": [], "forbidden_reasons": [],
            "reviewer": None, "reviewer_note": None,
            "analyst_followup": None, "review_locator": None,
        })
        return base

    output_text = run.get("output") or ""
    scored = [score_variant(output_text, v) for v in task["answer_variants"]]
    # The ambiguous case lives or dies here: every defensible variant is scored
    # and the best one wins, so two different correct answers both score
    # correct -- and the report names WHICH one matched, so the ambiguity is
    # recorded rather than quietly resolved.
    def rank(s):
        return (-(s["completeness"] or 0.0), s["modeled_repair_minutes"], -s["correctness"])

    best = sorted(scored, key=lambda s: rank(s) + (s["variant_id"],))[0]
    # If two variants score identically the output did not discriminate between
    # them. Report that rather than letting the variant_id sort decide quietly:
    # a silently resolved ambiguity is exactly what this case class exists to
    # catch, and the tie-break is not evidence about which reading was used.
    tied = [s["variant_id"] for s in scored if rank(s) == rank(best)]
    tied_variants = sorted(tied) if len(tied) > 1 else []

    measured = run.get("recorded_repair_minutes")
    if measured is None:
        repair_basis, repair_used = "MODELED", best["modeled_repair_minutes"]
    else:
        repair_basis, repair_used = "MEASURED", measured

    generation = run.get("generation_minutes")
    from_scratch = task.get("from_scratch_minutes")
    if from_scratch is None or generation is None:
        net_saved, time_basis = None, UNKNOWN
    else:
        net_saved, time_basis = from_scratch - (generation + repair_used), repair_basis

    base.update({
        "status": "SCORED",
        "matched_variant": best["variant_id"],
        "variant_label": best["variant_label"],
        "tied_variants": tied_variants,
        # flat form for the CSV column; None (not the empty string) when there is
        # no tie, so "no tie" and "tie with an empty list" cannot be confused.
        "tied_variants_text": ";".join(tied_variants) or None,
        "required_total": best["required_total"],
        "required_hit": best["required_hit"],
        "completeness": best["completeness"],
        "forbidden_fired": best["forbidden_fired"],
        "correctness": best["correctness"],
        "modeled_repair_minutes": best["modeled_repair_minutes"],
        "measured_repair_minutes": measured,
        "repair_basis": repair_basis,
        "repair_minutes_used": repair_used,
        "generation_minutes": generation,
        "net_minutes_saved": net_saved,
        "time_basis": time_basis,
        "hit_ids": best["hit_ids"], "missed_ids": best["missed_ids"],
        "forbidden_ids": best["forbidden_ids"],
        "forbidden_reasons": best["forbidden_reasons"],
        "reviewer": run.get("reviewer"),
        "reviewer_note": run.get("note"),
        "analyst_followup": run.get("analyst_followup"),
        "review_locator": run.get("review_locator"),
    })
    return base


def _mean(values):
    return round(sum(values) / len(values), 4) if values else None


def score_workflow(dataset, runs_doc):
    by_id = {r["task_id"]: r for r in runs_doc["runs"]}
    results = [score_task(t, by_id.get(t["task_id"])) for t in dataset["tasks"]]
    scored = [r for r in results if r["status"] == "SCORED"]
    not_run = [r["task_id"] for r in results if r["status"] == "NOT_RUN"]

    measured = [r for r in scored if r["measured_repair_minutes"] is not None]
    timed = [r for r in scored if r["net_minutes_saved"] is not None]

    by_class = {}
    for case_class in CASE_CLASSES:
        rows = [r for r in scored if r["case_class"] == case_class]
        by_class[case_class] = {
            "scored": len(rows),
            "completeness_mean": _mean([r["completeness"] for r in rows]),
            "correctness_mean": _mean([r["correctness"] for r in rows]),
            "modeled_repair_total": sum(r["modeled_repair_minutes"] for r in rows),
            "forbidden_fires": sum(r["forbidden_fired"] for r in rows),
        }

    by_family = {}
    for family in sorted({t["family"] for t in dataset["tasks"]}):
        rows = [r for r in scored if r["family"] == family]
        by_family[family] = {
            "scored": len(rows),
            "completeness_mean": _mean([r["completeness"] for r in rows]),
            "correctness_mean": _mean([r["correctness"] for r in rows]),
            "modeled_repair_total": sum(r["modeled_repair_minutes"] for r in rows),
        }

    return {
        "workflow_id": runs_doc["workflow_id"],
        "workflow_label": runs_doc.get("workflow_label", ""),
        "environment": runs_doc.get("environment", ""),
        "results": results,
        "summary": {
            "tasks_total": len(dataset["tasks"]),
            "tasks_scored": len(scored),
            "tasks_not_run": not_run,
            "completeness_mean": _mean([r["completeness"] for r in scored]),
            "correctness_mean": _mean([r["correctness"] for r in scored]),
            # Measured and modeled repair are reported side by side and NEVER
            # averaged together: one is an observation, the other is the answer
            # key's estimate, and mixing them launders the difference.
            "repair_measured_total": sum(r["measured_repair_minutes"] for r in measured),
            "repair_measured_tasks": [r["task_id"] for r in measured],
            "repair_not_measured_tasks": [
                r["task_id"] for r in scored if r["measured_repair_minutes"] is None
            ],
            "repair_modeled_total_all_scored": sum(
                r["modeled_repair_minutes"] for r in scored
            ),
            "forbidden_fires_total": sum(r["forbidden_fired"] for r in scored),
            "undiscriminated_ambiguous_tasks": [
                r["task_id"] for r in scored if r.get("tied_variants")
            ],
            "abstention_failures": [
                r["task_id"] for r in scored
                if r["case_class"] == "missing_information" and r["required_hit"] == 0
            ],
            "generation_minutes_total_timed": sum(r["generation_minutes"] for r in timed),
            "from_scratch_minutes_total_timed": sum(r["from_scratch_minutes"] for r in timed),
            "repair_minutes_used_total_timed": sum(r["repair_minutes_used"] for r in timed),
            "net_minutes_saved_timed": sum(r["net_minutes_saved"] for r in timed),
            "timed_tasks": [r["task_id"] for r in timed],
            "time_unknown_tasks": [
                r["task_id"] for r in scored if r["net_minutes_saved"] is None
            ],
            "by_case_class": by_class,
            "by_family": by_family,
        },
    }


def compare(left, right):
    """Paired comparison on the tasks BOTH workflows actually scored.

    A task only one side ran is unpaired and excluded.  Filling it with a zero
    would flatter whichever side skipped it, which is the failure this whole
    kit exists to avoid.
    """
    lmap = {r["task_id"]: r for r in left["results"] if r["status"] == "SCORED"}
    rmap = {r["task_id"]: r for r in right["results"] if r["status"] == "SCORED"}
    paired = sorted(set(lmap) & set(rmap))
    unpaired = sorted(set(lmap) ^ set(rmap))

    def agg(m, key):
        return _mean([m[t][key] for t in paired])

    def total(m, key):
        return sum(m[t][key] for t in paired)

    timed = [t for t in paired
             if lmap[t]["net_minutes_saved"] is not None
             and rmap[t]["net_minutes_saved"] is not None]

    return {
        "left_workflow": left["workflow_id"],
        "right_workflow": right["workflow_id"],
        "paired_tasks": paired,
        "unpaired_tasks_excluded": unpaired,
        "completeness_mean": {left["workflow_id"]: agg(lmap, "completeness"),
                              right["workflow_id"]: agg(rmap, "completeness")},
        "correctness_mean": {left["workflow_id"]: agg(lmap, "correctness"),
                             right["workflow_id"]: agg(rmap, "correctness")},
        "modeled_repair_total": {left["workflow_id"]: total(lmap, "modeled_repair_minutes"),
                                 right["workflow_id"]: total(rmap, "modeled_repair_minutes")},
        "forbidden_fires": {left["workflow_id"]: total(lmap, "forbidden_fired"),
                            right["workflow_id"]: total(rmap, "forbidden_fired")},
        "timed_tasks": timed,
        "generation_minutes": {
            left["workflow_id"]: sum(lmap[t]["generation_minutes"] for t in timed),
            right["workflow_id"]: sum(rmap[t]["generation_minutes"] for t in timed)},
        "repair_minutes_used": {
            left["workflow_id"]: sum(lmap[t]["repair_minutes_used"] for t in timed),
            right["workflow_id"]: sum(rmap[t]["repair_minutes_used"] for t in timed)},
        "net_minutes_saved": {
            left["workflow_id"]: sum(lmap[t]["net_minutes_saved"] for t in timed),
            right["workflow_id"]: sum(rmap[t]["net_minutes_saved"] for t in timed)},
        "note": ("Four measures, reported separately. This kit deliberately emits no "
                 "single composite usefulness score: the reader has to see the trade "
                 "between speed and repair, not a number that hides it."),
    }


# ------------------------------------------------------------- validation ---

def validate_dataset(dataset):
    """Structural checks on the answer keys.  Returns a list of problems."""
    problems = []
    seen = set()
    for task in dataset["tasks"]:
        tid = task["task_id"]
        if tid in seen:
            problems.append(f"{tid}: duplicate task_id")
        seen.add(tid)
        if task["case_class"] not in CASE_CLASSES:
            problems.append(f"{tid}: unknown case_class {task['case_class']!r}")
        if not task.get("answer_variants"):
            problems.append(f"{tid}: no answer variants")
        for source in task.get("context", []):
            try:
                ix._parse_date(source["as_of"])
            except ix.InterchangeError as exc:
                problems.append(f"{tid}: context source {source['source_id']}: {exc}")
        for variant in task.get("answer_variants", []):
            if not variant.get("required"):
                problems.append(f"{tid}/{variant['variant_id']}: no required elements")
            for element in list(variant.get("required", [])) + list(variant.get("forbidden", [])):
                if not (element.get("all_of") or element.get("any_of")):
                    problems.append(
                        f"{tid}/{variant['variant_id']}/{element['element_id']}: no match terms")
        if task["case_class"] == "missing_information":
            ids = {e["element_id"] for v in task["answer_variants"] for e in v["required"]}
            if "E-ABSTAIN" not in ids:
                problems.append(
                    f"{tid}: a missing_information task must require an abstention element")
            if not any(v.get("forbidden") for v in task["answer_variants"]):
                problems.append(
                    f"{tid}: a missing_information task must forbid the fabrication it invites")
        # Repair-cost asymmetry: catching a confident wrong statement costs more
        # than noticing an omission.  If a dataset inverts that, the ranking it
        # produces is wrong in a way no test downstream will notice.
        for variant in task.get("answer_variants", []):
            req = [e.get("repair_minutes", 0) for e in variant.get("required", [])]
            for forbidden in variant.get("forbidden", []):
                if req and forbidden.get("repair_minutes", 0) <= max(req):
                    problems.append(
                        f"{tid}/{variant['variant_id']}/{forbidden['element_id']}: forbidden "
                        "repair cost is not greater than the most expensive required element")
    return problems


# ----------------------------------------------------------------- output ---

def _csv_rows(scored_workflows):
    rows = []
    for workflow in scored_workflows:
        for result in workflow["results"]:
            row = {name: result.get(name) for name, _ in RESULT_COLUMNS}
            row["tied_variants"] = result.get("tied_variants_text")
            row["workflow_id"] = workflow["workflow_id"]
            rows.append(row)
    return rows


def _fmt(value, unknown=UNKNOWN):
    return unknown if value is None else value


def write_report(path, dataset, workflows, comparison, export_warnings):
    with open(path, "w", encoding="utf-8") as fh:
        w = fh.write
        w("# AI usefulness evaluation — results\n\n")
        w("**UIOWA-075 preparation artifact. Every task, output, reviewer and locator below "
          "is FICTION** invented for this kit. Nothing here is a University of Iowa finding, "
          "system, document or person.\n\n")
        w("## What was measured\n\n")
        w("Four measures, kept separate on purpose:\n\n")
        w("- **Correctness** — of what the output asserted, how much was right "
          "(precision against the answer key).\n")
        w("- **Completeness** — of what the answer key requires, how much the output covered.\n")
        w("- **Repair time** — minutes to make the output usable. Reported as **MEASURED** where "
          "an operator timed it and **MODELED** where the answer key's repair costs were used. "
          "The two are never averaged together.\n")
        w("- **Usefulness** — expressed as net minutes saved against an explicit "
          "`from_scratch_minutes` assumption, not as an opinion. Where that assumption or the "
          "generation time is absent, the task's usefulness is `UNKNOWN` and it leaves the "
          "total.\n\n")
        w("No model is called by this kit. It scores recorded outputs. "
          "**It produces no single composite score and does not rate any individual.**\n\n")

        for workflow in workflows:
            s = workflow["summary"]
            w(f"## Workflow: `{workflow['workflow_id']}`\n\n")
            w(f"{workflow['workflow_label']}\n\n")
            w(f"> {workflow['environment']}\n\n")
            ix.write_markdown_table(fh, ["Measure", "Value", "Basis"], [
                ["Tasks scored", f"{s['tasks_scored']} of {s['tasks_total']}", "—"],
                ["Tasks NOT_RUN (excluded from every denominator)",
                 ", ".join(s["tasks_not_run"]) or "none", "—"],
                ["Completeness (mean)", _fmt(s["completeness_mean"]), "answer key"],
                ["Correctness (mean)", _fmt(s["correctness_mean"]), "answer key"],
                ["Repair minutes — measured subtotal", s["repair_measured_total"],
                 f"MEASURED on {len(s['repair_measured_tasks'])} task(s)"],
                ["Repair minutes — modeled, all scored tasks",
                 s["repair_modeled_total_all_scored"], "MODELED from answer key"],
                ["Tasks with no measured repair time",
                 ", ".join(s["repair_not_measured_tasks"]) or "none", "UNKNOWN"],
                ["Forbidden-element fires (wrong/invented/stale assertions)",
                 s["forbidden_fires_total"], "answer key"],
                ["Missing-information tasks where the output did NOT abstain",
                 ", ".join(s["abstention_failures"]) or "none", "answer key"],
                ["Generation minutes (timed tasks)", s["generation_minutes_total_timed"], "recorded"],
                ["Repair minutes used (timed tasks)", s["repair_minutes_used_total_timed"],
                 "measured where available, else modeled"],
                ["From-scratch minutes (timed tasks)", s["from_scratch_minutes_total_timed"],
                 "stated assumption"],
                ["**Net minutes saved (timed tasks)**", s["net_minutes_saved_timed"], "derived"],
                ["Tasks with UNKNOWN time inputs (excluded)",
                 ", ".join(s["time_unknown_tasks"]) or "none", "UNKNOWN"],
            ])
            w("\n### By case class\n\n")
            ix.write_markdown_table(
                fh, ["Case class", "Scored", "Completeness", "Correctness",
                     "Modeled repair (min)", "Forbidden fires"],
                [[c, s["by_case_class"][c]["scored"],
                  _fmt(s["by_case_class"][c]["completeness_mean"]),
                  _fmt(s["by_case_class"][c]["correctness_mean"]),
                  s["by_case_class"][c]["modeled_repair_total"],
                  s["by_case_class"][c]["forbidden_fires"]] for c in CASE_CLASSES])
            w("\n### Per task\n\n")
            ix.write_markdown_table(
                fh, ["Task", "Class", "Status", "Variant", "Compl.", "Corr.",
                     "Repair (min)", "Basis", "Net saved (min)", "Fired", "Tied"],
                [[r["task_id"], r["case_class"], r["status"], _fmt(r["matched_variant"], "—"),
                  _fmt(r["completeness"]), _fmt(r["correctness"]),
                  _fmt(r["repair_minutes_used"]), r["repair_basis"],
                  _fmt(r["net_minutes_saved"]), ", ".join(r["forbidden_ids"]) or "—",
                  ", ".join(r.get("tied_variants") or []) or "—"]
                 for r in workflow["results"]])
            w("\n")

        w("## Paired comparison\n\n")
        w(f"Paired on the {len(comparison['paired_tasks'])} tasks both workflows scored. ")
        w(f"Excluded as unpaired: {', '.join(comparison['unpaired_tasks_excluded']) or 'none'} — "
          "not zero-filled.\n\n")
        left, right = comparison["left_workflow"], comparison["right_workflow"]
        ix.write_markdown_table(fh, ["Measure", left, right], [
            ["Completeness (mean)", _fmt(comparison["completeness_mean"][left]),
             _fmt(comparison["completeness_mean"][right])],
            ["Correctness (mean)", _fmt(comparison["correctness_mean"][left]),
             _fmt(comparison["correctness_mean"][right])],
            ["Modeled repair total (min)", comparison["modeled_repair_total"][left],
             comparison["modeled_repair_total"][right]],
            ["Forbidden fires", comparison["forbidden_fires"][left],
             comparison["forbidden_fires"][right]],
            ["Generation minutes (timed)", comparison["generation_minutes"][left],
             comparison["generation_minutes"][right]],
            ["Repair minutes used (timed)", comparison["repair_minutes_used"][left],
             comparison["repair_minutes_used"][right]],
            ["Net minutes saved (timed)", comparison["net_minutes_saved"][left],
             comparison["net_minutes_saved"][right]],
        ])
        w(f"\n{comparison['note']}\n\n")

        w("## What this result does NOT say\n\n")
        w("- It does not say either workflow is approved, certified or compliant.\n")
        w("- It does not rank any analyst. The unit of measurement is a workflow.\n")
        w("- It does not generalize past these 12 fictional tasks. A different task mix, "
          "especially a different share of missing-information cases, moves the answer.\n")
        w("- Where an input was absent it stayed `UNKNOWN`. No absent value was read as a zero, "
          "a pass, or a maturity rating.\n\n")

        w("## Export warnings\n\n")
        if export_warnings:
            ix.write_markdown_table(fh, ["Row", "Field", "Warning"],
                                    [[x["row"], x["field"], x["warning"]] for x in export_warnings])
            w("\nThese values were neutralized for spreadsheet safety on CSV export and are "
              "restored exactly on import. They were flagged, not silently changed.\n")
        else:
            w("None.\n")


def build(dataset_path, run_paths, out_dir):
    dataset = ix.read_json(dataset_path)
    problems = validate_dataset(dataset)
    if problems:
        raise SystemExit("dataset validation failed:\n  " + "\n  ".join(problems))

    workflows = [score_workflow(dataset, ix.read_json(p)) for p in run_paths]
    comparison = compare(workflows[0], workflows[1]) if len(workflows) >= 2 else None

    os.makedirs(out_dir, exist_ok=True)
    rows = _csv_rows(workflows)
    csv_path = os.path.join(out_dir, "results.csv")
    warnings = ix.write_csv(csv_path, RESULT_COLUMNS, rows)

    ix.write_json(os.path.join(out_dir, "results.json"), {
        "dataset_id": dataset["dataset_id"],
        "fiction_notice": dataset["fiction_notice"],
        "workflows": workflows,
        "comparison": comparison,
        "export_warnings": warnings,
    })
    ix.write_json(os.path.join(out_dir, "schema.json"), {
        "note": ("Column dictionary for results.csv. NULL (never recorded) is the sentinel "
                 "\\N; an empty field is the empty string; a literal 'NA' is the two "
                 "characters NA. A leading apostrophe is an export-safety marker and is "
                 "removed on import."),
        "null_sentinel": ix.NULL_TOKEN,
        "columns": [{"name": n, "kind": k} for n, k in RESULT_COLUMNS],
    })
    write_report(os.path.join(out_dir, "report.md"), dataset, workflows, comparison, warnings)

    artifacts = ["results.csv", "results.json", "schema.json", "report.md"]
    digests = {name: ix.digest_file(os.path.join(out_dir, name)) for name in artifacts}
    ix.write_json(os.path.join(out_dir, "digests.json"), {"artifacts": digests})
    return workflows, comparison, warnings, digests


# -------------------------------------------------------------------- CLI ---

def _default_paths(root):
    return (os.path.join(root, "data", "tasks.json"),
            [os.path.join(root, "data", "runs_assisted.json"),
             os.path.join(root, "data", "runs_manual.json")])


def main(argv=None):
    root = os.path.dirname(os.path.abspath(__file__))
    tasks_default, runs_default = _default_paths(root)

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["validate", "report", "check-digest"])
    parser.add_argument("--tasks", default=tasks_default)
    parser.add_argument("--runs", nargs="+", default=runs_default)
    parser.add_argument("--out", default=os.path.join(root, "examples"))
    args = parser.parse_args(argv)

    if args.command == "validate":
        problems = validate_dataset(ix.read_json(args.tasks))
        if problems:
            print("DATASET PROBLEMS:")
            for p in problems:
                print("  -", p)
            return 1
        print("dataset OK")
        return 0

    if args.command == "report":
        workflows, comparison, warnings, digests = build(args.tasks, args.runs, args.out)
        for workflow in workflows:
            s = workflow["summary"]
            print(f"{workflow['workflow_id']}: scored {s['tasks_scored']}/{s['tasks_total']}"
                  f"  completeness={s['completeness_mean']}  correctness={s['correctness_mean']}"
                  f"  forbidden_fires={s['forbidden_fires_total']}"
                  f"  net_saved_timed={s['net_minutes_saved_timed']}min"
                  f"  NOT_RUN={s['tasks_not_run'] or 'none'}"
                  f"  time_UNKNOWN={s['time_unknown_tasks'] or 'none'}")
        if comparison:
            print(f"paired on {len(comparison['paired_tasks'])} tasks; "
                  f"unpaired excluded: {comparison['unpaired_tasks_excluded'] or 'none'}")
        print(f"export warnings: {len(warnings)}")
        for name, digest in sorted(digests.items()):
            print(f"  {digest}  {name}")
        return 0

    if args.command == "check-digest":
        stored = ix.read_json(os.path.join(args.out, "digests.json"))["artifacts"]
        tmp = tempfile.mkdtemp(prefix="evalkit-digest-")
        try:
            _, _, _, fresh = build(args.tasks, args.runs, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        bad = [n for n in sorted(stored) if stored[n] != fresh.get(n)]
        if bad:
            print("DIGEST MISMATCH on: " + ", ".join(bad))
            return 1
        print(f"digests match ({len(stored)} artifacts) — a second operator gets identical bytes")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
