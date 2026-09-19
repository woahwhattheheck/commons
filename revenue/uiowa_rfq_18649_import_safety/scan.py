"""Read-only audit of module-name collisions across the assembled kit.

Reports a collision, its risk class, and nothing else. It does not edit a lane,
rename a module, score a lane, or rank an author. A collision is a property of
the assembled kit, not a defect in either lane that holds the name -- both are
correct on their own, which is why no single lane can see this.

Risk classes
------------
ACTIVE_RISK   Two or more lanes hold the name AND at least one file in the kit
              uses the `sys.path.insert` pattern that makes bare module names
              global. Loading both lanes in one process gives the second one
              the first one's file.
LATENT        The name is shared, but nothing in the kit currently loads lanes
              into a shared namespace. Not a defect today. Reported so it is
              visible before something starts composing lanes, not after.
UNKNOWN       Could not be determined -- for example a module that mutates
              sys.path at import time, whose resolution depends on run order.
              Never reported as clean.
"""

import ast
import os
import re

ACTIVE_RISK = "ACTIVE_RISK"
LATENT = "LATENT"
UNKNOWN = "UNKNOWN"

_PATH_MUTATION = re.compile(r"sys\.path\s*\.\s*(?:insert|append|extend)")


class Collision:
    def __init__(self, module_name, lanes, risk, reason):
        self.module_name = module_name
        self.lanes = lanes
        self.risk = risk
        self.reason = reason

    def as_dict(self):
        return {"module": self.module_name, "lanes": self.lanes,
                "risk": self.risk, "reason": self.reason}


class LaneSurvey:
    def __init__(self):
        self.lanes = []
        self.top_level_modules = {}
        self.test_modules = {}
        self.path_mutating_files = []
        self.packaged_lanes = []
        self.unparsable_files = []

    def as_dict(self):
        return {
            "lanes": len(self.lanes),
            "packaged_lanes": len(self.packaged_lanes),
            "path_mutating_files": len(self.path_mutating_files),
            "distinct_top_level_modules": len(self.top_level_modules),
            "unparsable_files": len(self.unparsable_files),
        }


def survey(root, lane_prefix="uiowa_rfq_18649_"):
    """Walk the kit. Pure inspection -- nothing is imported or executed."""
    result = LaneSurvey()
    if not os.path.isdir(root):
        return result
    for lane in sorted(os.listdir(root)):
        lane_dir = os.path.join(root, lane)
        if not lane.startswith(lane_prefix) or not os.path.isdir(lane_dir):
            continue
        result.lanes.append(lane)
        for dirpath, dirnames, filenames in os.walk(lane_dir):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                full = os.path.join(dirpath, name)
                stem = name[:-3]
                if name == "__init__.py":
                    if lane not in result.packaged_lanes:
                        result.packaged_lanes.append(lane)
                    continue
                if dirpath == lane_dir:
                    result.top_level_modules.setdefault(stem, []).append(lane)
                if stem.startswith("test_"):
                    result.test_modules.setdefault(stem, []).append(lane)
                try:
                    with open(full, "r", encoding="utf-8") as handle:
                        text = handle.read()
                except (OSError, UnicodeDecodeError):
                    result.unparsable_files.append(full)
                    continue
                if _PATH_MUTATION.search(text):
                    result.path_mutating_files.append(
                        os.path.relpath(full, root))
                try:
                    ast.parse(text)
                except SyntaxError:
                    result.unparsable_files.append(os.path.relpath(full, root))
    return result


def collisions(result):
    """Colliding names with a risk class. Non-colliding names are not output."""
    shared_namespace = bool(result.path_mutating_files)
    out = []
    for name, lanes in sorted(result.top_level_modules.items()):
        if len(lanes) < 2:
            continue
        if result.unparsable_files:
            risk, reason = UNKNOWN, (
                "%d file(s) in the kit could not be read or parsed, so whether "
                "this name is loaded into a shared namespace cannot be "
                "determined" % len(result.unparsable_files))
        elif shared_namespace:
            risk, reason = ACTIVE_RISK, (
                "%d file(s) use sys.path insertion, which makes bare module "
                "names global; loading these lanes in one process gives the "
                "later one the earlier one's file"
                % len(result.path_mutating_files))
        else:
            risk, reason = LATENT, (
                "the name is shared, but nothing in the kit loads lanes into "
                "a shared namespace, so nothing triggers it today")
        out.append(Collision(name, sorted(lanes), risk, reason))
    for name, lanes in sorted(result.test_modules.items()):
        if len(lanes) < 2:
            continue
        out.append(Collision(
            name, sorted(lanes), ACTIVE_RISK,
            "two lanes ship a test module with this name; `unittest discover` "
            "from a shared root imports one and skips the other"))
    return out


def summarise(result, found):
    counts = {}
    for c in found:
        counts[c.risk] = counts.get(c.risk, 0) + 1
    return {
        "survey": result.as_dict(),
        "collisions": len(found),
        "by_risk": dict(sorted(counts.items())),
        "colliding_files": sum(len(c.lanes) for c in found),
        "test_module_collisions": sum(
            1 for c in found if c.module_name.startswith("test_")),
    }
