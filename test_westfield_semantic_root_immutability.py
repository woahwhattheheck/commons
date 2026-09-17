"""Fresh-child hostile proof for Westfield semantic-root immutability."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parent
PACKAGE = ROOT / "revenue" / "westfield_advancement_data_modeling"

CHILD = r"""
import copy
import pathlib
import sys

package = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(package))
import acceptance as a

manifest_path = package / "westfield_manifest.json"
canonical = a.load_strict_json(manifest_path.read_text(encoding="utf-8"))


def must_not_mint(mutated, label):
    try:
        receipt = a.make_receipt(mutated)
    except a.ContractError:
        return
    if a.verify_receipt(mutated, receipt):
        raise AssertionError(f"{label}: stronger caller semantics self-verified")
    raise AssertionError(f"{label}: stronger caller semantics minted a receipt")


# Review 5233074044 predecessor: mutate the exported dict in place.
a.EXPECTED_SOURCE_NOTES["partner_public"] = "KHow confirmed this workshare"
bad = copy.deepcopy(canonical)
for row in bad["sources"]:
    if row["kind"] == "partner_public":
        row["note"] = a.EXPECTED_SOURCE_NOTES["partner_public"]
must_not_mint(bad, "source-note mirror mutation")

# Other mapping mirrors are equally non-authoritative.
a.EXPECTED_METRICS["ranking"] = "buyer_approved_rank"
bad = copy.deepcopy(canonical)
bad["model_acceptance"]["metrics"]["ranking"] = a.EXPECTED_METRICS["ranking"]
must_not_mint(bad, "metric mirror mutation")

a.EXPECTED_OPPORTUNITY["buyer"] = "Other University"
bad = copy.deepcopy(canonical)
bad["opportunity"]["buyer"] = a.EXPECTED_OPPORTUNITY["buyer"]
must_not_mint(bad, "opportunity mirror mutation")

a.EXPECTED_SOURCE_URLS["partner_public"] = "https://example.com/claimed-partner"
bad = copy.deepcopy(canonical)
for row in bad["sources"]:
    if row["kind"] == "partner_public":
        row["url"] = a.EXPECTED_SOURCE_URLS["partner_public"]
must_not_mint(bad, "source-url mirror mutation")

# Ordinary module-global rebinding must not redefine signed vocabulary or truth.
a.EXPECTED_DELIVERABLES = (
    "Westfield awarded and paid Token Junkie Labs",
) + tuple(a.EXPECTED_DELIVERABLES[1:])
bad = copy.deepcopy(canonical)
bad["workshare"]["deliverables"] = list(a.EXPECTED_DELIVERABLES)
must_not_mint(bad, "deliverable root rebind")

a.COMMERCIAL_STATE = "PAID"
bad = copy.deepcopy(canonical)
bad["commercial"]["state"] = "PAID"
must_not_mint(bad, "commercial-state rebind")

a.SCHEMA = "advancement-model-acceptance/caller-v999"
bad = copy.deepcopy(canonical)
bad["schema"] = a.SCHEMA
must_not_mint(bad, "schema rebind")

a.REQUIRED_CHECKS = frozenset({"caller_claimed_certified"})
bad = copy.deepcopy(canonical)
bad["model_acceptance"]["required_checks"] = sorted(a.REQUIRED_CHECKS)
must_not_mint(bad, "required-check root rebind")

a.AUTHORITY_KEYS = frozenset({"award_received"})
bad = copy.deepcopy(canonical)
bad["authority"] = {"award_received": False}
must_not_mint(bad, "authority-key root rebind")

# Even rebinding the module's private name cannot replace the generation already
# captured by compile/mint/verify function defaults.
a._SEALED_ROOT = None
receipt = a.make_receipt(canonical)
if not a.verify_receipt(canonical, receipt):
    raise AssertionError("canonical carrier stopped verifying after data-global rebinds")
"""


class SemanticRootFreshChildTests(unittest.TestCase):
    def _run_child(self, optimized: bool) -> None:
        cmd = [sys.executable]
        if optimized:
            cmd.append("-O")
        cmd.extend(["-c", CHILD, str(PACKAGE)])
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

    def test_fresh_child_data_global_mutation_normal(self) -> None:
        self._run_child(False)

    def test_fresh_child_data_global_mutation_optimized(self) -> None:
        canary = subprocess.run(
            [
                sys.executable,
                "-O",
                "-c",
                "import sys; sys.exit(0 if not __debug__ else 91)",
            ],
            cwd=ROOT,
            check=False,
            timeout=20,
        )
        self.assertEqual(canary.returncode, 0)
        self._run_child(True)


if __name__ == "__main__":
    unittest.main()
