"""Tests for the milestone packet kit (UIOWA-135).

Two of these are the safety property rather than a behaviour check:
`TestNoDestructiveFilesystemOperations` asserts, statically and at runtime, that
this tooling cannot delete, move, rename, or truncate anything. A packet builder
that runs against a directory of delivered client artifacts and *could* remove
one is a liability, so the absence of that capability is part of the deliverable
and is asserted rather than promised.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import completeness
import packets
import resolve
import schedule
import schema
from schema import UNKNOWN, Engagement, ForbiddenClaimError, Money, PacketError

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "engagement.json")
ARTIFACT_ROOT = os.path.join(HERE, "fixtures", "artifacts")
AS_OF = "2026-11-25"

# The modules that make up the shipped tool. The test file itself is excluded:
# it legitimately creates and cleans up temp directories.
PRODUCTION_MODULES = (
    "schema.py", "resolve.py", "schedule.py",
    "completeness.py", "packets.py", "milestone_packets.py",
)


def load_raw() -> dict:
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_report(raw: dict, as_of: str = AS_OF, root: str = ARTIFACT_ROOT):
    eng = Engagement.from_json(raw)
    res = resolve.resolve_all(eng, root)
    return eng, res, completeness.check(eng, res, as_of)


def codes(report) -> list:
    return [f.code for f in report.all_findings]


def hash_tree(root: str) -> dict:
    """relpath -> sha256 for every file under root. The safety-test oracle."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            with open(full, "rb") as fh:
                out[os.path.relpath(full, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


class TestMoney(unittest.TestCase):
    def test_parses_to_integer_cents(self):
        self.assertEqual(Money.parse("4,800.00").cents, 480_000)
        self.assertEqual(Money.parse("$9,600.00").cents, 960_000)
        self.assertEqual(Money.parse(2_400_000).cents, 2_400_000)   # int == cents
        self.assertEqual(Money.parse("$24000.00").cents, 2_400_000)

    def test_bare_digit_string_is_refused_as_ambiguous(self):
        """int 24000 means cents, so "24000" could mean $240 or $24,000.

        Found by this suite: the parser originally read it as dollars while the
        int path read cents -- a silent factor-of-100 disagreement between two
        ways of writing the same amount. Now it raises instead of picking one.
        """
        with self.assertRaises(schema.MoneyTypeError) as ctx:
            Money.parse("24000")
        self.assertIn("ambiguous", str(ctx.exception))

    def test_float_dollars_are_refused(self):
        # The whole reason for integer cents: floats let a wrong total print right.
        with self.assertRaises(schema.MoneyTypeError):
            Money.parse(4800.00)
        with self.assertRaises(schema.MoneyTypeError):
            Money(4800.00)

    def test_bool_is_not_an_amount(self):
        with self.assertRaises(schema.MoneyTypeError):
            Money.parse(True)

    def test_money_only_adds_to_money(self):
        self.assertEqual((Money(1) + Money(2)).cents, 3)
        with self.assertRaises(schema.MoneyTypeError):
            Money(1) + 2

    def test_display(self):
        self.assertEqual(Money(2_400_000).dollars(), "$24,000.00")


class TestUnknown(unittest.TestCase):
    def test_unknown_has_no_arithmetic_and_no_truthiness(self):
        for op in (lambda: UNKNOWN + 1, lambda: 1 + UNKNOWN, lambda: UNKNOWN * 2,
                   lambda: float(UNKNOWN), lambda: int(UNKNOWN), lambda: bool(UNKNOWN),
                   lambda: UNKNOWN < 5):
            with self.assertRaises(schema.UnknownUsedAsValueError):
                op()

    def test_unknown_is_a_singleton(self):
        self.assertIs(schema.opt(None), UNKNOWN)
        self.assertIs(schema.opt(""), UNKNOWN)
        self.assertIs(schema._Unknown(), UNKNOWN)


class TestAmounts(unittest.TestCase):
    def test_fixture_totals_exactly_24000(self):
        eng, _, report = build_report(load_raw())
        self.assertEqual(eng.milestone_total().cents, 2_400_000)
        self.assertEqual(eng.milestone_total().dollars(), "$24,000.00")
        self.assertIn("I_AMOUNTS_CONFIRMED", codes(report))
        self.assertNotIn("E_AMOUNTS_DO_NOT_SUM", codes(report))

    def test_one_cent_short_fails(self):
        """8000.00 + 8000.00 + 7999.99 prints like $24,000 and is not."""
        raw = load_raw()
        for ms, amount in zip(raw["milestones"], ("8,000.00", "8,000.00", "7,999.99")):
            ms["amount"] = amount
        _, _, report = build_report(raw)
        self.assertIn("E_AMOUNTS_DO_NOT_SUM", codes(report))
        self.assertFalse(report.passed)

    def test_contract_total_must_be_24000(self):
        raw = load_raw()
        raw["contract_total"] = "30,000.00"
        _, _, report = build_report(raw)
        self.assertIn("E_CONTRACT_TOTAL_MISMATCH", codes(report))


class TestDeliveryIsNotAcceptance(unittest.TestCase):
    def test_delivered_without_record_is_pending(self):
        eng, _, _ = build_report(load_raw())
        m2 = {m.milestone_id: m for m in eng.milestones}["M-2"]
        self.assertEqual(m2.submission_state, "DELIVERED")
        self.assertIs(m2.acceptance, UNKNOWN)
        self.assertEqual(m2.acceptance_state, "PENDING")

    def test_acceptance_requires_a_dated_record(self):
        eng, _, _ = build_report(load_raw())
        m1 = {m.milestone_id: m for m in eng.milestones}["M-1"]
        self.assertEqual(m1.acceptance_state, "ACCEPTED_RECORDED")
        self.assertEqual(m1.acceptance.recorded_on, "2026-10-09")

    def test_undelivered_milestone_is_not_requested(self):
        eng, _, _ = build_report(load_raw())
        m3 = {m.milestone_id: m for m in eng.milestones}["M-3"]
        self.assertEqual(m3.acceptance_state, "NOT_REQUESTED")

    def test_draft_and_final_are_distinct_milestones(self):
        eng, _, report = build_report(load_raw())
        kinds = [m.kind for m in eng.milestones]
        self.assertEqual(sorted(kinds), ["DRAFT_DELIVERY", "FINAL_ACCEPTANCE", "KICKOFF"])
        self.assertNotIn("E_DUPLICATE_MILESTONE_KIND", codes(report))

    def test_duplicate_kind_is_an_error(self):
        raw = load_raw()
        raw["milestones"][2]["kind"] = "DRAFT_DELIVERY"
        _, _, report = build_report(raw)
        self.assertIn("E_DUPLICATE_MILESTONE_KIND", codes(report))
        self.assertIn("E_MISSING_MILESTONE_KIND", codes(report))

    def test_billing_state_is_always_draft(self):
        eng, _, _ = build_report(load_raw())
        for ms in eng.milestones:
            self.assertEqual(ms.billing_state, "DRAFT_NOT_ISSUED")


class TestForbiddenClaims(unittest.TestCase):
    def test_input_claiming_payment_is_rejected(self):
        raw = load_raw()
        raw["milestones"][0]["billing_state"] = "PAID"
        with self.assertRaises(ForbiddenClaimError):
            Engagement.from_json(raw)

    def test_input_claiming_acceptance_without_record_is_rejected(self):
        raw = load_raw()
        raw["milestones"][1]["status"] = "ACCEPTED"
        with self.assertRaises(ForbiddenClaimError):
            Engagement.from_json(raw)

    def test_prose_claiming_an_issued_invoice_is_refused(self):
        with self.assertRaises(ForbiddenClaimError):
            packets.assert_no_forbidden_claim(
                "Milestone 2 complete; invoice issued 2026-11-20.", "T", False
            )

    def test_payment_claims_refused_even_with_an_acceptance_record(self):
        # Acceptance on record never licenses a payment claim.
        with self.assertRaises(ForbiddenClaimError):
            packets.assert_no_forbidden_claim("Paid in full.", "T", True)

    def test_acceptance_prose_refused_without_a_record(self):
        with self.assertRaises(ForbiddenClaimError):
            packets.assert_no_forbidden_claim(
                "Delivered and accepted on the 14th.", "T", False
            )

    def test_acceptance_prose_allowed_with_a_record(self):
        packets.assert_no_forbidden_claim(
            "Accepted on 2026-10-09, ref SYN-ACK-M1-0001.", "T", True
        )

    def test_negations_are_not_false_positives(self):
        packets.assert_no_forbidden_claim(schema.DRAFT_STAMP, "T", False)
        packets.assert_no_forbidden_claim(
            "Delivery is not acceptance; acceptance is pending.", "T", False
        )


class TestResolution(unittest.TestCase):
    def test_missing_artifact_never_becomes_a_pass_or_a_zero(self):
        _, res, report = build_report(load_raw())
        missing = res["IDX-M3-002"]
        self.assertEqual(missing.state, resolve.UNRESOLVED_MISSING)
        self.assertFalse(missing.opens)
        self.assertIs(missing.size_bytes, UNKNOWN)   # not 0
        self.assertIs(missing.sha256, UNKNOWN)       # not ""
        self.assertIn("E_ARTIFACT_DOES_NOT_OPEN", codes(report))

    def test_resolved_artifact_carries_size_and_digest(self):
        _, res, _ = build_report(load_raw())
        ok = res["IDX-M1-001"]
        self.assertTrue(ok.opens)
        self.assertEqual(len(ok.sha256), 64)
        self.assertGreater(ok.size_bytes, 0)
        self.assertTrue(ok.version_identifiable)

    def test_opened_but_unversioned_is_still_an_error(self):
        """The subtle one: the file opens, so a naive checker passes it."""
        _, res, report = build_report(load_raw())
        item = res["IDX-M3-003"]
        self.assertTrue(item.opens)
        self.assertEqual(len(item.sha256), 64)
        self.assertIs(item.declared_version, UNKNOWN)
        self.assertFalse(item.version_identifiable)
        self.assertIn("E_VERSION_NOT_IDENTIFIABLE", codes(report))

    def test_path_escaping_the_artifact_root_is_refused_unread(self):
        item = schema.IndexItem.from_json(
            {"item_id": "X", "path": "../../../../etc/passwd", "title": "hostile"}
        )
        r = resolve.resolve_item(item, ARTIFACT_ROOT)
        self.assertEqual(r.state, resolve.UNRESOLVED_OUTSIDE_ROOT)
        self.assertIs(r.sha256, UNKNOWN)


class TestCompleteness(unittest.TestCase):
    def test_missing_disposition_fails_and_is_not_defaulted(self):
        eng, _, report = build_report(load_raw())
        self.assertIn("E_MISSING_DISPOSITION", codes(report))
        m3 = {m.milestone_id: m for m in eng.milestones}["M-3"]
        item = {i.item_id: i for i in m3.index_items}["IDX-M3-003"]
        self.assertIs(item.disposition, UNKNOWN)   # still undecided, not filled in

    def test_every_item_needs_source_custodian_and_location(self):
        raw = load_raw()
        item = raw["milestones"][0]["index_items"][0]
        item["custodian"] = None
        item["storage_location"] = ""
        del item["source"]
        _, _, report = build_report(raw)
        for code in ("E_MISSING_CUSTODIAN", "E_MISSING_STORAGE_LOCATION", "E_MISSING_SOURCE"):
            self.assertIn(code, codes(report))

    def test_clean_milestones_are_ready_and_dirty_one_is_not(self):
        _, _, report = build_report(load_raw())
        by_id = {mr.milestone_id: mr for mr in report.milestone_results}
        self.assertEqual(by_id["M-1"].status, "READY_TO_SUBMIT_AS_DRAFT")
        self.assertEqual(by_id["M-2"].status, "READY_TO_SUBMIT_AS_DRAFT")
        self.assertEqual(by_id["M-3"].status, "NOT_READY")
        self.assertEqual(len(by_id["M-3"].errors), 3)
        self.assertFalse(report.passed)

    def test_warnings_do_not_block_a_packet(self):
        """An overdue dependency is a real condition, not a packet defect."""
        _, _, report = build_report(load_raw())
        by_id = {mr.milestone_id: mr for mr in report.milestone_results}
        self.assertEqual(len(by_id["M-2"].warnings), 1)
        self.assertEqual(by_id["M-2"].warnings[0].code, "W_DEPENDENCY_OVERDUE")
        self.assertEqual(by_id["M-2"].status, "READY_TO_SUBMIT_AS_DRAFT")

    def test_dangling_criterion_reference(self):
        raw = load_raw()
        raw["milestones"][0]["index_items"][0]["criteria_ids"] = ["C-DOES-NOT-EXIST"]
        _, _, report = build_report(raw)
        self.assertIn("E_DANGLING_CRITERION_REF", codes(report))

    def test_criterion_citing_a_missing_index_item(self):
        raw = load_raw()
        raw["milestones"][0]["criteria"][0]["evidence_item_ids"] = ["IDX-NOPE"]
        _, _, report = build_report(raw)
        self.assertIn("E_CRITERION_CITES_MISSING_ITEM", codes(report))

    def test_empty_index_is_an_error(self):
        raw = load_raw()
        raw["milestones"][0]["index_items"] = []
        raw["milestones"][0]["criteria"] = []
        _, _, report = build_report(raw)
        self.assertIn("E_EMPTY_INDEX", codes(report))


class TestSchedule(unittest.TestCase):
    def test_overdue_is_measured_not_guessed(self):
        st = schedule.classify_due("2026-11-10", "2026-11-25")
        self.assertEqual(st.state, schedule.OVERDUE)
        self.assertEqual(st.days_remaining, -15)

    def test_undated_open_item_is_neither_on_time_nor_late(self):
        st = schedule.classify_due(UNKNOWN, "2026-11-25")
        self.assertEqual(st.state, schedule.DUE_UNKNOWN)
        self.assertIs(st.days_remaining, UNKNOWN)

    def test_due_today_and_upcoming(self):
        self.assertEqual(schedule.classify_due("2026-11-25", "2026-11-25").state,
                         schedule.DUE_TODAY)
        self.assertEqual(schedule.classify_due("2026-12-12", "2026-11-25").state,
                         schedule.UPCOMING)

    def test_post_completion_window_is_calendar_days(self):
        """The 30-day post-completion obligation window, computed not asserted."""
        self.assertEqual(schedule.deadline_from("2026-11-20", 30), "2026-12-20")
        self.assertEqual(schedule.deadline_from("2026-12-12", 30), "2027-01-11")

    def test_unknown_completion_gives_unknown_deadline(self):
        self.assertIs(schedule.deadline_from(UNKNOWN, 30), UNKNOWN)
        self.assertIs(schedule.days_between(UNKNOWN, "2026-11-25"), UNKNOWN)

    def test_invalid_date_is_rejected(self):
        with self.assertRaises(schema.SchemaError):
            schedule.parse_date("2026-02-30")
        with self.assertRaises(schema.SchemaError):
            schedule.parse_date("11/25/2026")


class TestMalformedInput(unittest.TestCase):
    def test_malformed_json_gives_a_located_diagnostic(self):
        import milestone_packets
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write('{"engagement_id": "X",,}')
            with self.assertRaises(PacketError) as ctx:
                milestone_packets.load_engagement(bad)
        self.assertIn("line", str(ctx.exception))

    def test_missing_required_field_names_the_field(self):
        with self.assertRaises(schema.SchemaError) as ctx:
            Engagement.from_json({"engagement_id": "X"})
        self.assertIn("title", str(ctx.exception))

    def test_unknown_disposition_value_is_rejected(self):
        with self.assertRaises(schema.SchemaError):
            schema.IndexItem.from_json(
                {"item_id": "X", "path": "p", "title": "t", "disposition": "SHRED_MAYBE"}
            )


class TestNoDestructiveFilesystemOperations(unittest.TestCase):
    """The safety property. Asserted, not promised.

    This kit is pointed at a directory of delivered client artifacts. If it could
    remove, move, rename, or truncate one, a routine "regenerate the packets" run
    could destroy the very evidence the packet exists to account for.
    """

    # Unambiguous destroyers: no stdlib type has a harmless method by these names.
    FORBIDDEN_LEAF = {"rmtree", "removedirs", "unlink", "rmdir", "truncate"}
    # Names that are only destructive in a filesystem module (str.replace is fine).
    FORBIDDEN_DOTTED = {
        "os.remove", "os.unlink", "os.rmdir", "os.removedirs", "os.truncate",
        "os.rename", "os.renames", "os.replace", "os.system", "os.chmod", "os.chown",
        "shutil.rmtree", "shutil.move", "shutil.copy", "shutil.copy2", "shutil.copyfile",
        "subprocess.run", "subprocess.call", "subprocess.Popen",
        "pathlib.Path.unlink", "Path.unlink", "Path.rmdir", "Path.replace", "Path.rename",
        "Path.write_text", "Path.write_bytes",
    }
    WRITE_MODES = set("wax+")
    APPROVED_WRITER = "write_output"

    @staticmethod
    def _dotted(node: ast.AST):
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return ".".join(reversed(parts)) if parts else None

    def _sources(self):
        for name in PRODUCTION_MODULES:
            path = os.path.join(HERE, name)
            with open(path, "r", encoding="utf-8") as fh:
                yield name, fh.read()

    def test_no_destructive_calls_anywhere_in_the_tool(self):
        offenders = []
        for name, src in self._sources():
            for node in ast.walk(ast.parse(src)):
                if not isinstance(node, ast.Call):
                    continue
                dotted = self._dotted(node.func)
                if dotted is None:
                    continue
                leaf = dotted.rsplit(".", 1)[-1]
                if leaf in self.FORBIDDEN_LEAF or dotted in self.FORBIDDEN_DOTTED:
                    offenders.append(f"{name}:{node.lineno} {dotted}()")
        self.assertEqual(offenders, [], f"destructive call(s) found: {offenders}")

    def test_no_destructive_names_are_even_imported(self):
        offenders = []
        for name, src in self._sources():
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.ImportFrom) and node.module in ("os", "shutil", "pathlib"):
                    for alias in node.names:
                        if alias.name in self.FORBIDDEN_LEAF or alias.name in (
                            "remove", "rename", "replace", "move", "system"
                        ):
                            offenders.append(f"{name}:{node.lineno} from {node.module} import {alias.name}")
        self.assertEqual(offenders, [], f"destructive import(s): {offenders}")

    def test_only_the_approved_writer_opens_a_file_for_writing(self):
        offenders = []
        for name, src in self._sources():
            tree = ast.parse(src)
            # Map every node to its enclosing function so a write can be attributed.
            enclosing = {}
            for fn in ast.walk(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in ast.walk(fn):
                        enclosing.setdefault(child, fn.name)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "open"):
                    continue
                mode = ""
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = str(node.args[1].value)
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = str(kw.value.value)
                if set(mode) & self.WRITE_MODES:
                    fn_name = enclosing.get(node, "<module>")
                    if fn_name != self.APPROVED_WRITER:
                        offenders.append(f"{name}:{node.lineno} open(mode={mode!r}) in {fn_name}()")
        self.assertEqual(offenders, [], f"unapproved write(s): {offenders}")

    def test_writer_refuses_to_escape_the_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out")
            os.makedirs(out)
            for bad in ("../escaped.txt", "a/../../escaped.txt", "/tmp/escaped.txt"):
                with self.assertRaises(ValueError, msg=f"{bad} should be refused"):
                    packets.write_output(out, bad, "x")
            self.assertFalse(os.path.exists(os.path.join(tmp, "escaped.txt")))

    def test_full_run_leaves_the_input_tree_byte_identical(self):
        """The runtime half: hash every cited artifact before and after a build."""
        with tempfile.TemporaryDirectory() as tmp:
            src_root = os.path.join(tmp, "artifacts")
            shutil.copytree(ARTIFACT_ROOT, src_root)
            before = hash_tree(src_root)
            self.assertGreater(len(before), 0)

            out = os.path.join(tmp, "out")
            eng, res, report = build_report(load_raw(), root=src_root)
            packets.build(eng, res, report, out, AS_OF)

            after = hash_tree(src_root)
            self.assertEqual(before, after, "the tool modified its input tree")
            self.assertEqual(sorted(before), sorted(after), "files were added or removed")

    def test_build_writes_only_inside_the_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out")
            sibling = os.path.join(tmp, "sibling")
            os.makedirs(sibling)
            eng, res, report = build_report(load_raw())
            written = packets.build(eng, res, report, out, AS_OF)
            root = os.path.realpath(out)
            for path in written:
                self.assertTrue(
                    os.path.realpath(path).startswith(root + os.sep),
                    f"{path} is outside {root}",
                )
            self.assertEqual(os.listdir(sibling), [])


class TestBuildOutputs(unittest.TestCase):
    def test_three_packet_folders_with_the_required_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            eng, res, report = build_report(load_raw())
            packets.build(eng, res, report, tmp, AS_OF)
            folders = sorted(os.listdir(os.path.join(tmp, "packets")))
            self.assertEqual(len(folders), 3)
            for folder in folders:
                for required in ("PACKET.md", "TRANSMITTAL.md",
                                 "INVOICE_DESCRIPTION_DRAFT.md",
                                 "delivered_file_index.csv", "packet.json"):
                    self.assertTrue(
                        os.path.isfile(os.path.join(tmp, "packets", folder, required)),
                        f"{folder}/{required} missing",
                    )
            self.assertTrue(os.path.isfile(os.path.join(tmp, "COMPLETENESS_REPORT.md")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "completeness_report.json")))

    def test_every_document_carries_the_draft_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            eng, res, report = build_report(load_raw())
            written = packets.build(eng, res, report, tmp, AS_OF)
            for path in written:
                if not path.endswith((".md",)) or path.endswith("COMPLETENESS_REPORT.md"):
                    continue
                with open(path, "r", encoding="utf-8") as fh:
                    self.assertIn(schema.DRAFT_STAMP, fh.read(), f"{path} unstamped")

    def test_index_csv_carries_custody_and_disposition_columns(self):
        eng, res, _ = build_report(load_raw())
        csv_text = packets.render_index_csv(eng.milestones[2], res)
        header = csv_text.splitlines()[0]
        for column in ("source", "custodian", "storage_location", "disposition"):
            self.assertIn(column, header)
        self.assertIn("UNKNOWN", csv_text)   # the undecided disposition survives

    def test_output_is_deterministic(self):
        """No clock, no RNG: two runs of the same inputs are byte-identical."""
        with tempfile.TemporaryDirectory() as tmp:
            a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            for target in (a, b):
                eng, res, report = build_report(load_raw())
                packets.build(eng, res, report, target, AS_OF)
            self.assertEqual(hash_tree(a), hash_tree(b))

    def test_cli_exit_codes(self):
        import milestone_packets
        with tempfile.TemporaryDirectory() as tmp:
            rc = milestone_packets.main([
                FIXTURE, "--artifact-root", ARTIFACT_ROOT,
                "--output-dir", os.path.join(tmp, "out"), "--as-of", AS_OF,
            ])
            self.assertEqual(rc, 1, "fixture has known gaps, so completeness fails")
            rc = milestone_packets.main([
                os.path.join(tmp, "nope.json"), "--output-dir", os.path.join(tmp, "o2"),
            ])
            self.assertEqual(rc, 2, "unreadable input is a tool error, not a gap")


if __name__ == "__main__":
    unittest.main(verbosity=2)
