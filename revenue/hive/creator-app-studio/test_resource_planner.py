#!/usr/bin/env python3
"""Regression tests for the source-backed mixed workshop resource planner."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = (HERE / "resource_planner.html").read_text(encoding="utf-8")
PURE = HTML[HTML.index("// BEGIN RESOURCE PLANNER PURE"):HTML.index("// END RESOURCE PLANNER PURE")]


@unittest.skipUnless(shutil.which("node"), "Node is required for shipped JavaScript contract tests")
class MixedResourcePlannerTests(unittest.TestCase):
    def js(self, expression, data):
        code = PURE + '\nconst input=JSON.parse(require("fs").readFileSync(0,"utf8"));console.log(JSON.stringify(' + expression + '));'
        result = subprocess.run(
            ["node", "-e", code],
            input=json.dumps(data),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        return json.loads(result.stdout)

    @staticmethod
    def plan(expected=28, rostered=35):
        return {
            "name": "Ceramics class",
            "rostered": rostered,
            "expected": expected,
            "resources": [
                {"name": "Banding wheels", "unit": "wheels", "mode": "shared_reusable",
                 "quantity": "4", "pack_size": "1", "buffer_percent": "0"},
                {"name": "Consumable material", "unit": "units", "mode": "per_attendee_consumable",
                 "quantity": "1.5", "pack_size": "10", "buffer_percent": "0"},
            ],
        }

    def test_shared_resource_is_invariant_when_expected_attendance_changes(self):
        rows = self.js("input.map(p=>calculate(p)[0])", [self.plan(28), self.plan(35), self.plan(90)])
        self.assertEqual([(r["required"], r["packs"], r["purchase"]) for r in rows],
                         [("4", "4", "4"), ("4", "4", "4"), ("4", "4", "4")])

    def test_consumable_scales_only_with_expected_attendance(self):
        rows = self.js("input.map(p=>calculate(p)[1])", [self.plan(28), self.plan(35)])
        self.assertEqual((rows[0]["required"], rows[0]["packs"], rows[0]["purchase"]), ("42", "5", "50"))
        self.assertEqual((rows[1]["required"], rows[1]["packs"], rows[1]["purchase"]), ("52.5", "6", "60"))

    def test_rostered_headcount_is_reference_not_quantity_driver(self):
        rows = self.js("input.map(p=>calculate(p))", [self.plan(28, 35), self.plan(28, 300)])
        self.assertEqual(rows[0], rows[1])

    def test_mixed_reserve_and_fractional_pack_arithmetic_is_exact(self):
        plan = self.plan(3)
        plan["resources"] = [
            {"name": "Shared glaze tools", "unit": "sets", "mode": "shared_reusable",
             "quantity": "0.1", "pack_size": "0.3", "buffer_percent": "0"},
            {"name": "Sheets", "unit": "sheets", "mode": "per_attendee_consumable",
             "quantity": "0.1", "pack_size": "0.3", "buffer_percent": "0"},
        ]
        rows = self.js("calculate(input)", plan)
        self.assertEqual((rows[0]["required"], rows[0]["packs"], rows[0]["purchase"]), ("0.1", "1", "0.3"))
        self.assertEqual((rows[1]["required"], rows[1]["packs"], rows[1]["purchase"]), ("0.3", "1", "0.3"))

    def test_unknown_mode_fails_closed(self):
        plan = self.plan()
        plan["resources"][0]["mode"] = "maybe_shared"
        rejected = self.js("(()=>{try{calculate(input);return false}catch(e){return true}})()", plan)
        self.assertTrue(rejected)

    def test_backup_roundtrip_preserves_resource_modes(self):
        plan = self.plan()
        backup = {"schema": 1, "plans": [{"id": "ceramics-1", **plan}]}
        normalized = self.js("validateBackup(input)", backup)[0]
        self.assertEqual([r["mode"] for r in normalized["resources"]],
                         ["shared_reusable", "per_attendee_consumable"])

    def test_csv_formula_neutralization_is_retained(self):
        values = ["=1+1", "\t+2", "@formula", "-supply", "ordinary", 'a,"b"']
        result = self.js("input.map(csvCell)", values)
        self.assertEqual(result, ['"\'=1+1"', '"\'\t+2"', '"\'@formula"', '"\'-supply"', '"ordinary"', '"a,""b"""'])

    def test_script_parses_in_node(self):
        scripts = re.findall(r"<script>(.*?)</script>", HTML, re.S)
        self.assertEqual(len(scripts), 1)
        subprocess.run(["node", "--check"], input=scripts[0], text=True,
                       capture_output=True, check=True, timeout=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
