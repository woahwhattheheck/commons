"""Distinct POPLAR root-provenance cases composed on BASALT's actual module.

Adapted from ASTRA-POPLAR PR10634, source test blob
7ba9711c9fa2287f411f98a8cdc7d8d745a416fa. HARBOR-PUSH trimmed cases already
covered by BASALT's test_pack_waitlist_pointer_roots.py. No runtime patching;
only location constants point at real temporary checkout files.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parent / "host" / "pack_waitlist_pointer.py"
SPEC = importlib.util.spec_from_file_location("poplar_root_companion_subject", SOURCE)
assert SPEC is not None and SPEC.loader is not None
pointer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pointer)
POINTER_REL = Path("ground/BUSINESS_PACK_WAITLIST_POINTER.json")


def put_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_checkout(root: Path, label: str) -> None:
    put_json(root / POINTER_REL, {
        "id": f"pointer-{label}", "owner_seat": f"owner-{label}",
        "scout_demand_id": f"scout-{label}", "pointer_only": True,
        "did_not_remint_scout_demand": True, "checkout": "NOT_MINTED",
    })
    put_json(root / "ground/BUSINESS_PACKS.json", {
        "id": f"unique-{label}",
        "waitlist": {"id": f"pointer-{label}", "claimed_by": f"fallback-{label}"},
    })
    put_json(root / "packs/desk-website-service-20260902-01/instance.json", {
        "brand": "Harborline Local Sites", "door": f"door-{label}",
    })
    put_json(root / "packs/sidewalk-signal-web-desk-20260902-01/manifest.json", {
        "brand": "Sidewalk Signal",
    })
    for rel in pointer.OWNER_PATHS + (
        "packs/thanks.html", "host/business_pack_desk_instance.py",
        "host/business_pack_waitlist_pointer.py",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"synthetic fixture {label}: {rel}\n", encoding="utf-8")


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


class PackWaitlistPointerRootCompanionTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        self.default = self.work / "default"
        self.candidate = self.work / "candidate"
        self.other = self.work / "other"
        for root, label in ((self.default, "default"),
                            (self.candidate, "candidate"), (self.other, "other")):
            make_checkout(root, label)
        for name, value in (("ROOT", self.default),
                            ("POINTER_LAW", self.default / POINTER_REL)):
            override = patch.object(pointer, name, value)
            override.start()
            self.addCleanup(override.stop)

    def test_sequential_roots_do_not_leak_or_write(self) -> None:
        before = snapshot(self.work)
        ids = [pointer.classify(root=root)["id"] for root in
               (self.candidate, self.other, self.candidate, None)]
        self.assertEqual(ids, ["pointer-candidate", "pointer-other",
                               "pointer-candidate", "pointer-default"])
        self.assertEqual(snapshot(self.work), before)

    def test_relative_explicit_root_uses_selected_checkout(self) -> None:
        old_cwd = Path.cwd()
        try:
            os.chdir(self.work)
            result = pointer.classify(root=Path("candidate"))
        finally:
            os.chdir(old_cwd)
        self.assertEqual(result["id"], "pointer-candidate")
        self.assertEqual(result["unique_pack_law_id"], "unique-candidate")

    def test_other_nonobject_selected_laws_are_not_hidden(self) -> None:
        # The existing BASALT suite already covers [] at this boundary.
        for value in (None, "not-an-object", 7, False):
            with self.subTest(value=value):
                put_json(self.candidate / POINTER_REL, value)
                with self.assertRaisesRegex(ValueError, "is not an object"):
                    pointer.classify(root=self.candidate)

    def test_non_dict_override_keeps_selected_root_fallback(self) -> None:
        for value in ([], "ignored", 0, False):
            with self.subTest(value=value):
                result = pointer.classify(root=self.candidate, pointer=value)
                self.assertEqual(result["id"], "pointer-candidate")

    def test_owner_path_presence_is_selected_checkout_local(self) -> None:
        removed = pointer.OWNER_PATHS[0]
        (self.candidate / removed).unlink()
        candidate = pointer.classify(root=self.candidate)
        default = pointer.classify()
        self.assertEqual(candidate["owner_seat"], "owner-candidate")
        self.assertEqual(candidate["owner_paths"][0]["path"], removed)
        self.assertFalse(candidate["owner_paths"][0]["present"])
        self.assertTrue(default["owner_paths"][0]["present"])
        self.assertTrue(all(not row["this_seat_writes"]
                            for row in candidate["owner_paths"]))

    def test_explicit_pointer_and_nested_metadata_are_not_mutated(self) -> None:
        override = {"id": "override", "owner_seat": "override-owner",
                    "extra": {"retained": ["original", {"value": 1}]}}
        original = copy.deepcopy(override)
        before = snapshot(self.work)
        pointer.classify(root=self.candidate, pointer=override)
        pointer.classify(root=self.other, pointer=override)
        self.assertEqual(override, original)
        self.assertEqual(snapshot(self.work), before)

    def test_full_preservation_declarations_remain_unchanged(self) -> None:
        result = pointer.classify(root=self.candidate)
        for field in ("did_not_write_owner_paths", "did_not_overwrite_tally_helper",
                      "did_not_overwrite_peer_helper", "no_fake_stripe_urls"):
            self.assertIs(result[field], True, field)
        self.assertIs(result["agents_spend_ads"], False)
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["do_not_overwrite"], list(pointer.DO_NOT_OVERWRITE))
        self.assertEqual(result["this_seat_paths"], list(pointer.THIS_SEAT_PATHS))
        self.assertFalse(result["harborline"]["clone_stamp"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
