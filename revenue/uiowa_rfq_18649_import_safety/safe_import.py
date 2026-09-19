"""Load a lane's module under a lane-scoped name, so two lanes can coexist.

The problem
-----------
58 of 59 landed lanes ship no `__init__.py`, and 17 files reach their siblings
with `sys.path.insert(0, HERE)`. Under that pattern a module name is global:
the first lane to import `cli` owns the name `cli` in `sys.modules`, and every
later lane asking for `cli` gets the first lane's file.

Reproduced on real main:

    lane A cli -> .../qa_refusal_contract/cli.py
    lane B cli -> .../qa_refusal_contract/cli.py
    SAME OBJECT: True
    lane B FAILED: IndexError list index out of range

The `IndexError` is the dangerous part. The failure does not present as an
ImportError pointing at the real cause; it presents as the wrong code running,
and then something unrelated breaking several frames away.

The fix that touches nobody's lane
----------------------------------
`spec_from_file_location` with a lane-qualified name. The module is registered
as `uiowa_lane.<lane>.<module>` rather than `<module>`, so two lanes can hold
the same filename and neither shadows the other. No lane has to rename a file,
and no lane has to be edited.

    alpha = load("fixtures/lane_alpha", "report")
    beta = load("fixtures/lane_beta", "report")
    alpha.summary()   # "ALPHA: 3 findings"
    beta.summary()    # "BETA: 7 findings"

What this does NOT fix
----------------------
Only the module *this* function loads is scoped. If that module then does
`import helper` internally, `helper` resolves through the ordinary path and can
still collide. `load_lane_isolated` handles that case by putting the lane's own
directory first for the duration of the load, which is correct for lanes whose
internal imports are all siblings -- the shape every lane in this kit uses.
Neither form can help a module that mutates `sys.path` at import time itself.
That case is reported by `scan.py` as UNKNOWN rather than assumed safe.
"""

import contextlib
import importlib.util
import os
import sys

NAMESPACE = "uiowa_lane"


class LaneImportError(Exception):
    pass


def qualified_name(lane_dir, module_name):
    """The name a lane's module is registered under. Stable and collision-free."""
    lane = os.path.basename(os.path.abspath(lane_dir.rstrip(os.sep)))
    return "%s.%s.%s" % (NAMESPACE, lane, module_name)


def load(lane_dir, module_name, reload=False):
    """Import `<lane_dir>/<module_name>.py` without claiming the bare name."""
    path = os.path.join(lane_dir, module_name + ".py")
    if not os.path.isfile(path):
        raise LaneImportError("no module %s in %s" % (module_name, lane_dir))

    qualified = qualified_name(lane_dir, module_name)
    if qualified in sys.modules and not reload:
        return sys.modules[qualified]

    spec = importlib.util.spec_from_file_location(qualified, path)
    if spec is None or spec.loader is None:
        raise LaneImportError("cannot build a loader for %s" % path)
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so a module that imports itself does not recurse.
    sys.modules[qualified] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # A half-initialised module left in sys.modules is worse than none:
        # the next caller gets an object whose attributes silently do not
        # exist, which is this whole failure class one level down.
        sys.modules.pop(qualified, None)
        raise
    return module


@contextlib.contextmanager
def lane_path(lane_dir):
    """Put one lane's directory first, then restore sys.path exactly.

    Restoring by saved copy rather than by removing what was added: a module
    that mutates sys.path during import would otherwise leave its entries
    behind, and the next lane would load against a path this code did not
    choose.
    """
    saved = list(sys.path)
    sys.path.insert(0, os.path.abspath(lane_dir))
    try:
        yield
    finally:
        sys.path[:] = saved


def load_lane_isolated(lane_dir, module_name, reload=False):
    """`load`, with the lane's own directory first while it executes.

    For a lane whose internal imports are all siblings -- the shape every lane
    in this kit uses -- this makes those sibling imports resolve inside the
    lane rather than against whatever loaded first.
    """
    with lane_path(lane_dir):
        return load(lane_dir, module_name, reload=reload)


def loaded_lanes():
    """Which lane modules are currently held, for diagnosis."""
    out = {}
    for name, module in sorted(sys.modules.items()):
        if not name.startswith(NAMESPACE + "."):
            continue
        out[name] = getattr(module, "__file__", None)
    return out
