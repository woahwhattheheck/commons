import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations.shared_equipment import github_publication
from integrations.shared_equipment.services import ServiceEquipment


class MetadataPublicationTests(unittest.TestCase):
    def test_catalog_is_identical_for_new_peer(self):
        left = ServiceEquipment().tools(peer="existing")
        right = ServiceEquipment().tools(peer="newcomer")
        self.assertEqual(left, right)
        names = {t["name"] for t in right}
        self.assertTrue({"github_add_issue_comment", "github_update_issue_comment",
                         "github_update_issue", "github_update_pull_request"} <= names)

    def test_comment_routes_exact_text_and_stable_id_to_publisher(self):
        with patch.object(github_publication, "publish", return_value={"ok": True}) as publish:
            result = ServiceEquipment().call("github_add_issue_comment", {
                "repository": "upstream/project", "issue_number": 9,
                "body": "Source evidence\nsecond line", "operation_id": "fleet-comment-01"})
        self.assertFalse(result["isError"])
        publish.assert_called_once_with("issue.comment.create", {
            "owner": "upstream", "repo": "project", "issue_number": 9,
            "body": "Source evidence\nsecond line"}, "fleet-comment-01")

    def test_nonpositive_or_boolean_identity_never_publishes(self):
        with patch.object(github_publication, "publish") as publish:
            for value in (0, -1, True, "9"):
                r = ServiceEquipment().call("github_add_issue_comment", {
                    "repository": "upstream/project", "issue_number": value,
                    "body": "text", "operation_id": "fleet-invalid"})
                self.assertTrue(r["isError"])
            publish.assert_not_called()

    def test_stale_pr_head_does_not_publish(self):
        tool = ServiceEquipment()
        with patch.object(tool, "github", return_value={"head": {"sha": "new"}}), patch.object(github_publication, "publish") as publish:
            r = tool.call("github_update_pull_request", {"repository": "upstream/project",
                "pull_number": 9, "expected_head": "old", "body": "text", "operation_id": "fleet-pr-01"})
        self.assertTrue(r["isError"])
        publish.assert_not_called()

    def test_pr_readback_failure_retains_successful_write_receipt(self):
        tool = ServiceEquipment()
        receipt = {"ok": True, "publication": {"receipt": {"id": 9}}}
        with patch.object(tool, "github", side_effect=[{"head": {"sha": "current"}}, OSError("offline")]), patch.object(github_publication, "publish", return_value=receipt):
            r = tool.call("github_update_pull_request", {"repository": "upstream/project",
                "pull_number": 9, "expected_head": "current", "body": "text", "operation_id": "fleet-pr-02"})
        self.assertFalse(r["isError"])
        self.assertEqual(r["result"]["publication"]["receipt"]["id"], 9)
        self.assertIn("readback_error", r["result"])

    def test_incident_denial_and_uncertain_delivery_are_errors(self):
        for result in ({"ok": False, "publication": {"allow": False, "incident": True}},
                       {"ok": False, "uncertain": True}):
            with patch.object(github_publication, "publish", return_value=result):
                r = ServiceEquipment().call("github_update_issue", {"repository": "upstream/project",
                    "issue_number": 9, "body": "text", "operation_id": "fleet-issue-01"})
            self.assertTrue(r["isError"])
            self.assertEqual(r["uncertain"], result.get("uncertain", False))

    def test_client_uses_stdin_and_preserves_replayed_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            client = Path(directory)/"publish.py"; client.write_text("# fixture")
            seen=[]
            def runner(command, **kwargs):
                seen.append((command, kwargs))
                return subprocess.CompletedProcess(command,0,json.dumps({"allow":True,
                    "operation_id":"fleet-op-01","replayed":True,"receipt":{"id":9}}),"")
            r=github_publication.publish("issue.comment.create",{"body":"one\ntwo"},"fleet-op-01",runner=runner,client=client)
        self.assertTrue(r["ok"])
        self.assertTrue(r["publication"]["replayed"])
        self.assertEqual(json.loads(seen[0][1]["input"])["args"]["body"],"one\ntwo")
        self.assertNotIn("shell",seen[0][1])

    def test_invalid_identity_and_timeout_do_not_expose_output(self):
        with tempfile.TemporaryDirectory() as directory:
            client=Path(directory)/"publish.py"; client.write_text("# fixture")
            for output in ("not JSON",json.dumps({"allow":True,"operation_id":"wrong","receipt":{"id":9}})):
                with self.assertRaises(github_publication.EquipmentError) as error:
                    github_publication.publish("issue.update",{},"fleet-op-01",client=client,
                        runner=lambda *a,**k:subprocess.CompletedProcess(a,0,output,"private stderr"))
                self.assertTrue(error.exception.uncertain)
                self.assertNotIn("private",str(error.exception))
            with self.assertRaises(github_publication.EquipmentError) as error:
                github_publication.publish("issue.update",{},"fleet-op-01",client=client,
                    runner=lambda *a,**k:(_ for _ in ()).throw(subprocess.TimeoutExpired("fixture",150)))
            self.assertTrue(error.exception.uncertain)


if __name__ == "__main__": unittest.main()
