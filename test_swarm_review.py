"""Review invariants against real Git objects and provider execution authority."""
import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from host import coordination_state as cs
from host import swarm_review as sr


class ReviewGit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git = cs.Git(str(self.root))
        self.git.out("init", "-b", "main")
        self.git.out("config", "user.name", "review test")
        self.git.out("config", "user.email", "test@example.invalid")
        self.workflow = ".github/workflows/tests.yml"
        for p, value in {
            "module.py": "old",
            "dep.py": "dependency",
            sr.POLICY: "policy",
            "AGENTS.md": "entry",
            sr.RELIABILITY: '{"outcomes":[]}',
            self.workflow: "name: tests\non: pull_request\njobs: {}\n",
        }.items():
            self.write(p, value)
        self.base = self.commit("base")
        self.workflow_blob = self.git.out(
            "rev-parse", self.base + ":" + self.workflow).strip()
        self.git.out("checkout", "-b", "candidate")
        self.write("module.py", "new")
        self.head = self.commit("change")
        self.git.out("checkout", "main")
        self.work = {
            "seat": "MUSE",
            "family": "muse",
            "operation": "one-operation",
            "read_paths": ["dep.py"],
            "evidence": [{"result": "PASS", "reference": "actual check fixture"}],
        }
        self.authority = {
            "provider": sr.ACTIONS_PROVIDER,
            "head": self.head,
            "run_id": 101,
            "job_id": 202,
            "job_name": "battery",
            "workflow_path": self.workflow,
            "reference": "https://github.example/actions/runs/101",
            "steps": ["the whole battery, one failure fails the run"],
        }
        self.exec_evidence = [{
            "result": "PASS",
            "kind": "execution",
            "provider": sr.ACTIONS_PROVIDER,
            "head": self.head,
            "run_id": 101,
            "job_id": 202,
            "workflow_path": self.workflow,
            "workflow_blob": self.workflow_blob,
            "steps": ["the whole battery, one failure fails the run"],
            "reference": "https://github.example/actions/runs/101",
        }]
        self.pull = {
            "number": 1,
            "headRefOid": self.head,
            "baseRefName": "main",
            "body": "```commons-work\n" + json.dumps(self.work) + "\n```",
            "_execution_authority": [copy.deepcopy(self.authority)],
        }
        self.subject = sr.change(self.git, self.base, self.pull)
        self.receipt = sr.review_template(self.subject)
        self.receipt.update(
            decision="PASS",
            reviewer={"seat": "ASTRA", "family": "gpt", "session_ref": "test-session"},
            summary="read actual diff",
            evidence=copy.deepcopy(self.exec_evidence),
        )

    def write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)

    def commit(self, message):
        self.git.out("add", ".")
        self.git.out("commit", "-m", message)
        return self.git.out("rev-parse", "HEAD").strip()

    def review(self, value=None, **kw):
        return {
            "id": 1,
            "commit_id": self.head,
            "state": "COMMENTED",
            "submitted_at": "2026-09-12T22:00:00Z",
            "body": "```commons-gpt-review\n" + json.dumps(value or self.receipt) + "\n```",
            **kw,
        }

    def test_non_gpt_needs_gpt(self):
        self.assertEqual("WAIT_GPT", sr.decision(self.git, self.subject, [])["state"])
        self.assertEqual("READY", sr.decision(
            self.git, self.subject, [self.review()])["state"])

    def test_source_only_pass_cannot_authorize_code_merge(self):
        value = copy.deepcopy(self.receipt)
        value["evidence"] = [{"result": "PASS", "reference": "semantic source clean"}]
        verdict = sr.decision(self.git, self.subject, [self.review(value)])
        self.assertEqual("HOLD", verdict["state"])
        self.assertIn("provider-verified exact-head execution", verdict["reason"])

    def test_relabelled_source_claim_cannot_invent_execution(self):
        value = copy.deepcopy(self.receipt)
        value["evidence"] = [{
            "result": "PASS",
            "kind": "execution",
            "head": self.head,
            "reference": "source clean; reviewer relabelled it",
        }]
        verdict = sr.decision(self.git, self.subject, [self.review(value)])
        self.assertEqual("HOLD", verdict["state"])
        self.assertIn("provider-verified", verdict["reason"])

    def test_provider_run_job_and_head_are_bound(self):
        for field, replacement in (
            ("head", "0" * 40),
            ("run_id", 999),
            ("job_id", 999),
            ("workflow_blob", "0" * 40),
            ("reference", "https://github.example/actions/runs/not-101"),
        ):
            value = copy.deepcopy(self.receipt)
            value["evidence"][0][field] = replacement
            verdict = sr.decision(self.git, self.subject, [self.review(value)])
            self.assertEqual("HOLD", verdict["state"], field)

    def test_unreported_or_failed_step_cannot_be_cited(self):
        value = copy.deepcopy(self.receipt)
        value["evidence"][0]["steps"] = ["imaginary successful command"]
        self.assertEqual("HOLD", sr.decision(
            self.git, self.subject, [self.review(value)])["state"])

    def test_candidate_cannot_modify_its_execution_authority_workflow(self):
        self.git.out("checkout", "candidate")
        self.write(self.workflow, "name: candidate-controlled\n")
        head = self.commit("self-authorizing workflow")
        pull = copy.deepcopy(self.pull)
        pull["headRefOid"] = head
        pull["_execution_authority"][0]["head"] = head
        pull["_execution_authority"][0]["run_id"] = 303
        pull["_execution_authority"][0]["job_id"] = 404
        self.git.out("checkout", "main")
        subject = sr.change(self.git, self.base, pull)
        receipt = sr.review_template(subject)
        receipt.update(
            decision="PASS",
            reviewer={"seat": "ASTRA", "family": "gpt", "session_ref": "test-session"},
            summary="hostile fixture",
            evidence=[{
                **copy.deepcopy(self.exec_evidence[0]),
                "head": head,
                "run_id": 303,
                "job_id": 404,
            }],
        )
        review = self.review(receipt)
        review["commit_id"] = head
        self.assertEqual("HOLD", sr.decision(
            self.git, subject, [review])["state"])

    def test_execution_requirement_is_change_object_derived(self):
        def changed(path, old_mode="100644", new_mode="100644", status="M"):
            return (status, path, old_mode, new_mode, "a" * 40, "b" * 40)

        self.assertTrue(sr.execution_required([changed("module.py")]))
        self.assertTrue(sr.execution_required([changed("config/policy.json")]))
        self.assertTrue(sr.execution_required([changed("web/control.html")]))
        self.assertTrue(sr.execution_required([changed("requirements.txt")]))
        self.assertFalse(sr.execution_required([
            changed("README.md"), changed("docs/guide.rst"), changed("docs/guide.adoc")
        ]))
        self.assertFalse(sr.execution_required([
            changed("docs/new.md", old_mode="000000", status="A"),
            changed("docs/old.rst", new_mode="000000", status="D"),
        ]))
        self.assertTrue(sr.execution_required([changed("AGENTS.md")]))
        self.assertTrue(sr.execution_required([changed(sr.POLICY)]))
        self.assertTrue(sr.execution_required([changed(".github/review-notes.md")]))
        self.assertTrue(sr.execution_required([changed("docs/link.md", "120000", "120000")]))
        self.assertTrue(sr.execution_required([changed("docs/module.adoc", "160000", "160000")]))
        self.assertTrue(sr.execution_required([changed("docs/tool.md", "100755", "100755")]))
        self.assertTrue(sr.execution_required([changed("docs/tool.md", "100644", "100755")]))
        self.assertTrue(sr.execution_required([changed("docs/tool.md", "100755", "100644")]))
        self.assertTrue(sr.execution_required([
            changed("docs/new-tool.md", old_mode="000000", new_mode="100755", status="A")
        ]))

    def test_unrelated_main_advance_reuses_review(self):
        self.write("unrelated.py", "another builder")
        new = self.commit("unrelated")
        subject = sr.change(self.git, new, self.pull)
        self.assertEqual("READY", sr.decision(
            self.git, subject, [self.review()])["state"])

    def test_changed_dependency_revokes_cached_review(self):
        self.write("dep.py", "changed contract")
        new = self.commit("dependency")
        subject = sr.change(self.git, new, self.pull)
        self.assertEqual("WAIT_GPT", sr.decision(
            self.git, subject, [self.review()])["state"])

    def test_changed_head_cannot_reuse_review(self):
        self.git.out("checkout", "candidate")
        self.write("module.py", "new again")
        head = self.commit("more work")
        pull = dict(self.pull, headRefOid=head)
        self.git.out("checkout", "main")
        self.assertEqual("WAIT_GPT", sr.decision(
            self.git, sr.change(self.git, self.base, pull), [self.review()])["state"])

    def test_non_gpt_self_attestation_rejected(self):
        for family, seat in (("muse", "OTHER"), ("gpt", "MUSE")):
            value = copy.deepcopy(self.receipt)
            value["reviewer"].update(family=family, seat=seat)
            self.assertEqual("HOLD", sr.decision(
                self.git, self.subject, [self.review(value)])["state"])

    def test_gpt_is_a_builder_and_can_record_its_pass(self):
        self.subject["work"]["family"] = "gpt"
        value = copy.deepcopy(self.receipt)
        value["reviewer"]["seat"] = "MUSE"
        value["work_sha256"] = sr.work_digest(self.subject["work"])
        self.assertEqual("READY", sr.decision(
            self.git, self.subject, [self.review(value)])["state"])

    def test_hold_and_dismissal_supersede(self):
        hold = dict(self.receipt, decision="HOLD")
        self.assertEqual("HOLD", sr.decision(
            self.git, self.subject,
            [self.review(), self.review(
                hold, id=2, submitted_at="2026-09-12T22:01:00Z")])["state"])
        self.assertEqual("WAIT_GPT", sr.decision(
            self.git, self.subject, [self.review(state="DISMISSED")])["state"])

    def test_missing_dependency_or_test_evidence_rejected(self):
        value = copy.deepcopy(self.receipt)
        del value["read_set"]["dep.py"]
        self.assertEqual("HOLD", sr.decision(
            self.git, self.subject, [self.review(value)])["state"])

    def test_recent_regression_requires_an_independent_preflight(self):
        self.write(sr.RELIABILITY, json.dumps({"outcomes": [{
            "seat": "MUSE",
            "outcome": "regression",
            "source_url": "https://example.invalid/incident",
            "observed_at": "2026-09-12T22:02:00Z",
        }]}))
        current = self.commit("record observed defect")
        subject = sr.change(self.git, current, self.pull)
        self.assertEqual("HOLD", sr.decision(
            self.git, subject, [self.review()])["state"])
        reviewed = copy.deepcopy(self.receipt)
        reviewed["preflight"] = {
            "seat": "OTHER",
            "evidence": copy.deepcopy(self.exec_evidence),
        }
        self.assertEqual("READY", sr.decision(
            self.git, subject, [self.review(reviewed)])["state"])
        source_only = copy.deepcopy(reviewed)
        source_only["preflight"]["evidence"] = [{
            "result": "PASS",
            "reference": "source-only preflight",
        }]
        self.assertEqual("HOLD", sr.decision(
            self.git, subject, [self.review(source_only)])["state"])
        value = dict(self.receipt, evidence=[])
        self.assertEqual("HOLD", sr.decision(
            self.git, self.subject, [self.review(value)])["state"])

    def test_fast_forward_commit_cannot_land_over_unreviewed_main(self):
        changes = self.git.diff_tree(self.base, self.head)
        tree = self.git.compose(self.base, changes)
        merge = self.git.out(
            "commit-tree", tree, "-p", self.base, "-p", self.head,
            "-m", "reviewed merge").strip()
        self.write("dep.py", "concurrent dependency change")
        newer = self.commit("concurrent main")
        self.assertNotEqual(
            0,
            self.git.run(
                "merge-base", "--is-ancestor", newer, merge, check=False).returncode,
        )
        self.assertEqual("new", self.git.out("show", merge + ":module.py"))


