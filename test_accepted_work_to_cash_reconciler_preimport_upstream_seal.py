"""Fresh-child proof that upstream exports cannot be poisoned before AWC import."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parent

CHILD = r'''
import copy
import importlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root))

# Exact predecessor order: import the upstream engine FIRST. The downstream
# reconciler engine must not have been imported yet.
from revenue.revenue_funnel_control import engine as funnel_engine
if "revenue.accepted_work_to_cash_reconciler.engine" in sys.modules:
    raise AssertionError("reconciler engine imported before predecessor setup")
if not getattr(type(funnel_engine), "__revenue_funnel_semantic_root_sealed__", False):
    raise AssertionError("upstream engine did not seal on first normal import")

example_path = root / "revenue" / "accepted_work_to_cash_reconciler" / "example.json"
document = json.loads(example_path.read_text(encoding="utf-8"))

genuine_upstream = funnel_engine.compile_bundle(document["funnel_input"])
forged_upstream = copy.deepcopy(genuine_upstream)
forged_item = forged_upstream["packet"]["opportunities"][0]
forged_item["stage"] = "INVOICED_OR_AWARDED"
forged_item["settlement_target_cents"] = 0
forged_id = forged_item["id"]


def fake_compile(_document):
    return forged_upstream


def fake_verify(_bundle):
    return True

# Review 5233132461 predecessor: ordinary upstream module-export assignment
# before the first reconciler-engine import must fail. Include the factory name
# so the repair cannot simply move the mutable capture one symbol sideways.
for name, replacement in (
    ("compile_bundle", fake_compile),
    ("verify_bundle", fake_verify),
    ("_make_core", lambda: (None, fake_compile, fake_verify, None, None, None)),
):
    try:
        setattr(funnel_engine, name, replacement)
    except AttributeError as exc:
        if "revenue-funnel semantic root is sealed" not in str(exc):
            raise
    else:
        raise AssertionError(f"upstream export remained ordinarily assignable: {name}")

try:
    delattr(funnel_engine, "compile_bundle")
except AttributeError as exc:
    if "revenue-funnel semantic root is sealed" not in str(exc):
        raise
else:
    raise AssertionError("upstream compile_bundle remained ordinarily deletable")

# Only after the poisoning attempt do we import the reconciler. It must capture
# the genuine upstream closure generation and remain semantically narrow.
import revenue.accepted_work_to_cash_reconciler.engine as reconciler_engine
bundle = reconciler_engine.compile_bundle(document)
if not reconciler_engine.verify_bundle(bundle):
    raise AssertionError("genuine reconciler bundle did not verify")
item = next(row for row in bundle["packet"]["items"] if row["opportunity_id"] == forged_id)
if item["terminal_action"] == "DONE_ZERO_VALUE":
    raise AssertionError("pre-import upstream poisoning minted DONE_ZERO_VALUE")
if forged_id not in bundle["packet"]["open_queue"]:
    raise AssertionError("pre-import upstream poisoning removed item from open queue")

# Supported ordinary reload must restore source while keeping the same upstream
# engine object sealed. This also catches loaders that seal only the first import.
reloaded = importlib.reload(funnel_engine)
if reloaded is not funnel_engine:
    raise AssertionError("reload replaced upstream module object")
if not getattr(type(reloaded), "__revenue_funnel_semantic_root_sealed__", False):
    raise AssertionError("reload unsealed upstream semantic root")
try:
    reloaded.verify_bundle = fake_verify
except AttributeError:
    pass
else:
    raise AssertionError("upstream verifier became assignable after reload")
'''


class AcceptedWorkToCashPreImportUpstreamSealTests(unittest.TestCase):
    def _run_child(self, optimized: bool) -> None:
        cmd = [sys.executable]
        if optimized:
            cmd.append("-O")
        cmd.extend(["-c", CHILD, str(ROOT)])
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_preimport_upstream_export_poisoning_is_blocked_normal(self) -> None:
        self._run_child(False)

    def test_preimport_upstream_export_poisoning_is_blocked_optimized(self) -> None:
        canary = subprocess.run(
            [sys.executable, "-O", "-c", "import sys; sys.exit(0 if not __debug__ else 91)"],
            cwd=ROOT,
            check=False,
            timeout=20,
        )
        self.assertEqual(canary.returncode, 0)
        self._run_child(True)


if __name__ == "__main__":
    unittest.main()
