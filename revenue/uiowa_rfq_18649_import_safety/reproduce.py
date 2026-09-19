"""Reproduce the shadowing failure, then show the scoped loader avoiding it.

Run against the two fixture lanes, or against two real lanes:

    python3 reproduce.py
    python3 reproduce.py <laneA> <laneB> <module>

The fixtures return DIFFERENT values on purpose. A demonstration where both
lanes raise, or where both return the same thing, cannot show this bug: the
failure is not an exception, it is the wrong module answering plausibly.
"""

import os
import sys

import safe_import

HERE = os.path.dirname(os.path.abspath(__file__))


def naive(lane_a, lane_b, module_name):
    """What 17 files in this kit currently do."""
    sys.path.insert(0, os.path.abspath(lane_a))
    first = __import__(module_name)
    sys.path.insert(0, os.path.abspath(lane_b))
    second = __import__(module_name)
    return first, second


def scoped(lane_a, lane_b, module_name):
    return (safe_import.load(lane_a, module_name),
            safe_import.load(lane_b, module_name))


def describe(module):
    return {"file": getattr(module, "__file__", None),
            "LANE": getattr(module, "LANE", None),
            "summary": (module.summary() if hasattr(module, "summary")
                        else None)}


def main(argv):
    if len(argv) >= 4:
        lane_a, lane_b, module_name = argv[1], argv[2], argv[3]
    else:
        lane_a = os.path.join(HERE, "fixtures", "lane_alpha")
        lane_b = os.path.join(HERE, "fixtures", "lane_beta")
        module_name = "report"

    saved_path, saved_modules = list(sys.path), dict(sys.modules)
    first, second = naive(lane_a, lane_b, module_name)
    a_naive, b_naive = describe(first), describe(second)
    shadowed = first is second
    sys.path[:] = saved_path
    sys.modules.clear()
    sys.modules.update(saved_modules)

    a_safe, b_safe = (describe(m) for m in scoped(lane_a, lane_b, module_name))

    print("NAIVE  sys.path.insert + import %s" % module_name)
    print("  lane A -> %s" % a_naive["file"])
    print("  lane B -> %s" % b_naive["file"])
    print("  SAME MODULE OBJECT: %s" % shadowed)
    print("  lane A says: %r" % a_naive["summary"])
    print("  lane B says: %r" % b_naive["summary"])
    print()
    print("SCOPED  safe_import.load")
    print("  lane A -> %s" % a_safe["file"])
    print("  lane B -> %s" % b_safe["file"])
    print("  SAME MODULE OBJECT: %s" % (a_safe["file"] == b_safe["file"]))
    print("  lane A says: %r" % a_safe["summary"])
    print("  lane B says: %r" % b_safe["summary"])
    print()
    if shadowed:
        print("RESULT: shadowing reproduced. The naive path returned lane A's "
              "module\n        for lane B's request, with no error raised.")
        return 1
    print("RESULT: no shadowing observed for this pair.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