class ActionsAuthority(unittest.TestCase):
    def test_provider_readback_normalizes_only_successful_exact_head_jobs(self):
        head = "a" * 40

        class Github:
            repo = "owner/repo"

            def rest(self, path, params=None):
                if path.endswith("/actions/runs"):
                    return {"workflow_runs": [{
                        "id": 11,
                        "head_sha": head,
                        "event": "pull_request",
                        "status": "completed",
                        "conclusion": "success",
                        "path": ".github/workflows/tests.yml",
                        "html_url": "https://github.example/actions/runs/11",
                    }]}
                if path.endswith("/actions/runs/11/jobs"):
                    return {"jobs": [{
                        "id": 22,
                        "name": "battery",
                        "status": "completed",
                        "conclusion": "success",
                        "steps": [
                            {"name": "Set up job", "conclusion": "success"},
                            {"name": "actual exact-head command", "conclusion": "success"},
                            {"name": "failed optional probe", "conclusion": "failure"},
                            {"name": "Complete job", "conclusion": "success"},
                        ],
                    }]}
                raise AssertionError(path)

        self.assertEqual([{
            "provider": sr.ACTIONS_PROVIDER,
            "head": head,
            "run_id": 11,
            "job_id": 22,
            "job_name": "battery",
            "workflow_path": ".github/workflows/tests.yml",
            "reference": "https://github.example/actions/runs/11",
            "steps": ["actual exact-head command"],
        }], sr.actions_authorities(Github(), head))

    def test_failed_or_queued_provider_runs_are_not_authority(self):
        head = "b" * 40

        class Github:
            repo = "owner/repo"

            def rest(self, path, params=None):
                if path.endswith("/actions/runs"):
                    return {"workflow_runs": [
                        {
                            "id": 1,
                            "head_sha": head,
                            "event": "pull_request",
                            "status": "completed",
                            "conclusion": "failure",
                            "path": ".github/workflows/tests.yml",
                        },
                        {
                            "id": 2,
                            "head_sha": head,
                            "event": "pull_request",
                            "status": "queued",
                            "conclusion": None,
                            "path": ".github/workflows/tests.yml",
                        },
                    ]}
                raise AssertionError("job endpoint must not be read for non-success runs")

        self.assertEqual([], sr.actions_authorities(Github(), head))


