from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

PATH = Path(__file__).with_name("workflow_cost_surface.py")
SPEC = importlib.util.spec_from_file_location("workflow_cost_surface", PATH)
cost = importlib.util.module_from_spec(SPEC)
if SPEC.loader is None:
    raise RuntimeError("missing workflow_cost_surface loader")
sys.modules[SPEC.name] = cost
SPEC.loader.exec_module(cost)


def analyze(text: str):
    raw = text.encode("utf-8")
    return cost.analyze_text(
        text,
        path=".github/workflows/ci.yml",
        byte_sha256=hashlib.sha256(raw).hexdigest(),
        byte_size=len(raw),
    )


class WorkflowCostSurfaceTests(unittest.TestCase):
    def test_unscoped_push_pr_exposes_duplicate_launch_pressure(self):
        result = analyze("""on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
""")
        self.assertIn("UNRESTRICTED_PUSH_PLUS_PR", result.signals)
        self.assertIn("BROAD_PUSH_PR_PATH_SURFACE", result.signals)
        self.assertIn("RUN_EVENTS_WITHOUT_CONCURRENCY", result.signals)
        self.assertIn("RUNNER_JOB_MISSING_TIMEOUT", result.signals)

    def test_scoped_cancelled_timed_self_hosted_is_observed(self):
        result = analyze("""on:
  push:
    branches: [main]
    paths: [src/**]
  pull_request:
    paths: [src/**]
concurrency:
  group: ci-main
  cancel-in-progress: true
jobs:
  test:
    runs-on: [self-hosted, linux]
    timeout-minutes: 10
""")
        self.assertTrue(result.push_branch_scoped)
        self.assertTrue(result.push_path_scoped)
        self.assertTrue(result.pull_request_path_scoped)
        self.assertTrue(result.cancel_in_progress_true)
        self.assertNotIn("UNRESTRICTED_PUSH_PLUS_PR", result.signals)
        self.assertNotIn("HOSTED_OR_DYNAMIC_RUNNER_EXPOSURE", result.signals)

    def test_schedule_and_simple_matrix_are_counted(self):
        result = analyze("""on:
  schedule:
    - cron: '0 * * * *'
    - cron: '30 * * * *'
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    strategy:
      matrix:
        python: ['3.11', '3.12']
        os: [ubuntu-latest, windows-latest]
""")
        self.assertEqual(result.schedule_entries, 2)
        self.assertEqual(result.jobs[0].static_matrix_multiplier, 4)
        self.assertIn("SCHEDULED_RUNS", result.signals)
        self.assertIn("MATRIX_FANOUT", result.signals)

    def test_complex_matrix_does_not_invent_multiplier(self):
        result = analyze("""on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        py: ['3.11', '3.12']
        include:
          - py: '3.13'
""")
        self.assertTrue(result.jobs[0].matrix_declared)
        self.assertIsNone(result.jobs[0].static_matrix_multiplier)

    def test_reusable_job_is_not_direct_runner_job(self):
        result = analyze("""on:
  pull_request:
jobs:
  delegated:
    uses: org/repo/.github/workflows/reuse.yml@main
""")
        summary = cost.summarize(Path("/repo"), [result])
        self.assertEqual(summary["runner_jobs"], 0)
        self.assertEqual(summary["reusable_workflow_jobs"], 1)

    def test_exact_file_hash_and_symlink_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / ".github" / "workflows"
            directory.mkdir(parents=True)
            body = "on:\n  workflow_dispatch:\n"
            path = directory / "manual.yml"
            path.write_text(body, encoding="utf-8")
            summary = cost.audit_root(root)
            self.assertEqual(summary["workflow_files"], 1)
            self.assertEqual(
                summary["workflows"][0]["byte_sha256"],
                hashlib.sha256(body.encode("utf-8")).hexdigest(),
            )
            link = directory / "link.yml"
            try:
                link.symlink_to(path)
            except (OSError, NotImplementedError):
                return
            self.assertEqual(cost.audit_root(root)["workflow_files"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
