import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aws_agent import ContractError, _parse_s3_event, _review_body, _source_ref


def s3_event(*, bucket="prooflens", key="current/unit%201.png", version="v-current"):
    return {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key, "versionId": version},
                },
            }
        ]
    }


class AwsContractTests(unittest.TestCase):
    def test_event_binds_bucket_key_and_version(self):
        self.assertEqual(
            _parse_s3_event(s3_event(), "prooflens"),
            ("prooflens", "current/unit 1.png", "v-current"),
        )

    def test_wrong_bucket_rejected(self):
        with self.assertRaisesRegex(ContractError, "bucket"):
            _parse_s3_event(s3_event(bucket="other"), "prooflens")

    def test_non_current_prefix_rejected(self):
        with self.assertRaisesRegex(ContractError, "current"):
            _parse_s3_event(s3_event(key="baseline/unit.png"), "prooflens")

    def test_missing_current_version_rejected(self):
        event = s3_event()
        del event["Records"][0]["s3"]["object"]["versionId"]
        with self.assertRaisesRegex(ContractError, "versionId"):
            _parse_s3_event(event, "prooflens")

    def test_empty_current_version_rejected(self):
        with self.assertRaisesRegex(ContractError, "versionId"):
            _parse_s3_event(s3_event(version=""), "prooflens")

    def test_multiple_records_rejected(self):
        event = s3_event()
        event["Records"].append(event["Records"][0])
        with self.assertRaisesRegex(ContractError, "exactly one"):
            _parse_s3_event(event, "prooflens")

    def test_missing_records_rejected(self):
        with self.assertRaises(ContractError):
            _parse_s3_event({"unrelated": []}, "prooflens")

    def test_source_ref_preserves_exact_object_versions(self):
        baseline = {"version_id": "b-17", "etag": "beef"}
        current = {"version_id": "c-42", "etag": "cafe"}
        ref = _source_ref("bucket", "baseline/x.png", baseline, "current/x.png", current)
        self.assertIn("versionId=b-17", ref)
        self.assertIn("versionId=c-42", ref)
        self.assertIn("etag=beef", ref)
        self.assertIn("etag=cafe", ref)

    def test_review_message_cannot_authorize_external_action(self):
        evidence = {"event_id": "a" * 64, "source_ref": "s3://example"}
        receipt = {
            "decision": "REQUEST_HUMAN_REVIEW",
            "reason_codes": ["CHANGED_FRACTION_THRESHOLD"],
            "receipt_sha256": "b" * 64,
        }
        body = _review_body(evidence, receipt)
        self.assertIs(body["external_action_authorized"], False)
        self.assertEqual(body["event_id"], evidence["event_id"])


if __name__ == "__main__":
    unittest.main()
