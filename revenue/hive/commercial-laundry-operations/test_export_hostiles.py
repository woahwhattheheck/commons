from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from laundry_desk import LaundryDesk


class ExportHostiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "desk.sqlite3")
        self.desk = LaundryDesk(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("cli.py")), self.db, *args],
            cwd=Path(__file__).parent,
            text=True,
            capture_output=True,
        )

    def test_maximum_customer_id_exports_with_bounded_deterministic_filenames(self):
        customer_id = "z" * 255
        self.desk.add_customer("cli.max.customer", customer_id, "Max Export Customer")
        out = Path(self.tmp.name) / "max-customer-export"
        run = self._cli("export-customer", customer_id, str(out))
        self.assertEqual(run.returncode, 0, run.stderr)
        payload = json.loads(run.stdout)
        self.assertEqual(set(payload["created"]), {"json", "csv", "markdown"})
        for path_text in payload["created"].values():
            path = Path(path_text)
            self.assertTrue(path.exists())
            self.assertLessEqual(len(path.name.encode("utf-8")), 255)
            self.assertIn("sha256", path.name)
        exported = json.loads(Path(payload["created"]["json"]).read_text(encoding="utf-8"))
        self.assertEqual(exported["customer_id"], customer_id)

    def test_occupied_sibling_preflights_whole_bundle_before_any_write(self):
        d = self.desk
        d.add_customer("op.c", "cust-a", "Customer A")
        d.add_site("op.s", "site-a", "cust-a", "Site A")
        d.add_agreement("op.a", "agr-sheet", "site-a", "sheet", 125, "2026-01-01")
        d.add_service_plan("op.p", "plan-a", "site-a", "route-one", 0, 10, "2026-01-01")
        route = d.create_daily_route("op.r", "2026-09-21", "route-one").value
        stop = route["stops"][0]["stop_id"]
        d.pickup("op.pickup", stop, {"sheet": 10}, ["bin-1"])
        d.process("op.process", stop, {"sheet": 10}, {"sheet": 0})
        d.deliver("op.deliver", stop, {"sheet": 10}, ["bin-1"])
        d.draft_invoice("op.invoice", stop)

        out = Path(self.tmp.name) / "preflight-exports"
        out.mkdir()
        occupied = out / "route-route_2026-09-21_route-one.csv"
        occupied.write_text("already here\n", encoding="utf-8")
        run = self._cli("export-route", route["route_id"], str(out))
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(sorted(path.name for path in out.iterdir()), [occupied.name])
        self.assertEqual(occupied.read_text(encoding="utf-8"), "already here\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
