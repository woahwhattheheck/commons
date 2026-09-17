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

# Preserve the import-generation public API. Later module-name rebinding must not
# alter these closure objects or the semantic generation they consume.
original_compile = a.compile_acceptance
original_make = a.make_receipt
original_verify = a.verify_receipt


def must_not_mint(mutated, label):
    try:
        receipt = original_make(mutated)
    except a.ContractError:
        return
    if original_verify(mutated, receipt):
        raise AssertionError(f"{label}: stronger caller semantics self-verified")
    raise AssertionError(f"{label}: stronger caller semantics minted a receipt")


# Review 5233074044 predecessor: mutate exported data mirrors in place and mirror
# those values into the manifest. The closed API must still enforce its captured
# import-generation semantics.
a.EXPECTED_SOURCE_NOTES["partner_public"] = "KHow confirmed this workshare"
bad = copy.deepcopy(canonical)
for row in bad["sources"]:
    if row["kind"] == "partner_public":
        row["note"] = a.EXPECTED_SOURCE_NOTES["partner_public"]
must_not_mint(bad, "source-note mirror mutation")

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

# Review 5235059489 predecessor: the exported `_SEALED_ROOT` must be a detached
# introspection snapshot, never the authority object captured by the public API.
# Mutating it in place through either route must not redefine signed semantics.
if not hasattr(a._SEALED_ROOT, "__dict__"):
    raise AssertionError("detached root snapshot lost __dict__ predecessor surface")
a._SEALED_ROOT.__dict__["commercial_state"] = "PAID"
bad = copy.deepcopy(canonical)
bad["commercial"]["state"] = "PAID"
must_not_mint(bad, "sealed-root __dict__ commercial-state mutation")

object.__setattr__(
    a._SEALED_ROOT,
    "deliverables",
    ("Westfield awarded and paid Token Junkie Labs",)
    + tuple(a._SEALED_ROOT.deliverables[1:]),
)
bad = copy.deepcopy(canonical)
bad["workshare"]["deliverables"] = list(a._SEALED_ROOT.deliverables)
must_not_mint(bad, "sealed-root object.__setattr__ scope mutation")

# The original authority generation must remain byte-stable after both in-place
# attacks against the detached snapshot.
receipt_after_root_attacks = original_make(canonical)
if not original_verify(canonical, receipt_after_root_attacks):
    raise AssertionError("canonical carrier changed after detached-root mutation")

# Rebind every exposed implementation/data name that previously represented an
# authority seam. The already-captured API must remain unchanged.
a._SEALED_ROOT = None
a._validate_sources = lambda value: value
a._expect_keys = lambda *args, **kwargs: None
a.canonical_json = lambda value: "forged"
a.sha256_json = lambda value: "0" * 64
a._build_semantic_api = lambda: (None, None, None, None)
a.compile_acceptance = lambda manifest: {"forged": True}
a.make_receipt = lambda manifest: {"forged": True}

receipt = original_make(canonical)
if not original_verify(canonical, receipt):
    raise AssertionError("canonical carrier stopped verifying after module rebinds")
if original_compile(canonical).get("forged"):
    raise AssertionError("captured compiler resolved the rebound module function")

# Public business APIs must not expose semantic/helper override parameters. Each
# predecessor should be a TypeError rather than an alternate authority route.
override_attempts = (
    lambda: original_compile(canonical, _root=None),
    lambda: original_make(canonical, _root=None),
    lambda: original_make(canonical, _compile=lambda manifest: {"forged": True}),
    lambda: original_verify(
        canonical,
        receipt,
        _make_receipt=lambda manifest: receipt,
    ),
    lambda: original_verify(
        canonical,
        receipt,
        _canonical_json=lambda value: "same",
    ),
)
for index, attempt in enumerate(override_attempts):
    try:
        attempt()
    except TypeError:
        continue
    raise AssertionError(f"override route {index} was accepted")
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

    def test_fresh_child_module_data_mutation_normal(self) -> None:
        self._run_child(False)

    def test_fresh_child_module_data_mutation_optimized(self) -> None:
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
