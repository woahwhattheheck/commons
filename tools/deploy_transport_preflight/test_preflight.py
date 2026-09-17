from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .preflight import (
    DomainError,
    HOLD_AMBIGUOUS,
    HOLD_UNBOUND,
    READY,
    canonical_bytes,
    compile_values,
    strict_loads,
    verify_bytes,
)

HERE = Path(__file__).resolve().parent
COMMIT = "1" * 40
ALT_COMMIT = "3" * 40
DIGEST = "2" * 64
REPO = "https://github.com/woahwhattheheck/public-commons-sprint-2026"


def request(provider="netlify", *, project_id=None, source=None):
    return {
        "schema": "deploy-transport-request.v1",
        "provider": provider,
        "source": source or {"repo": REPO, "commit_sha": COMMIT, "subdir": "cookie-crumbs"},
        "target": {"project_id": project_id},
    }


def action(name, kind, source_binding):
    return {"name": name, "kind": kind, "source_binding": source_binding}


def manifest(provider, *actions):
    return {
        "schema": "deploy-transport-capability-manifest.v1",
        "provider": provider,
        "actions": list(actions),
    }


def binding(provider="netlify", project_id="site-123", source=None):
    return {
        "schema": "deploy-project-binding.v1",
        "provider": provider,
        "project_id": project_id,
        "source": source or request(provider)["source"],
    }


def raw(value):
    return canonical_bytes(value)


