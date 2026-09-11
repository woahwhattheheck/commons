import json
import unittest

from host.receipt_resolver import ParsedId, ResolutionError, Resolver, parse_identifier


SHA = "830e8e9a3ddae95799142eba6bcbd03f85eb4787"


class FakeTransport:
    def __init__(self, json_by_url=None, text_by_url=None):
        self.json_by_url = dict(json_by_url or {})
        self.text_by_url = dict(text_by_url or {})
        self.json_calls = []
        self.text_calls = []

    def get_json(self, url):
        self.json_calls.append(url)
        if url not in self.json_by_url:
            raise AssertionError(f"unexpected JSON URL: {url}")
        value = self.json_by_url[url]
        if isinstance(value, Exception):
            raise value
        return value

    def get_text(self, url):
        self.text_calls.append(url)
        if url not in self.text_by_url:
            raise AssertionError(f"unexpected text URL: {url}")
        value = self.text_by_url[url]
        if isinstance(value, Exception):
            raise value
        return value


def resolver(transport):
    return Resolver(
        "o/r",
        api_base="https://api.example",
        coordination_url="https://coord.example/state",
        get_json=transport.get_json,
        get_text=transport.get_text,
    )


class ParseIdentifierTests(unittest.TestCase):
    def test_explicit_namespaces(self):
        self.assertEqual(parse_identifier("#12", "o/r"), ParsedId("pr", "12"))
        self.assertEqual(parse_identifier("pr:12", "o/r"), ParsedId("pr", "12"))
        self.assertEqual(parse_identifier("run:34", "o/r"), ParsedId("run", "34"))
        self.assertEqual(parse_identifier(f"blob:{SHA.upper()}", "o/r"), ParsedId("blob", SHA))
        self.assertEqual(parse_identifier("review:56", "o/r"), ParsedId("review", "56"))
        self.assertEqual(parse_identifier("review:12:56", "o/r"), ParsedId("review", "56", 12))
        self.assertEqual(parse_identifier("marker:LANE-X", "o/r"), ParsedId("marker", "LANE-X"))

    def test_pull_url_binds_repository(self):
        self.assertEqual(
            parse_identifier("https://github.com/o/r/pull/12", "o/r"),
            ParsedId("pr", "12"),
        )
        with self.assertRaisesRegex(ResolutionError, "different repository") as caught:
            parse_identifier("https://github.com/other/r/pull/12", "o/r")
        self.assertEqual(caught.exception.code, "WRONG_REPOSITORY")

    def test_bare_number_and_bad_blob_fail_closed(self):
        with self.assertRaises(ResolutionError) as caught:
            parse_identifier("123", "o/r")
        self.assertEqual(caught.exception.code, "AMBIGUOUS_NUMERIC_ID")
        with self.assertRaises(ResolutionError) as caught:
            parse_identifier("blob:deadbeef", "o/r")
        self.assertEqual(caught.exception.code, "INVALID_BLOB")


