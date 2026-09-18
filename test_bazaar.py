#!/usr/bin/env python3
"""Paid Action Bazaar: market for copied Muhlnickel computation, not verification."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SEED0 = os.path.join(HERE, "muhl", "containers", "MUHLNICKEL_DISTRO", "SEED0.mno")
_SPEC = importlib.util.spec_from_file_location(
    "commons_bazaar_cli", os.path.join(HERE, "host", "bazaar.py")
)
bazaar = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bazaar)


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


class BazaarTests(unittest.TestCase):
    def test_land_exists(self):
        for name in (
            "bazaar.html", "bazaar.js", "bazaar.json",
            "host/bazaar.py", "ground/BAZAAR.md",
        ):
            self.assertTrue(os.path.isfile(os.path.join(HERE, name)), name)

    def test_catalog_validates_and_has_verticals(self):
        self.assertEqual(bazaar.main(["validate"]), 0)
        data = json.loads(read("bazaar.json"))
        verticals = {row["vertical"] for row in data["offers"]}
        for need in ("muhl-observe", "reproduce", "repo-work", "machine-device", "public-network"):
            self.assertIn(need, verticals)
        blob = json.dumps(data).lower()
        self.assertNotIn("3+5", blob)
        self.assertNotIn("does it work", blob)

    def test_plaza_is_computation_market(self):
        html = read("bazaar.html")
        self.assertIn("copied, addressed Muhlnickels", html)
        self.assertIn("action.html", html)
        self.assertIn("SEED0.mno", html)
        self.assertNotIn("VERDICT", html)
        js = read("bazaar.js")
        self.assertIn('kind: "ACTION"', js)
        self.assertIn("action.html#fire=", js)
        self.assertNotIn("VERDICT", js)

    def test_boards_list_bazaar(self):
        self.assertIn('href="./bazaar.html"', read("boards.html"))
        self.assertIn('href="./bazaar.html"', read("hub_pages.py"))

    def test_action_pad_untouched(self):
        html = read("action.html")
        self.assertIn("OPEN DOOR", html)
        self.assertIn("THE LINK AUTHORIZES USE", html)
        self.assertIn("No login", html)

    def test_pack_wire_refuses_computer(self):
        with tempfile.TemporaryDirectory() as td:
            dest = os.path.join(td, "nope.bin")
            rc = bazaar.main(["pack-wire", "--in", SEED0, "--out", dest])
            self.assertEqual(rc, 2)
            self.assertFalse(os.path.isfile(dest))

    def test_pack_wire_archives_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            dest = os.path.join(td, "packed.bin")
            src = os.path.join(HERE, "bazaar.json")
            rc = bazaar.main(["pack-wire", "--in", src, "--out", dest])
            self.assertEqual(rc, 0)
            raw = open(src, "rb").read()
            packed = open(dest, "rb").read()
            self.assertEqual(zlib.decompress(packed), raw)
            self.assertTrue(os.path.isfile(dest + ".recipe.json"))

    def test_copy_node_is_byte_exact(self):
        with tempfile.TemporaryDirectory() as td:
            dest = os.path.join(td, "SEED0.mno")
            rc = bazaar.main(["copy-node", "--source", SEED0, "--dest", dest])
            self.assertEqual(rc, 0)
            self.assertEqual(open(SEED0, "rb").read(), open(dest, "rb").read())

    def test_lineage_records_output_not_ceremony(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "lineage.json")
            rc = bazaar.main([
                "lineage", "--computer", SEED0,
                "--artifact", os.path.join(HERE, "bazaar.json"),
                "--out", out, "--id", "bazaar-test-lineage-01",
            ])
            self.assertEqual(rc, 0)
            row = json.loads(open(out, encoding="utf-8").read())
            self.assertEqual(row["kind"], "BAZAAR_RESULT")
            self.assertEqual(row["computer"]["size"], 8192)
            self.assertEqual(row["computer"]["magic"], "MUHLPKG1")
            self.assertTrue(row["artifacts"][0]["sha256"])
            self.assertIn("does-it-work ceremony", row["not"])

    def test_refuses_go_inject_337(self):
        self.assertEqual(bazaar.main(["--go", "catalog"]), 2)
        self.assertEqual(bazaar.main(["catalog", "--inject"]), 2)
        self.assertEqual(bazaar.main(["catalog", "337"]), 2)

    def test_emit_action_is_addressed_capability(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bazaar.main(["emit-action", "--offer-id", "cursor-bazaar-open-marker-20260822-01"])
        self.assertEqual(rc, 0)
        packet = json.loads(buf.getvalue())
        self.assertEqual(packet["kind"], "ACTION")
        self.assertEqual(packet["act"], "PUSH")
        self.assertIn("bazaar/work/repo/", packet["target"])

    def test_host_script_has_no_subprocess(self):
        text = read("host/bazaar.py")
        self.assertNotIn("subprocess", text)
        self.assertNotIn("numpy", text)
        self.assertNotIn("def fire", text)


if __name__ == "__main__":
    unittest.main()
