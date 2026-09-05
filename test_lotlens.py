#!/usr/bin/env python3
"""LotLens: expected graph facts frozen independently of the engine; result-level checks.

The synthetic pilot fixture was written by hand, so every expected set below was
derived from the CSV rows, not from running the engine. If a dependency row is
removed, the corresponding assertion must fail (see the mutation test).
"""
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("lotlens_engine", ROOT / "lotlens" / "engine.py")
engine = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = engine
SPEC.loader.exec_module(engine)

FIXTURE = ROOT / "lotlens" / "fixtures" / "synthetic_pilot"
CLI = ROOT / "lotlens" / "lotlens.py"
CITRIC = ("sup-acme", "lot", "LOT-CITRIC-01")

# Hand-derived from the CSV rows.
FORWARD_KNOWN_FROM_CITRIC = {
    "sup-acme/lot/LOT-CITRIC-01A", "sup-acme/lot/LOT-CITRIC-01B",
    "pilot-plant/batch/BATCH-P1", "pilot-plant/batch/BATCH-P3", "pilot-plant/batch/BATCH-P2", "pilot-plant/batch/BATCH-P4",
    "pilot-plant/package/PKG-P1-1", "pilot-plant/package/PKG-P2-1", "pilot-plant/package/PKG-P2-2",
    "pilot-plant/package/PKG-P3-1", "pilot-plant/package/PKG-P4-1",
    "pilot-plant/shipment/SHIP-1", "pilot-plant/shipment/SHIP-2", "pilot-plant/shipment/SHIP-3",
    "pilot-plant/shipment/SHIP-4", "pilot-plant/shipment/SHIP-9",
}
NEVER_FROM_CITRIC = {
    "pilot-plant/batch/BATCH-P5", "pilot-plant/package/PKG-P5-1", "pilot-plant/shipment/SHIP-5",
    "pilot-plant/batch/L-7", "sup-acme/lot/L-7", "pilot-plant/package/PKG-L7-1", "pilot-plant/shipment/SHIP-7",
    "sup-acme/lot/LOT-SUGAR-02", "sup-h2o/lot/LOT-WATER-01", "sup-aqua/lot/LOT-WATER-01",
    "pilot-plant/package/PKG-P9-1",
}
BACKWARD_FROM_SHIP3 = {
    "pilot-plant/package/PKG-P2-2", "pilot-plant/batch/BATCH-P2", "pilot-plant/batch/BATCH-P1",
    "sup-acme/lot/LOT-CITRIC-01A", "sup-acme/lot/LOT-CITRIC-01", "sup-h2o/lot/LOT-WATER-01",
    "sup-acme/lot/LOT-SUGAR-02", "sup-aqua/lot/LOT-WATER-01",
}


def workspace_with_fixture(tmp: str, source: Path = FIXTURE, label: str = "pilot"):
    ws = engine.Workspace(Path(tmp) / "ws")
    info = ws.import_dir(source, label=label)
    return ws, info


def copy_fixture(tmp: str) -> Path:
    dest = Path(tmp) / "fixture"
    shutil.copytree(FIXTURE, dest)
    return dest


def rewrite_csv(path: Path, keep) -> None:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = rows[0].keys() if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            if keep(row):
                writer.writerow(row)


