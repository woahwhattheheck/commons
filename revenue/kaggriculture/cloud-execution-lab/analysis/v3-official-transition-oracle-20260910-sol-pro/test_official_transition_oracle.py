#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import textwrap
import unittest

from official_transition_corpus import (
    atomic_plant_fixture,
    build_fixture_map,
    run_corpus,
)
from official_transition_oracle import (
    EXPECTED_ENGINE_GIT_BLOB,
    OracleError,
    run_fixture,
    semantic_hash,
    strict_loads,
    validate_envelope,
    write_json_atomic,
)

HERE = Path(__file__).resolve().parent
ENGINE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py"
)


def find_repo_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / ENGINE_REL).is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO = find_repo_root()
ENGINE = REPO / ENGINE_REL
WORKER = HERE / "official_transition_worker.py"


class OfficialTransitionCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence, cls.envelopes = run_corpus(
            engine_path=ENGINE,
            worker_path=WORKER,
        )

    def test_full_predecessor_corpus_passes(self):
        self.assertTrue(self.evidence["all_contracts_passed"])
        self.assertEqual(len(self.evidence["cases"]), 24)
        self.assertEqual(
            self.evidence["prior_compact_oracle"]["pr"],
            11700,
        )

    def test_corpus_evidence_hash_is_self_consistent(self):
        claimed = self.evidence["evidence_sha256"]
        body = dict(self.evidence)
        del body["evidence_sha256"]
        self.assertEqual(semantic_hash(body), claimed)

    def test_every_envelope_is_valid_and_source_pinned(self):
        for name, envelope in self.envelopes.items():
            with self.subTest(name=name):
                validate_envelope(envelope)
                self.assertEqual(
                    envelope["source"]["engine_git_blob"],
                    EXPECTED_ENGINE_GIT_BLOB,
                )
                worker = envelope["worker_receipt"]
                self.assertTrue(worker["engine_unchanged"])
                sequences = [
                    event["sequence"]
                    for row in worker["steps"]
                    for event in row["events"]
                ]
                # Sequence restarts at zero at each step; each row is contiguous.
                for row in worker["steps"]:
                    self.assertEqual(
                        [event["sequence"] for event in row["events"]],
                        list(range(len(row["events"]))),
                    )
                self.assertGreaterEqual(len(sequences), len(worker["steps"]))

    def test_determinism_on_exact_same_fixture(self):
        fixture = atomic_plant_fixture()
        first = run_fixture(engine_path=ENGINE, worker_path=WORKER, fixture=fixture)
        second = run_fixture(engine_path=ENGINE, worker_path=WORKER, fixture=fixture)
        self.assertEqual(first, second)

    def test_metamorphic_cases_have_different_authored_actions(self):
        fixtures = build_fixture_map()
        pairs = (
            ("suffix_control", "suffix_variant"),
            ("current_horizon_control", "current_horizon_variant"),
            ("future_horizon_control", "future_horizon_variant"),
            ("minimum_one_control", "minimum_one_variant"),
        )
        for left, right in pairs:
            with self.subTest(pair=(left, right)):
                self.assertNotEqual(
                    semantic_hash(fixtures[left]["steps"]),
                    semantic_hash(fixtures[right]["steps"]),
                )
                self.assertEqual(
                    self.envelopes[left]["worker_receipt"]["terminal_state_sha256"],
                    self.envelopes[right]["worker_receipt"]["terminal_state_sha256"],
                )


class ProtocolAndCustodyTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            strict_loads('{"x":1,"x":2}')

    def test_nonfinite_json_is_rejected(self):
        for text in ('{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, "non-finite"):
                    strict_loads(text)

    def test_unknown_fixture_surface_is_rejected(self):
        fixture = atomic_plant_fixture()
        fixture["surprise"] = True
        with self.assertRaisesRegex(OracleError, "unknown top-level"):
            run_fixture(engine_path=ENGINE, worker_path=WORKER, fixture=fixture)

    def test_noncontiguous_steps_are_rejected(self):
        fixture = atomic_plant_fixture()
        fixture["steps"][0]["step"] = 2
        with self.assertRaisesRegex(OracleError, "contiguous value"):
            run_fixture(engine_path=ENGINE, worker_path=WORKER, fixture=fixture)

    def test_engine_source_drift_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory(prefix="titan-engine-drift-") as temp:
            drifted = Path(temp) / ENGINE_REL
            drifted.parent.mkdir(parents=True)
            drifted.write_bytes(ENGINE.read_bytes() + b"\n# drift\n")
            with self.assertRaisesRegex(OracleError, "engine Git blob mismatch"):
                run_fixture(
                    engine_path=drifted,
                    worker_path=WORKER,
                    fixture=atomic_plant_fixture(),
                )

    def test_engine_copy_outside_bound_path_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="titan-engine-alias-") as temp:
            copied = Path(temp) / "kaggriculture.py"
            copied.write_bytes(ENGINE.read_bytes())
            with self.assertRaisesRegex(OracleError, "engine path must end"):
                run_fixture(
                    engine_path=copied,
                    worker_path=WORKER,
                    fixture=atomic_plant_fixture(),
                )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_symlinked_worker_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="titan-worker-link-") as temp:
            linked = Path(temp) / "worker.py"
            linked.symlink_to(WORKER)
            with self.assertRaisesRegex(OracleError, "must not be a symlink"):
                run_fixture(
                    engine_path=ENGINE,
                    worker_path=linked,
                    fixture=atomic_plant_fixture(),
                )

    def _fake_worker(self, source: str):
        temp = tempfile.TemporaryDirectory(prefix="titan-fake-worker-")
        path = Path(temp.name) / "worker.py"
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return temp, path

    def test_extra_stdout_lines_are_rejected(self):
        temp, fake = self._fake_worker(
            """
            import sys
            sys.stdin.buffer.read()
            print('{}')
            print('{}')
            """
        )
        try:
            with self.assertRaisesRegex(OracleError, "extra stdout lines"):
                run_fixture(
                    engine_path=ENGINE,
                    worker_path=fake,
                    fixture=atomic_plant_fixture(),
                )
        finally:
            temp.cleanup()

    def test_stderr_is_rejected(self):
        temp, fake = self._fake_worker(
            """
            import sys
            sys.stdin.buffer.read()
            sys.stderr.write('noise')
            print('{}')
            """
        )
        try:
            with self.assertRaisesRegex(OracleError, "wrote stderr"):
                run_fixture(
                    engine_path=ENGINE,
                    worker_path=fake,
                    fixture=atomic_plant_fixture(),
                )
        finally:
            temp.cleanup()

    def test_timeout_is_fail_closed(self):
        temp, fake = self._fake_worker(
            """
            import sys, time
            sys.stdin.buffer.read()
            time.sleep(2)
            print('{}')
            """
        )
        try:
            with self.assertRaisesRegex(OracleError, "exceeded timeout"):
                run_fixture(
                    engine_path=ENGINE,
                    worker_path=fake,
                    fixture=atomic_plant_fixture(),
                    timeout_seconds=0.05,
                )
        finally:
            temp.cleanup()

    def test_envelope_tamper_is_rejected(self):
        envelope = run_fixture(
            engine_path=ENGINE,
            worker_path=WORKER,
            fixture=atomic_plant_fixture(),
        )
        tampered = copy.deepcopy(envelope)
        tampered["worker_receipt"]["terminal_state"]["farms"][0]["money"] += 1
        with self.assertRaisesRegex(OracleError, "envelope hash mismatch"):
            validate_envelope(tampered)

    def test_atomic_writer_refuses_overwrite_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix="titan-atomic-output-") as temp:
            root = Path(temp)
            target = root / "evidence.json"
            write_json_atomic(target, {"ok": True})
            self.assertEqual(json.loads(target.read_text()), {"ok": True})
            with self.assertRaisesRegex(OracleError, "already exists"):
                write_json_atomic(target, {"ok": False})
            link = root / "link.json"
            if hasattr(os, "symlink"):
                link.symlink_to(target)
                with self.assertRaisesRegex(OracleError, "already exists"):
                    write_json_atomic(link, {"ok": False})


if __name__ == "__main__":
    unittest.main(verbosity=2)
