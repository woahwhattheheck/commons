"""Command line for the uncertainty-language lint. Stdlib only, no network.

    python3 cli.py scan <dir>          # findings + class breakdown
    python3 cli.py scan <dir> --json
    python3 cli.py scan <dir> --all    # show every candidate, not just flags
    python3 cli.py score               # precision/recall vs the labelled set
    python3 cli.py explain             # what each class means

Exit codes: 0 when nothing is flagged, 1 when something is. Advisory by
design -- wire it into a lane's own check if that lane's owner wants it, never
as a gate on someone else's work.
"""

import json
import os
import sys
import textwrap

import lint

WIDTH = 78
CLASS_HELP = {
    lint.FLAG_ASSESSED_ENTITY:
        "FLAGGED. The absence is stated as a property of an assessed entity. "
        "Rewrite it as a property of the search.",
    lint.OK_EVIDENCE_SUBJECT:
        "ok. The subject is the evidence, the assessment or the search -- "
        "this is the correct form.",
    lint.OK_TOOL_SUBJECT:
        "ok. The subject is software, a record, a document or a fixture, not "
        "an assessed entity.",
    lint.OK_HEDGED:
        "ok. Hedged or conditional, so it asserts nothing.",
    lint.OK_QUOTED:
        "ok. The phrase is quoted -- usually the lane demonstrating the "
        "wording it forbids.",
    lint.OK_UNCLASSIFIED:
        "ok. No assessed entity found near the predicate. The default is to "
        "pass: a tool that guesses when unsure is the noisy grep again.",
}


def wrap(text, indent=""):
    return textwrap.fill(text, width=WIDTH, initial_indent=indent,
                         subsequent_indent=indent)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    here = os.path.dirname(os.path.abspath(__file__))

    if cmd == "explain":
        for name, help_text in CLASS_HELP.items():
            print(name)
            print(wrap(help_text, indent="    "))
            print()
        return 0

    if cmd == "score":
        path = os.path.join(here, "fixtures", "labelled_lines.json")
        data = lint.load_labelled(path)
        overall = lint.score_against_labels(data)
        print("PRECISION / RECALL vs hand-labelled lines")
        print("-" * WIDTH)
        for origin in ("corpus", "constructed"):
            subset = {"lines": [l for l in data["lines"]
                                if l["origin"] == origin]}
            s = lint.score_against_labels(subset)
            print("%-12s n=%-4d tp=%-3d fp=%-3d fn=%-3d tn=%-3d  "
                  "precision=%.2f recall=%.2f"
                  % (origin, len(subset["lines"]), s["true_positive"],
                     s["false_positive"], s["false_negative"],
                     s["true_negative"], s["precision"], s["recall"]))
        print("-" * WIDTH)
        print("%-12s n=%-4d tp=%-3d fp=%-3d fn=%-3d tn=%-3d  "
              "precision=%.2f recall=%.2f"
              % ("overall", len(data["lines"]), overall["true_positive"],
                 overall["false_positive"], overall["false_negative"],
                 overall["true_negative"], overall["precision"],
                 overall["recall"]))
        for kind, text in overall["errors"]:
            print(wrap("%s: %s" % (kind, text), indent="  "))
        return 0 if not overall["errors"] else 1

    if cmd == "scan":
        if len(argv) < 3:
            print(__doc__)
            return 2
        root = argv[2]
        findings = lint.scan_tree(root)
        findings = [f for f in findings if "uncertainty_lint" not in f.path]
        flagged = [f for f in findings if f.klass == lint.FLAG_ASSESSED_ENTITY]
        summary = lint.summarise(findings)

        if "--json" in argv:
            print(json.dumps({"summary": summary,
                              "findings": [f.as_dict() for f in
                                           (findings if "--all" in argv
                                            else flagged)]}, indent=2))
            return 1 if flagged else 0

        print("UNCERTAINTY-LANGUAGE SCAN  %s" % root)
        print("-" * WIDTH)
        print("candidates examined : %d" % summary["candidates_examined"])
        print("flagged             : %d  (%.2f%% of candidates)"
              % (summary["flagged"], summary["flag_rate"] * 100))
        print("-" * WIDTH)
        for klass, count in summary["by_class"].items():
            print("  %-42s %4d" % (klass, count))
        print("-" * WIDTH)
        shown = findings if "--all" in argv else flagged
        if not shown:
            print("Nothing flagged. Note this is not a clean bill of health: "
                  "see\nthe documented limitation on existential phrasing in "
                  "lint.py and README.md.")
        for f in shown:
            print("%s:%d  [%s]" % (f.path, f.line_no, f.klass))
            print(wrap(f.text, indent="    "))
            if f.klass == lint.FLAG_ASSESSED_ENTITY:
                print(wrap("subject read as: %s" % f.subject, indent="    "))
                print(wrap("suggestion: " + lint.SUGGESTION, indent="    "))
            print()
        return 1 if flagged else 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
