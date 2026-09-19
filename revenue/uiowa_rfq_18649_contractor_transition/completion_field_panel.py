#!/usr/bin/env python3
"""Execute the retained 264-case synthetic completion-field regression panel.

This is a developer verification tool using the existing test packet, not a
production assessment or a new classifier. No network or source-file writes.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile

import transition
from test_completion_integrity import packet


def run():
    base = packet()
    values = [None, "", " ", "UNKNOWN", 0, True, [], {},
              ["SYN-APP-001"], {"unrecognized": "shape"}]
    results = {"cases": 0, "controlled_bad_input": 0, "classified": 0,
               "exceptions": [], "closed_with_issues": [],
               "python_optimized": bool(sys.flags.optimize)}
    control, control_issues = transition.build(copy.deepcopy(base))
    results["clean_control_closed"] = control.transition_closed() and not control_issues
    with tempfile.TemporaryDirectory(prefix="transition-field-panel-") as tmp:
        for section in ("people", "applications", "access_changes"):
            for position, record in enumerate(base[section]):
                for field in record:
                    for number in range(len(values) + 1):
                        data = copy.deepcopy(base)
                        name = "%s[%d].%s=value%d" % (section, position, field, number)
                        if number == len(values):
                            del data[section][position][field]
                            name = "%s[%d].%s=MISSING" % (section, position, field)
                        else:
                            data[section][position][field] = copy.deepcopy(values[number])
                        results["cases"] += 1
                        try:
                            report, issues = transition.build(data)
                            json.dumps(report.as_dict())
                            transition.render_markdown(report)
                            transition.write_csv(report, str(Path(tmp) / "report.csv"))
                            results["classified"] += 1
                            if report.transition_closed() and issues:
                                results["closed_with_issues"].append(name)
                        except ValueError:
                            results["controlled_bad_input"] += 1
                        except Exception as exc:
                            results["exceptions"].append({"case": name,
                                "exception": type(exc).__name__, "message": str(exc)})
    return results


def main():
    result = run()
    result["matched"] = (result["clean_control_closed"]
        and result["cases"] == 264 and result["classified"] == 240
        and result["controlled_bad_input"] == 24
        and not result["exceptions"] and not result["closed_with_issues"])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["matched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