class PreflightTests(unittest.TestCase):
    def test_current_netlify_surface_holds(self):
        m = json.loads((HERE / "fixtures/netlify_current.json").read_text())
        report = compile_values(request(), m)
        self.assertEqual(report["status"], HOLD_UNBOUND)
        self.assertEqual(report["viable_paths"], [])
        self.assertIn("create-new-project:ACTION_HAS_NO_SOURCE_BINDING", report["blockers"])
        self.assertIn("deploy-site:PROJECT_BINDING_MISSING", report["blockers"])
        self.assertTrue(all(v is False for v in report["external_authority"].values()))

    def test_current_vercel_surface_holds(self):
        m = json.loads((HERE / "fixtures/vercel_current.json").read_text())
        report = compile_values(request("vercel"), m)
        self.assertEqual(report["status"], HOLD_UNBOUND)
        self.assertIn("deploy-current-project:PROJECT_BINDING_MISSING", report["blockers"])

    def test_repo_commit_is_ready(self):
        m = manifest("netlify", action("deploy-repo", "DEPLOY_REPO", "repo_commit"))
        report = compile_values(request(), m)
        self.assertEqual(report["status"], READY)
        self.assertEqual(report["viable_paths"], ["deploy-repo"])

    def test_artifact_and_bundle_are_ready(self):
        req = request("host", source={"artifact_sha256": DIGEST, "file_bundle_sha256": "4" * 64})
        m = manifest(
            "host",
            action("deploy-artifact", "DEPLOY_ARTIFACT", "artifact_sha256"),
            action("deploy-bundle", "DEPLOY_FILE_BUNDLE", "file_bundle_sha256"),
        )
        report = compile_values(req, m)
        self.assertEqual(report["status"], READY)
        self.assertEqual(report["viable_paths"], ["deploy-artifact", "deploy-bundle"])

    def test_exact_project_binding_is_ready(self):
        req = request(project_id="site-123")
        m = manifest("netlify", action("deploy-site", "DEPLOY_EXISTING_PROJECT", "existing_project_binding"))
        report = compile_values(req, m, binding())
        self.assertEqual(report["status"], READY)
        self.assertEqual(report["viable_paths"], ["deploy-site"])

    def test_project_binding_commit_transplant_holds(self):
        req = request(project_id="site-123")
        other = binding(source={"repo": REPO, "commit_sha": ALT_COMMIT, "subdir": "cookie-crumbs"})
        m = manifest("netlify", action("deploy-site", "DEPLOY_EXISTING_PROJECT", "existing_project_binding"))
        report = compile_values(req, m, other)
        self.assertEqual(report["status"], HOLD_UNBOUND)
        self.assertIn("deploy-site:PROJECT_BINDING_SOURCE_MISMATCH", report["blockers"])

    def test_cross_provider_binding_holds(self):
        req = request(project_id="site-123")
        m = manifest("netlify", action("deploy-site", "DEPLOY_EXISTING_PROJECT", "existing_project_binding"))
        report = compile_values(req, m, binding(provider="vercel"))
        self.assertEqual(report["status"], HOLD_UNBOUND)
        self.assertIn("deploy-site:PROJECT_BINDING_PROVIDER_MISMATCH", report["blockers"])

    def test_branch_only_is_not_immutable(self):
        req = request(source={"repo": REPO, "branch": "main"})
        m = manifest("netlify", action("deploy-repo", "DEPLOY_REPO", "repo_commit"))
        report = compile_values(req, m)
        self.assertEqual(report["status"], HOLD_UNBOUND)
        self.assertIn("REQUEST_SOURCE_NOT_IMMUTABLE", report["blockers"])
        self.assertIn("deploy-repo:REQUEST_REPO_COMMIT_MISSING", report["blockers"])

    def test_unknown_binding_is_ambiguous(self):
        m = manifest("netlify", action("deploy-magic", "DEPLOY_REPO", "free_form_source"))
        report = compile_values(request(), m)
        self.assertEqual(report["status"], HOLD_AMBIGUOUS)
        self.assertIn("deploy-magic:UNKNOWN_SOURCE_BINDING", report["blockers"])

    def test_contradictory_kind_binding_is_ambiguous(self):
        m = manifest("netlify", action("deploy-site", "DEPLOY_EXISTING_PROJECT", "repo_commit"))
        report = compile_values(request(), m)
        self.assertEqual(report["status"], HOLD_AMBIGUOUS)
        self.assertIn("deploy-site:CONTRADICTORY_ACTION_BINDING", report["blockers"])

    def test_provider_mismatch_is_ambiguous(self):
        m = manifest("vercel", action("deploy-repo", "DEPLOY_REPO", "repo_commit"))
        report = compile_values(request(), m)
        self.assertEqual(report["status"], HOLD_AMBIGUOUS)
        self.assertIn("MANIFEST_PROVIDER_MISMATCH", report["blockers"])

    def test_report_tamper_rejected(self):
        req = request()
        m = manifest("netlify", action("deploy-repo", "DEPLOY_REPO", "repo_commit"))
        report = compile_values(req, m)
        verify_bytes(raw(req), raw(m), raw(report))
        report["status"] = HOLD_UNBOUND
        with self.assertRaises(DomainError):
            verify_bytes(raw(req), raw(m), raw(report))

    def test_strict_json_hostiles(self):
        bad = [
            b'{"schema":"a","schema":"b"}',
            b'{"x":NaN}',
            b'{"x":1.25}',
            b'{"x":9007199254740992}',
            b'{"x":"\\ud800"}',
        ]
        for payload in bad:
            with self.subTest(payload=payload), self.assertRaises(DomainError):
                strict_loads(payload)

    def test_bool_cannot_alias_project_id(self):
        req = request()
        req["target"]["project_id"] = True
        m = manifest("netlify", action("deploy-site", "DEPLOY_EXISTING_PROJECT", "existing_project_binding"))
        with self.assertRaises(DomainError):
            compile_values(req, m)

    def test_noncanonical_repo_urls_rejected(self):
        m = manifest("netlify", action("deploy-repo", "DEPLOY_REPO", "repo_commit"))
        for repo in ("https://github.com/a/b?ref=x", "https://user@github.com/a/b", "https://github.com/a/b/"):
            with self.subTest(repo=repo), self.assertRaises(DomainError):
                compile_values(request(source={"repo": repo, "commit_sha": COMMIT}), m)

    def test_cli_compile_verify_and_overwrite_refusal(self):
        req = request()
        m = manifest("netlify", action("deploy-repo", "DEPLOY_REPO", "repo_commit"))
        script = HERE / "preflight.py"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            reqp, manp, outp = td / "request.json", td / "manifest.json", td / "report.json"
            reqp.write_bytes(raw(req))
            manp.write_bytes(raw(m))
            run = subprocess.run(
                [sys.executable, str(script), "compile", "--request", str(reqp), "--manifest", str(manp), "--out", str(outp)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn(READY, run.stdout)
            verify = subprocess.run(
                [sys.executable, str(script), "verify", "--request", str(reqp), "--manifest", str(manp), "--report", str(outp)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            second = subprocess.run(
                [sys.executable, str(script), "compile", "--request", str(reqp), "--manifest", str(manp), "--out", str(outp)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(second.returncode, 2)
            self.assertIn("refusing to overwrite output", second.stderr)


if __name__ == "__main__":
    unittest.main()