class ImportTests(unittest.TestCase):
    def test_import_records_every_file_and_row_with_namespaces_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws, info = workspace_with_fixture(tmp)
            self.assertTrue(info["new"])
            self.assertEqual(sorted(f["name"] for f in info["files"]), sorted(engine.FILES))
            self.assertEqual(info["rows"]["lots.csv"], 7)
            self.assertEqual(info["rows"]["shipments.csv"], 9)
            graph = ws.graph()
            summary = graph.summary()
            self.assertEqual(summary["nodes"], {"batch": 6, "lot": 7, "package": 9, "shipment": 8})
            self.assertEqual(summary["namespaces"], ["pilot-plant", "sup-acme", "sup-aqua", "sup-h2o"])
            water = graph.find("LOT-WATER-01")
            self.assertEqual([n.namespace for n in water], ["sup-aqua", "sup-h2o"])
            self.assertEqual({n.attrs["supplier"] for n in water}, {"Aqua Ltd", "H2O Co"})
            l7 = graph.find("L-7")
            self.assertEqual(sorted((n.namespace, n.kind) for n in l7), [("pilot-plant", "batch"), ("sup-acme", "lot")])
            # every node and edge cites a real row
            for node in graph.nodes.values():
                self.assertTrue(node.sources, node.key)
                for s in node.sources:
                    self.assertIn(f"{s.version}:{s.file}:{s.line}", graph.rows)
            for edge in graph.edges:
                self.assertTrue(edge.sources)
                self.assertEqual(edge.status, "known")
            self.assertTrue((ws.imports_dir / info["version"] / "lots.csv").is_file(), "source bytes are kept")

    def test_reimport_of_identical_bytes_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws, first = workspace_with_fixture(tmp)
            before = ws.graph().summary()
            again = ws.import_dir(FIXTURE)
            self.assertFalse(again["new"])
            self.assertEqual(again["version"], first["version"])
            self.assertEqual(len(ws.imports()), 1)
            self.assertEqual(len(ws.imports()[0]["seen"]), 1)
            self.assertEqual(ws.graph().summary(), before)

    def test_changed_export_is_a_new_version_and_compare_names_the_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws, first = workspace_with_fixture(tmp)
            changed = copy_fixture(tmp)
            with (changed / "shipments.csv").open("a", encoding="utf-8", newline="") as fh:
                fh.write("pilot-plant,SHIP-10,PKG-P4-1,Cafe North,1000,L,2026-08-10\n")
            second = ws.import_dir(changed, label="corrected")
            self.assertTrue(second["new"])
            self.assertNotEqual(second["version"], first["version"])
            diff = ws.compare(first["version"], second["version"])
            self.assertEqual(diff["files"]["shipments.csv"]["only_in_a"], [])
            self.assertEqual([r["shipment_id"] for r in diff["files"]["shipments.csv"]["only_in_b"]], ["SHIP-10"])
            self.assertEqual(diff["files"]["lots.csv"]["only_in_b"], [])
            latest = ws.graph()
            self.assertIn(("pilot-plant", "shipment", "SHIP-10"), latest.nodes)
            old = ws.graph([first["version"]])
            self.assertNotIn(("pilot-plant", "shipment", "SHIP-10"), old.nodes)
            gaps_old = [f for f in old.facts if f["code"] == "package_without_shipment" and "pilot-plant/package/PKG-P4-1" in f["nodes"]]
            gaps_new = [f for f in latest.facts if f["code"] == "package_without_shipment" and "pilot-plant/package/PKG-P4-1" in f["nodes"]]
            self.assertEqual((len(gaps_old), len(gaps_new)), (1, 0), "the corrected export closes the gap; the old version still shows it")

    def test_empty_directory_is_refused_with_the_expected_file_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = engine.Workspace(Path(tmp) / "ws")
            with self.assertRaises(ValueError) as ctx:
                ws.import_dir(Path(tmp))
            self.assertIn("lots.csv", str(ctx.exception))
            with self.assertRaises(ValueError):
                ws.graph()


class ImpactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ws, cls.info = workspace_with_fixture(cls.tmp.name)
        cls.graph = cls.ws.graph()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_forward_impact_from_the_split_lot_matches_the_hand_derived_set(self):
        impact = self.graph.impact(CITRIC, "forward")
        known = {a["key"] for a in impact["affected"] if a["status"] == engine.STATUS_KNOWN}
        self.assertEqual(known, FORWARD_KNOWN_FROM_CITRIC)
        self.assertEqual({a["key"] for a in impact["affected"]} & NEVER_FROM_CITRIC, set())
        self.assertEqual(impact["counts"][engine.STATUS_POTENTIAL], 0, "no assumption asked, nothing potential")
        by_key = {a["key"]: a for a in impact["affected"]}
        # the rework edge is the only road to BATCH-P4, and it is cited to rework.csv line 2
        p4 = by_key["pilot-plant/batch/BATCH-P4"]
        self.assertEqual([e["relation"] for e in p4["path"]], ["split", "consumed", "consumed", "rework"])
        self.assertEqual(p4["path"][-1]["sources"], [{"version": self.info["version"], "file": "rework.csv", "line": 2}])
        self.assertEqual(by_key["sup-acme/lot/LOT-CITRIC-01A"]["hops"], 1)
        self.assertEqual(by_key["pilot-plant/shipment/SHIP-9"]["status"], engine.STATUS_KNOWN)
        for a in impact["affected"]:
            for e in a["path"]:
                self.assertTrue(e["sources"], "every edge on a path cites a row")

    def test_contradictions_and_gaps_on_the_path_are_reported_with_all_rows(self):
        impact = self.graph.impact(CITRIC, "forward")
        codes = sorted(f["code"] for f in impact["contradictions"])
        self.assertEqual(codes, ["multiple_shipped_links", "over_consumption"])
        over = next(f for f in impact["contradictions"] if f["code"] == "over_consumption")
        self.assertIn("sup-acme/lot/LOT-CITRIC-01B", over["nodes"])
        self.assertEqual(over["detail"]["lot_quantity"], 30.0)
        self.assertEqual(over["detail"]["consumed_total"], 40.0)
        self.assertTrue(any(s["file"] == "consumption.csv" for s in over["sources"]))
        ship9 = next(f for f in impact["contradictions"] if f["code"] == "multiple_shipped_links")
        self.assertIn("pilot-plant/shipment/SHIP-9", ship9["nodes"])
        self.assertEqual(sorted(s["line"] for s in ship9["sources"]), [7, 8])
        gaps = {(f["code"], f["nodes"][0]) for f in impact["coverage_gaps"]}
        self.assertIn(("package_without_shipment", "pilot-plant/package/PKG-P4-1"), gaps)
        self.assertNotIn("pilot-plant/package/PKG-P4-1", NEVER_FROM_CITRIC)
        self.assertIn("not that nothing happened", impact["note"])

    def test_global_facts_include_dangling_references_and_the_orphan_package(self):
        codes = sorted(f["code"] for f in self.graph.facts if f["kind"] == "unresolved")
        self.assertEqual(codes, ["consumed_input_not_in_records", "package_batch_not_in_records", "package_without_batch_link"])
        dangling = next(f for f in self.graph.facts if f["code"] == "package_batch_not_in_records")
        self.assertEqual(dangling["detail"]["batch_ref"], "pilot-plant/batch/BATCH-P9")
        vanilla = next(f for f in self.graph.facts if f["code"] == "consumed_input_not_in_records")
        self.assertEqual(vanilla["detail"]["input_ref"], "sup-acme/lot/LOT-VANILLA-09")
        self.assertEqual(vanilla["nodes"], ["pilot-plant/batch/BATCH-P4"])
        self.assertEqual(self.graph.cycles(), [])

    def test_assumption_turns_the_orphan_package_into_potentially_affected_with_the_name_on_the_edge(self):
        plain = self.graph.impact(CITRIC, "forward")
        self.assertNotIn("pilot-plant/package/PKG-ORPHAN-1", {a["key"] for a in plain["affected"]})
        assumed = self.graph.impact(CITRIC, "forward", ["unlinked_package_same_product_day"])
        by_key = {a["key"]: a for a in assumed["affected"]}
        orphan = by_key["pilot-plant/package/PKG-ORPHAN-1"]
        self.assertEqual(orphan["status"], engine.STATUS_POTENTIAL)
        self.assertEqual(orphan["assumptions_on_path"], ["unlinked_package_same_product_day"])
        last = orphan["path"][-1]
        self.assertEqual((last["from"], last["status"], last["assumption"]), ("pilot-plant/batch/BATCH-P2", "potential", "unlinked_package_same_product_day"))
        self.assertEqual(by_key["pilot-plant/shipment/SHIP-6"]["status"], engine.STATUS_POTENTIAL)
        known_now = {a["key"] for a in assumed["affected"] if a["status"] == engine.STATUS_KNOWN}
        self.assertEqual(known_now, FORWARD_KNOWN_FROM_CITRIC, "an assumption never promotes anything to KNOWN")
        with self.assertRaises(ValueError):
            self.graph.impact(CITRIC, "forward", ["no_such_rule"])

    def test_backward_from_a_shipment_names_every_contributing_lot_in_its_own_namespace(self):
        impact = self.graph.impact(("pilot-plant", "shipment", "SHIP-3"), "backward")
        self.assertEqual({a["key"] for a in impact["affected"]}, BACKWARD_FROM_SHIP3)
        self.assertTrue(all(a["status"] == engine.STATUS_KNOWN for a in impact["affected"]))
        by_key = {a["key"]: a for a in impact["affected"]}
        citric = by_key["sup-acme/lot/LOT-CITRIC-01"]
        # SHIP-3 <- PKG-P2-2 <- BATCH-P2 <- BATCH-P1 <- LOT-CITRIC-01A <- LOT-CITRIC-01
        self.assertEqual(citric["hops"], 5)
        self.assertEqual([e["relation"] for e in citric["path"]], ["shipped", "packed", "consumed", "consumed", "split"])
        self.assertEqual(citric["path"][0]["to"], "pilot-plant/shipment/SHIP-3")
        self.assertEqual(citric["path"][-1]["from"], "sup-acme/lot/LOT-CITRIC-01")
        self.assertEqual(by_key["sup-aqua/lot/LOT-WATER-01"]["hops"], 3)
        self.assertEqual(by_key["sup-h2o/lot/LOT-WATER-01"]["hops"], 4)

    def test_start_outside_the_records_is_said_plainly(self):
        impact = self.graph.impact(("sup-acme", "lot", "LOT-NOPE"), "forward")
        self.assertFalse(impact["start_found"])
        self.assertEqual(impact["affected"], [])
        self.assertEqual(impact["unresolved"][0]["code"], "start_not_in_records")
        with self.assertRaises(ValueError):
            engine.parse_key("just-an-id")

    def test_export_is_deterministic_and_markdown_carries_statuses_and_rows(self):
        impact = self.graph.impact(CITRIC, "forward", ["unlinked_package_same_product_day"])
        r1 = engine.build_report(self.ws, self.graph, impact)
        r2 = engine.build_report(self.ws, self.graph, self.graph.impact(CITRIC, "forward", ["unlinked_package_same_product_day"]))
        self.assertEqual(r1["content_sha256"], r2["content_sha256"])
        strip = lambda r: {k: v for k, v in r.items() if k != "generated_at"}
        self.assertEqual(strip(r1), strip(r2))
        md = engine.render_markdown(r1)
        self.assertIn("KNOWN_AFFECTED", md)
        self.assertIn("POTENTIALLY_AFFECTED", md)
        self.assertIn("rework.csv:2", md)
        self.assertIn("over_consumption", md)
        self.assertIn("`*` marks an edge", md)
        self.assertIn("unlinked_package_same_product_day", md)