class ResolverTests(unittest.TestCase):
    def test_pr_and_run_keep_queued_distinct_from_success(self):
        transport = FakeTransport(
            json_by_url={
                "https://api.example/repos/o/r/pulls/12": {
                    "number": 12,
                    "state": "open",
                    "draft": True,
                    "merged": False,
                    "html_url": "https://github.com/o/r/pull/12",
                    "head": {"sha": "h"},
                    "base": {"sha": "b"},
                    "mergeable": True,
                    "updated_at": "now",
                },
                "https://api.example/repos/o/r/actions/runs/34": {
                    "id": 34,
                    "status": "queued",
                    "conclusion": None,
                    "head_sha": "h",
                    "event": "pull_request",
                    "run_attempt": 1,
                    "html_url": "https://github.com/o/r/actions/runs/34",
                    "updated_at": "now",
                },
            }
        )
        r = resolver(transport)
        self.assertEqual(r.resolve("pr:12")["state"], "OPEN_DRAFT")
        self.assertEqual(r.resolve("run:34")["state"], "QUEUED")

    def test_blob_response_must_bind_exact_sha(self):
        transport = FakeTransport(
            json_by_url={
                f"https://api.example/repos/o/r/git/blobs/{SHA}": {
                    "sha": SHA,
                    "size": 17,
                    "encoding": "base64",
                    "url": "blob-url",
                }
            }
        )
        out = resolver(transport).resolve(f"blob:{SHA}")
        self.assertEqual(out["state"], "AVAILABLE")
        self.assertEqual(out["sha"], SHA)

        bad = FakeTransport(
            json_by_url={
                f"https://api.example/repos/o/r/git/blobs/{SHA}": {
                    "sha": "0" * 40,
                    "size": 17,
                }
            }
        )
        with self.assertRaises(ResolutionError) as caught:
            resolver(bad).resolve(f"blob:{SHA}")
        self.assertEqual(caught.exception.code, "BAD_GITHUB_RESPONSE")

    def test_review_can_resolve_pr_from_coordination_jsonl(self):
        rows = "\n".join(
            [
                json.dumps({"number": 11, "verdicts": {"source": {"review_id": 111}}}),
                json.dumps({"number": 12, "verdicts": {"source": {"review_id": 222}}}),
            ]
        )
        transport = FakeTransport(
            text_by_url={"https://coord.example/state": rows},
            json_by_url={
                "https://api.example/repos/o/r/pulls/12/reviews/222": {
                    "id": 222,
                    "state": "COMMENTED",
                    "commit_id": "head",
                    "submitted_at": "now",
                    "html_url": "review-url",
                }
            },
        )
        out = resolver(transport).resolve("review:222")
        self.assertEqual(out["pr"], 12)
        self.assertEqual(out["resolved_via"], "coordination-index")
        self.assertEqual(out["state"], "COMMENTED")

    def test_review_index_ambiguity_fails_before_github_review_fetch(self):
        rows = json.dumps(
            [
                {"number": 11, "verdicts": {"source": {"review_id": 222}}},
                {"number": 12, "verdicts": {"hosted": {"review_id": 222}}},
            ]
        )
        transport = FakeTransport(text_by_url={"https://coord.example/state": rows})
        with self.assertRaises(ResolutionError) as caught:
            resolver(transport).resolve("review:222")
        self.assertEqual(caught.exception.code, "AMBIGUOUS_REVIEW")
        self.assertEqual(transport.json_calls, [])

    def test_explicit_review_pr_does_not_depend_on_coordination(self):
        transport = FakeTransport(
            json_by_url={
                "https://api.example/repos/o/r/pulls/12/reviews/222": {
                    "id": 222,
                    "state": "APPROVED",
                    "commit_id": "head",
                    "submitted_at": "now",
                    "html_url": "review-url",
                }
            }
        )
        out = resolver(transport).resolve("review:12:222")
        self.assertEqual(out["state"], "APPROVED")
        self.assertEqual(out["resolved_via"], "explicit-pr")
        self.assertEqual(transport.text_calls, [])

    def test_marker_prefers_exact_coordination_index(self):
        rows = json.dumps(
            [
                {"number": 12, "marker": "LANE-X"},
                {"number": 13, "marker": "OTHER"},
            ]
        )
        transport = FakeTransport(
            text_by_url={"https://coord.example/state": rows},
            json_by_url={
                "https://api.example/repos/o/r/pulls/12": {
                    "number": 12,
                    "state": "closed",
                    "draft": False,
                    "merged": True,
                    "html_url": "pr-url",
                    "head": {"sha": "h"},
                    "base": {"sha": "b"},
                    "mergeable": None,
                    "updated_at": "now",
                }
            },
        )
        out = resolver(transport).resolve("marker:LANE-X")
        self.assertEqual(out["resolved_via"], "coordination-index")
        self.assertEqual(out["target"]["state"], "MERGED")
        self.assertFalse(any("/search/issues" in url for url in transport.json_calls))

    def test_marker_search_requires_unique_pr(self):
        rows = "[]"
        marker = "LANE-X"
        expected_search = (
            "https://api.example/search/issues?"
            "q=repo%3Ao%2Fr+is%3Apr+%22LANE-X%22&per_page=10"
        )
        transport = FakeTransport(
            text_by_url={"https://coord.example/state": rows},
            json_by_url={
                expected_search: {
                    "items": [
                        {"number": 12, "pull_request": {"url": "p12"}},
                        {"number": 13, "pull_request": {"url": "p13"}},
                    ]
                }
            },
        )
        with self.assertRaises(ResolutionError) as caught:
            resolver(transport).resolve(f"marker:{marker}")
        self.assertEqual(caught.exception.code, "AMBIGUOUS_MARKER")

    def test_mismatched_pr_response_fails_closed(self):
        transport = FakeTransport(
            json_by_url={
                "https://api.example/repos/o/r/pulls/12": {"number": 13, "state": "open"}
            }
        )
        with self.assertRaises(ResolutionError) as caught:
            resolver(transport).resolve("pr:12")
        self.assertEqual(caught.exception.code, "BAD_GITHUB_RESPONSE")


if __name__ == "__main__":
    unittest.main()
