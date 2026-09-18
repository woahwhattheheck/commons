import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("projection", ROOT / "prototype" / "dashboard_projection.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)

BASE = {
    "project_id": "P-001", "town": "Concord", "program": "ARPA",
    "funding_kind": "grant", "project_type": "drinking_water",
    "funding_cents": 12500000, "source_year": 2026,
    "latitude": "43.2081", "longitude": "-71.5376",
    "narrative": "Synthetic fixture only; not an NHDES project record.",
    "media": [{"url": "https://example.invalid/p-001.jpg", "alt": "Synthetic water project fixture"}],
}


def build(rows):
    raw = (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return mod.build_projection(raw, rows)


class ProjectionTests(unittest.TestCase):
    def test_deterministic_order_and_totals(self):
        a = copy.deepcopy(BASE)
        b = copy.deepcopy(BASE)
        b.update(project_id="P-000", town="Dover", program="CWSRF", funding_kind="loan", funding_cents=500)
        out1 = build([a, b]); out2 = build([b, a])
        self.assertEqual([p["project_id"] for p in out1["projects"]], ["P-000", "P-001"])
        self.assertEqual(out1["total_funding_cents"], 12500500)
        c1 = dict(out1); c2 = dict(out2)
        c1.pop("source_sha256"); c2.pop("source_sha256")
        self.assertEqual(mod.canonical_bytes(c1), mod.canonical_bytes(c2))

    def test_duplicate_id_blocks(self):
        with self.assertRaises(mod.DataError): build([BASE, copy.deepcopy(BASE)])

    def test_negative_money_blocks(self):
        row = copy.deepcopy(BASE); row["funding_cents"] = -1
        with self.assertRaises(mod.DataError): build([row])

    def test_float_money_blocks(self):
        row = copy.deepcopy(BASE); row["funding_cents"] = 1.5
        with self.assertRaises(mod.DataError): build([row])

    def test_out_of_state_coordinate_blocks(self):
        row = copy.deepcopy(BASE); row["latitude"] = "40.0"
        with self.assertRaises(mod.DataError): build([row])

    def test_missing_alt_text_blocks(self):
        row = copy.deepcopy(BASE); row["media"][0]["alt"] = ""
        with self.assertRaises(mod.DataError): build([row])

    def test_missing_narrative_blocks(self):
        row = copy.deepcopy(BASE); row["narrative"] = "   "
        with self.assertRaises(mod.DataError): build([row])

    def test_unknown_program_blocks(self):
        row = copy.deepcopy(BASE); row["program"] = "MAGIC"
        with self.assertRaises(mod.DataError): build([row])

    def test_unknown_project_type_blocks(self):
        row = copy.deepcopy(BASE); row["project_type"] = "spaceship"
        with self.assertRaises(mod.DataError): build([row])


if __name__ == "__main__": unittest.main()
