#!/usr/bin/env python3
"""Real-directory regressions for pack waitlist pointer root provenance.

Only module-location constants are redirected. JSON loading, hashing and all
classification functions execute normally against actual temporary files.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import pack_waitlist_pointer as pointer  # noqa: E402

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


class PackWaitlistPointerRootProvenanceTest(unittest.TestCase):
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
            p = patch.object(pointer, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_explicit_root_uses_its_own_pointer(self) -> None:
        result = pointer.classify(root=self.candidate)
        self.assertEqual(result["id"], "pointer-candidate")
        self.assertEqual(result["id"], result["unique_pack_waitlist_pointer_id"])

    def test_identity_and_other_facts_share_one_checkout(self) -> None:
        (self.candidate / pointer.OWNER_PATHS[0]).unlink()
        result = pointer.classify(root=self.candidate)
        self.assertEqual(result["owner_seat"], "owner-candidate")
        self.assertEqual(result["scout_demand_id"], "scout-candidate")
        self.assertEqual(result["unique_pack_law_id"], "unique-candidate")
        self.assertEqual(result["harborline"]["harborline_door"], "door-candidate")
        self.assertFalse(result["owner_paths"][0]["present"])
        self.assertEqual(result["thanks_door"]["blob"],
                         pointer.git_blob_sha(self.candidate / "packs/thanks.html"))

    def test_sequential_roots_do_not_leak_identity(self) -> None:
        ids = [pointer.classify(root=root)["id"] for root in
               (self.candidate, self.other, self.candidate)]
        self.assertEqual(ids, ["pointer-candidate", "pointer-other", "pointer-candidate"])

    def test_missing_selected_law_does_not_fall_back(self) -> None:
        (self.candidate / POINTER_REL).unlink()
        with self.assertRaises(FileNotFoundError) as caught:
            pointer.classify(root=self.candidate)
        self.assertEqual(Path(caught.exception.filename), self.candidate / POINTER_REL)

    def test_malformed_selected_law_is_not_hidden(self) -> None:
        (self.candidate / POINTER_REL).write_text("{broken", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            pointer.classify(root=self.candidate)

    def test_non_object_selected_law_is_not_hidden(self) -> None:
        for value in ([], None, "not-an-object", 7, False):
            with self.subTest(value=value):
                put_json(self.candidate / POINTER_REL, value)
                with self.assertRaisesRegex(ValueError, "is not an object"):
                    pointer.classify(root=self.candidate)

    def test_missing_default_law_cannot_break_explicit_root(self) -> None:
        (self.default / POINTER_REL).unlink()
        self.assertEqual(pointer.classify(root=self.candidate)["id"], "pointer-candidate")

    def test_malformed_default_law_cannot_break_explicit_root(self) -> None:
        (self.default / POINTER_REL).write_text("{broken", encoding="utf-8")
        self.assertEqual(pointer.classify(root=self.candidate)["id"], "pointer-candidate")

    def test_explicit_pointer_override_still_wins(self) -> None:
        (self.candidate / POINTER_REL).unlink()
        override = {"id": "override", "owner_seat": "override-owner", "pointer_only": True}
        original = dict(override)
        result = pointer.classify(root=self.candidate, pointer=override)
        self.assertEqual(result["id"], "override")
        self.assertEqual(result["owner_seat"], "override-owner")
        self.assertEqual(result["unique_pack_law_id"], "unique-candidate")
        self.assertEqual(override, original)

    def test_empty_dict_override_still_wins(self) -> None:
        (self.candidate / POINTER_REL).unlink()
        result = pointer.classify(root=self.candidate, pointer={})
        self.assertEqual(result["id"], "")
        self.assertEqual(result["owner_seat"], "fallback-candidate")
        self.assertFalse(result["pointer_only"])

    def test_no_root_preserves_default_lookup(self) -> None:
        self.assertEqual(pointer.classify()["id"], "pointer-default")
        self.assertEqual(pointer.classify(root=None)["id"], "pointer-default")

    def test_no_root_preserves_configured_pointer_law(self) -> None:
        custom = self.work / "custom-pointer.json"
        put_json(custom, {"id": "configured-default"})
        with patch.object(pointer, "POINTER_LAW", custom):
            result = pointer.classify()
        self.assertEqual(result["id"], "configured-default")
        self.assertEqual(result["unique_pack_law_id"], "unique-default")

    def test_relative_explicit_root_uses_selected_checkout(self) -> None:
        old_cwd = Path.cwd()
        try:
            os.chdir(self.work)
            result = pointer.classify(root=Path("candidate"))
        finally:
            os.chdir(old_cwd)
        self.assertEqual(result["id"], "pointer-candidate")

    def test_classification_does_not_write_either_checkout(self) -> None:
        before = snapshot(self.work)
        pointer.classify(root=self.candidate)
        pointer.classify(root=self.other)
        pointer.classify()
        self.assertEqual(snapshot(self.work), before)

    def test_existing_non_gate_contract_is_unchanged(self) -> None:
        result = pointer.classify(root=self.candidate)
        for field in ("gate", "commons_admission", "agents_spend_ads"):
            self.assertIs(result[field], False, field)
        for field in ("did_not_write_owner_paths", "did_not_overwrite_tally_helper",
                      "did_not_overwrite_peer_helper", "no_fake_stripe_urls"):
            self.assertIs(result[field], True, field)
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["do_not_overwrite"], list(pointer.DO_NOT_OVERWRITE))
        self.assertEqual(result["this_seat_paths"], list(pointer.THIS_SEAT_PATHS))
        self.assertTrue(result["harborline"]["similar_is_not_clone"])
        self.assertFalse(result["harborline"]["clone_stamp"])

    def test_non_dict_override_keeps_fallback_contract_for_selected_root(self) -> None:
        for value in ([], "ignored", 0, False):
            with self.subTest(value=value):
                result = pointer.classify(root=self.candidate, pointer=value)
                self.assertEqual(result["id"], "pointer-candidate")

    def test_cli_default_lookup_remains_compatible(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = pointer.main([])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["id"], "pointer-default")

    def test_cli_explicit_pointer_override_remains_compatible(self) -> None:
        custom = self.work / "cli-pointer.json"
        put_json(custom, {"id": "cli-override"})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = pointer.main(["--pointer", str(custom)])
        self.assertEqual(status, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["id"], "cli-override")
        self.assertEqual(result["unique_pack_law_id"], "unique-default")


if __name__ == "__main__":
    unittest.main(verbosity=2)