class InvestigatorTests(unittest.TestCase):
    def test_annotations_keep_revisions_and_never_touch_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws, _ = workspace_with_fixture(tmp)
            before = ws.graph().summary()
            first = ws.annotate("pilot-plant/batch/BATCH-P3", "40 kg against a 30 kg lot: asking QA", investigator="A")
            second = ws.annotate("pilot-plant/batch/BATCH-P3", "QA confirms the consumption row is a typo for 4 kg", investigator="A", supersedes=first["id"])
            other = ws.annotate("pilot-plant/shipment/SHIP-9", "two packages on one shipment id: asking logistics", investigator="B")
            notes = ws.annotations("pilot-plant/batch/BATCH-P3")
            self.assertEqual([n["revision"] for n in notes], [1, 2])
            self.assertEqual([n["current"] for n in notes], [False, True])
            self.assertEqual(notes[1]["supersedes"], first["id"])
            self.assertEqual(len(ws.annotations()), 3)
            self.assertEqual(ws.graph().summary(), before, "annotating changes no observation")
            graph = ws.graph()
            report = engine.build_report(ws, graph, graph.impact(CITRIC, "forward"))
            targets = {a["target"] for a in report["annotations"]}
            self.assertEqual(targets, {"pilot-plant/batch/BATCH-P3", "pilot-plant/shipment/SHIP-9"})
            with self.assertRaises(ValueError):
                ws.annotate("pilot-plant/batch/BATCH-P3", "", investigator="A")
            with self.assertRaises(ValueError):
                ws.annotate("pilot-plant/batch/BATCH-P3", "x", supersedes="nope")
            _ = other

    def test_a_second_question_needs_no_stored_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws, _ = workspace_with_fixture(tmp)
            graph = ws.graph()
            first = graph.impact(CITRIC, "forward")
            second = graph.impact(("sup-aqua", "lot", "LOT-WATER-01"), "forward")
            self.assertEqual({a["key"] for a in second["affected"]} & {"pilot-plant/batch/BATCH-P2", "pilot-plant/batch/BATCH-P5"}, {"pilot-plant/batch/BATCH-P2", "pilot-plant/batch/BATCH-P5"})
            self.assertNotIn("pilot-plant/batch/BATCH-P1", {a["key"] for a in second["affected"]}, "the other water supplier is not this one")
            self.assertNotEqual({a["key"] for a in first["affected"]}, {a["key"] for a in second["affected"]})
            self.assertFalse(any(p.name in ("workflow.json", "plan.json", "steps.json") for p in ws.root.rglob("*")))
            cli = CLI.read_text(encoding="utf-8")
            for word in ("investigate", "autorun", "playbook"):
                self.assertNotIn(word, cli)


