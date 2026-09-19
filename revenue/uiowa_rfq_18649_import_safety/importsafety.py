"""Command line for the import-safety audit. Stdlib only, no network.

    python3 importsafety.py scan <kit-root>
    python3 importsafety.py scan <kit-root> --json
    python3 importsafety.py reproduce                 # fixture lanes
    python3 importsafety.py reproduce <A> <B> <mod>   # two real lanes

Named `importsafety.py` rather than `cli.py` deliberately: `cli` is already one
of the colliding names this tool reports, and adding a third holder of it would
be a poor advertisement.

Exit codes: 0 no ACTIVE_RISK collision, 1 at least one, 2 usage error.
"""

import json
import os
import sys
import textwrap

import reproduce as reproduce_mod
import scan as scan_mod

WIDTH = 78


def wrap(text, indent=""):
    return textwrap.fill(text, width=WIDTH, initial_indent=indent,
                         subsequent_indent=indent)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]

    if cmd == "reproduce":
        return reproduce_mod.main(["reproduce"] + list(argv[2:]))

    if cmd == "scan":
        if len(argv) < 3:
            print(__doc__)
            return 2
        root = argv[2]
        result = scan_mod.survey(root)
        found = scan_mod.collisions(result)
        summary = scan_mod.summarise(result, found)
        active = [c for c in found if c.risk == scan_mod.ACTIVE_RISK]

        if "--json" in argv:
            print(json.dumps({"summary": summary,
                              "collisions": [c.as_dict() for c in found]},
                             indent=2))
            return 1 if active else 0

        print("IMPORT-SAFETY SCAN  %s" % root)
        print("-" * WIDTH)
        s = summary["survey"]
        print("lanes                        : %d" % s["lanes"])
        print("lanes shipping __init__.py   : %d" % s["packaged_lanes"])
        print("files mutating sys.path      : %d" % s["path_mutating_files"])
        print("distinct top-level modules   : %d"
              % s["distinct_top_level_modules"])
        print("files unreadable/unparsable  : %d" % s["unparsable_files"])
        print("-" * WIDTH)
        print("colliding module names       : %d" % summary["collisions"])
        for risk, count in summary["by_risk"].items():
            print("  %-26s %d" % (risk, count))
        print("test-module collisions       : %d"
              % summary["test_module_collisions"])
        print("-" * WIDTH)
        if not found:
            print("No colliding module names.")
        for c in found:
            print("%-16s %s" % (c.module_name, c.risk))
            print(wrap("held by: " + ", ".join(c.lanes), indent="    "))
            print(wrap(c.reason, indent="    "))
            print()
        if active:
            print(wrap(
                "Remediation that edits no lane: load lane modules through "
                "safe_import.load(lane_dir, module_name), which registers "
                "them as uiowa_lane.<lane>.<module>. No file needs renaming."))
        return 1 if active else 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
