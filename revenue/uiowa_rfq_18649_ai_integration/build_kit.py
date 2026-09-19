"""Generate the full UIOWA-080 deliverable kit into out/.

Run:  python3 build_kit.py

Deterministic: same inputs -> byte-identical outputs, so a reviewer can diff two
runs and see only what actually changed. No network, stdlib only.
"""

import json
import os
import sys

import kit_status
import patterns as patterns_mod
import portability
import worksheet as worksheet_mod
from demo_swap import build_receipt

OUT = "out"
WORKFLOWS = os.path.join("data", "workflows.json")


def _write(name, text):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path, len(text)


def score_inventories(workflows):
    """Score every declared inventory. Malformed counts are OBSERVABLE, not fatal.

    portability.swap_blast_radius() raises on a non-integer count on purpose -- the
    API should fail loudly rather than coerce. At kit level that has to become a
    reported data-quality finding instead of a crash, so a bad row in one fixture
    cannot silently stop the other three from being assessed.
    """
    scores, rejected = [], []
    for workflow in workflows:
        inventory = workflow.get("code_surface_inventory", {})
        try:
            scores.append(portability.swap_blast_radius(
                inventory, system_id=workflow["workflow_id"]))
        except ValueError as exc:
            rejected.append({"workflow_id": workflow["workflow_id"],
                             "error": str(exc),
                             "handling": "inventory rejected; the workflow keeps NO "
                                         "portability score. It is not scored as zero "
                                         "and not scored as contained."})
    return scores, rejected


def main():
    os.makedirs(OUT, exist_ok=True)
    workflows = worksheet_mod.load_workflows(WORKFLOWS)
    written = []

    patterns_md = patterns_mod.render_patterns_markdown()
    written.append(_write("reference_patterns.md", patterns_md))

    evaluations = [worksheet_mod.evaluate(w) for w in workflows]
    worksheet_md = worksheet_mod.render_worksheet_markdown(evaluations)
    written.append(_write("integration_decision_worksheet.md", worksheet_md))
    written.append(_write("integration_decision_worksheet.csv",
                          worksheet_mod.render_worksheet_csv(evaluations)))
    written.append(_write("worksheet_evaluations.json",
                          json.dumps(evaluations, indent=2, sort_keys=True) + "\n"))

    scores, rejected = score_inventories(workflows)
    written.append(_write("portability_blast_radius.md",
                          portability.render_portability_markdown(scores)))
    written.append(_write("portability_scores.json",
                          json.dumps({"scores": scores,
                                      "rejected_inventories": rejected},
                                     indent=2, sort_keys=True) + "\n"))

    receipt = build_receipt()
    written.append(_write("swap_receipt.json",
                          json.dumps(receipt, indent=2, sort_keys=True) + "\n"))

    # Vendor-neutrality tripwire over every text artifact we just produced.
    neutrality = {}
    for name, text in (("reference_patterns.md", patterns_md),
                       ("integration_decision_worksheet.md", worksheet_md),
                       ("portability_blast_radius.md",
                        portability.render_portability_markdown(scores))):
        neutrality[name] = patterns_mod.check_vendor_neutrality(
            text, patterns_mod.declared_capability_classes())
    written.append(_write("neutrality_check.json",
                          json.dumps(neutrality, indent=2, sort_keys=True) + "\n"))

    print("UIOWA-080 kit written to out/")
    for path, size in written:
        print(f"  {path:<46} {size:>7} bytes")

    print("\nWorksheet verdicts")
    for evaluation in evaluations:
        fits = ", ".join(f"{p.split('_')[0]}={evaluation['patterns'][p]['fit']}"
                         for p in patterns_mod.PATTERN_ORDER)
        print(f"  {evaluation['workflow_id']:<18} {fits}")
        if evaluation["unanswered_questions"]:
            print(f"{'':<20}UNKNOWN: "
                  f"{', '.join(evaluation['unanswered_questions'])}")
        if evaluation["invalid_answers_discarded"]:
            print(f"{'':<20}discarded: "
                  f"{'; '.join(evaluation['invalid_answers_discarded'])}")

    print("\nPortability (provider-swap blast radius)")
    for score in scores:
        floor = " (FLOOR, incomplete inventory)" if score["total_is_floor"] else ""
        print(f"  {score['system_id']:<18} {score['edit_points']:>3} edit points  "
              f"{score['band']}{floor}")
    for item in rejected:
        print(f"  {item['workflow_id']:<18} NOT SCORED - {item['error']}")

    failures = sum(v["finding_count"] for v in neutrality.values())
    print(f"\nVendor-neutrality tripwire over generated artifacts: "
          f"{failures} finding(s)")
    if failures:
        print("  ARTIFACTS CONTAIN PROCUREMENT/PRODUCT LANGUAGE - review before use")

    # Signal the result to whoever ran this, rather than leaving it in stdout for a
    # human to notice. A rejected inventory and a neutrality hit both need action;
    # an incomplete inventory or an UNDETERMINED pattern verdict is unresolved
    # evidence, which is INDETERMINATE and must not be reported as a clean run.
    findings = failures + len(rejected)
    unresolved = sum(1 for score in scores if score["total_is_floor"])
    unresolved += sum(1 for evaluation in evaluations
                      if any(evaluation["patterns"][pattern_id]["fit"] == "UNDETERMINED"
                             for pattern_id in patterns_mod.PATTERN_ORDER))
    return kit_status.emit("build_kit", findings=findings, indeterminate=unresolved,
                           note=f"{failures} neutrality finding(s), "
                                f"{len(rejected)} rejected inventory(ies), "
                                f"{unresolved} unresolved item(s)")


if __name__ == "__main__":
    sys.exit(main())