class RobustnessTests(unittest.TestCase):
    def test_rework_loop_is_reported_and_traversed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = copy_fixture(tmp)
            with (src / "rework.csv").open("a", encoding="utf-8", newline="") as fh:
                fh.write("pilot-plant,REW-02,BATCH-P4,BATCH-P2,50,L,2026-08-09\n")
            ws, _ = workspace_with_fixture(tmp, src)
            graph = ws.graph()
            cycles = graph.cycles()
            self.assertEqual(len(cycles), 1)
            self.assertEqual(sorted(engine.key_str(k) for k in cycles[0]), ["pilot-plant/batch/BATCH-P2", "pilot-plant/batch/BATCH-P4"])
            impact = graph.impact(("pilot-plant", "batch", "BATCH-P4"), "forward")
            keys = [a["key"] for a in impact["affected"]]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertIn("pilot-plant/batch/BATCH-P2", keys)
            self.assertEqual(impact["cycles"][0]["code"], "batch_cycle")

    def test_removing_the_rework_row_removes_batch_p4_from_the_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = copy_fixture(tmp)
            rewrite_csv(src / "rework.csv", lambda row: row["rework_id"] != "REW-01")
            ws, _ = workspace_with_fixture(tmp, src)
            impact = ws.graph().impact(CITRIC, "forward")
            keys = {a["key"] for a in impact["affected"]}
            self.assertNotIn("pilot-plant/batch/BATCH-P4", keys)
            self.assertNotIn("pilot-plant/package/PKG-P4-1", keys)
            self.assertEqual(keys, FORWARD_KNOWN_FROM_CITRIC - {"pilot-plant/batch/BATCH-P4", "pilot-plant/package/PKG-P4-1"})

    def test_unit_mismatch_and_duplicate_link_quantities_are_contradictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = copy_fixture(tmp)
            with (src / "consumption.csv").open("a", encoding="utf-8", newline="") as fh:
                fh.write("pilot-plant,BATCH-P5,sup-acme,lot,LOT-SUGAR-02,10,L\n")
                fh.write("pilot-plant,BATCH-P1,sup-acme,lot,LOT-CITRIC-01A,12,kg\n")
            ws, _ = workspace_with_fixture(tmp, src)
            codes = sorted(f["code"] for f in ws.graph().facts if f["kind"] == "contradiction")
            self.assertIn("unit_mismatch", codes)
            self.assertIn("duplicate_link_different_quantity", codes)