class Queue(unittest.TestCase):
    def test_hundred_prs_are_ten_batches_with_evidenced_builders(self):
        outcomes = [{
            "seat": "BUILDER",
            "outcome": "accepted",
            "source_url": "https://example.invalid/" + str(i),
            "observed_at": "2026-09-12T20:00:00Z",
        } for i in range(10)]
        rows = [{
            "number": n,
            "paths": ["component/" + str(n)],
            "risk": "standard",
            "work": {"seat": "BUILDER"},
            "review": {"state": "WAIT_GPT"},
        } for n in range(100)]
        planned = sr.batches(rows, outcomes, capacity=0)
        self.assertEqual(10, len(planned))
        self.assertTrue(all(x["dispatch"] == "STAGED" for x in planned))
        self.assertEqual(100, sum(len(x["prs"]) for x in planned))

    def test_colliding_changes_and_regressions_get_separate_review(self):
        rows = [{
            "number": n,
            "paths": ["same.py"],
            "risk": "standard",
            "work": {"seat": "NEW"},
            "review": {"state": "WAIT_GPT"},
        } for n in range(3)]
        self.assertEqual(3, len(sr.batches(rows)))
        outcomes = [{
            "seat": "NEW",
            "outcome": "regression",
            "source_url": "receipt",
            "observed_at": "2026-09-12",
        }]
        self.assertEqual("individual", sr.scrutiny("NEW", outcomes))
        self.assertEqual("new", sr.scrutiny("UNKNOWN", outcomes))

    def test_claim_future_heartbeat_holds_lane_fail_closed(self):
        now = dt.datetime(2026, 9, 12, tzinfo=dt.timezone.utc)
        self.assertTrue(cs._holding_live({
            "state": "HELD",
            "heartbeat_at": "2026-09-13T00:00:00Z",
            "ttl_s": 1800,
        }, now))

    def test_duplicate_metadata_and_path_traversal_are_not_review_subjects(self):
        self.assertIsNone(sr.block(
            '```commons-work\n{"seat":"A","seat":"B"}\n```', "commons-work"))
        self.assertFalse(sr.paths_valid(["../policy"]))


if __name__ == "__main__":
    unittest.main()