class CliTests(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        proc = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=cwd or ROOT, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_cli_round_trip_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = str(Path(tmp) / "ws")
            imported = self.run_cli("-w", ws, "import", str(FIXTURE), "--label", "pilot")
            self.assertTrue(imported["new"])
            summary = self.run_cli("-w", ws, "summary")
            self.assertEqual(summary["nodes"]["lot"], 7)
            found = self.run_cli("-w", ws, "find", "LOT-WATER-01")
            self.assertEqual(len(found["matches"]), 2)
            inspected = self.run_cli("-w", ws, "inspect", "pilot-plant/batch/BATCH-P3")
            self.assertTrue(inspected["found"])
            self.assertIn("batches.csv:4", inspected["source_rows"])
            self.assertEqual(inspected["source_rows"]["batches.csv:4"]["batch_id"], "BATCH-P3")
            upstream_rows = {(s["file"], s["line"]) for e in inspected["upstream"] for s in e["sources"]}
            self.assertEqual(upstream_rows, {("consumption.csv", 7), ("consumption.csv", 8)})
            self.assertTrue(any(f["code"] == "over_consumption" for f in inspected["facts"]))
            out_json, out_md = Path(tmp) / "r.json", Path(tmp) / "r.md"
            brief = self.run_cli("-w", ws, "impact", "sup-acme/lot/LOT-CITRIC-01", "--brief", "--out", str(out_json), "--md", str(out_md))
            self.assertEqual(brief["counts"]["KNOWN_AFFECTED"], len(FORWARD_KNOWN_FROM_CITRIC))
            by_key = {a["key"]: a for a in brief["affected"]}
            self.assertEqual(by_key["sup-acme/lot/LOT-CITRIC-01A"]["detail"], "citric acid Acme Acids")
            self.assertEqual(by_key["pilot-plant/shipment/SHIP-3"]["detail"], "Market South")
            p4 = by_key["pilot-plant/batch/BATCH-P4"]["path"]
            self.assertEqual(len(p4), 4)
            self.assertTrue(p4[-1].startswith("pilot-plant/batch/BATCH-P2 -rework-> pilot-plant/batch/BATCH-P4 (rework.csv:2@"), p4[-1])
            summarised = self.run_cli("-w", ws, "impact", "pilot-plant/shipment/SHIP-3", "--backward", "--paths", "summary")
            first = summarised["impact"]["affected"][0]
            self.assertIsInstance(first["path"][0], str)
            self.assertIn("what |", out_md.read_text(encoding="utf-8"))
            self.assertIn("| citric acid Acme Acids |", out_md.read_text(encoding="utf-8"))
            full_written = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertIsInstance(full_written["impact"]["affected"][0]["path"][0], dict, "files keep the full edge objects")
            report = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(report["content_sha256"], brief["content_sha256"])
            self.assertIn("# LotLens impact report", out_md.read_text(encoding="utf-8"))
            note = self.run_cli("-w", ws, "annotate", "pilot-plant/batch/BATCH-P3", "asking QA", "--by", "CLI")
            self.assertEqual(note["revision"], 1)
            facts = self.run_cli("-w", ws, "facts", "--kind", "contradiction")
            self.assertEqual(facts["count"], 2)
            assumptions = self.run_cli("assumptions")
            self.assertIn("unlinked_package_same_product_day", assumptions)
            proc = subprocess.run([sys.executable, str(CLI), "-w", ws, "impact", "bad-key"], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("namespace/kind/id", json.loads(proc.stdout)["message"])


class PageTests(unittest.TestCase):
    def test_viewer_page_loads_nothing_but_the_file_it_is_given(self):
        page = (ROOT / "lotlens" / "app.html").read_text(encoding="utf-8")
        self.assertNotIn("<script src", page)
        self.assertNotIn("http://", page.replace("http-equiv", ""))
        self.assertNotIn("https://", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("XMLHttpRequest", page)
        self.assertNotIn("localStorage", page)
        self.assertIn('name="robots" content="index, follow"', page)
        self.assertIn("KNOWN_AFFECTED", page)
        self.assertIn("annotations.json", page)


if __name__ == "__main__":
    unittest.main()
