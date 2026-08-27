#!/usr/bin/env python3
"""Fail-closed tests for the MCP 2026-07-28 static evidence pack."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("mcp_stateless_72", ROOT / "host/mcp_stateless_72.py")
mcp = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mcp)


class FakeResponse:
    def __init__(self, raw: bytes, url: str, status: int = 200, content_length: str | None = None):
        self.raw = raw
        self.url = url
        self.status = status
        self.headers = {"Content-Length": content_length or str(len(raw))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self.url

    def read(self, limit: int):
        return self.raw[:limit]


class FakeOpener:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.requests = []

    def open(self, request, timeout: int):
        self.requests.append((request, timeout))
        return self.response


class MCPStateless72Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack, cls.schema = mcp.load(ROOT)

    def assert_invalid(self, broken, pattern):
        with self.assertRaisesRegex(mcp.EvidenceError, pattern):
            mcp.validate(ROOT, broken, self.schema)

    def run_cli(self, command):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "host/mcp_stateless_72.py"), command, "--root", str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rendered = completed.stdout.strip()
        parsed = json.loads(rendered)
        self.assertEqual(rendered, json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return parsed

    def test_build_contract_is_stable(self):
        self.assertEqual(mcp.BASE_SHA, "6827afadf7428e2139299da704a0821567b0037f")
        self.assertEqual(self.pack["generated_from_main"], mcp.BASE_SHA)
        self.assertEqual(
            mcp.BUILD_PATHS,
            (
                "revenue/mcp_stateless_72/prospects.schema.json",
                "revenue/mcp_stateless_72/prospects.json",
                "host/mcp_stateless_72.py",
                "test_mcp_stateless_72.py",
            ),
        )

    def test_schema_is_draft_2020_12_and_closed(self):
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        mcp._assert_closed_schema(self.schema)

    def test_public_schema_validates_pack(self):
        from test_outcome_commerce import MiniSchemaValidator

        MiniSchemaValidator(ROOT / "revenue/mcp_stateless_72").validate_file(
            self.pack, "prospects.schema.json"
        )

    def test_runtime_validates_exact_counts(self):
        result = mcp.validate(ROOT, self.pack, self.schema)
        self.assertEqual(
            result,
            {
                "status": "VALID",
                "kind": "MCP_STATELESS_72_VERIFIED_STATIC_SIGNAL_PACK",
                "sources": 2,
                "prospects": 10,
            },
        )

    def test_exact_ids_and_full_commit_pins(self):
        self.assertEqual(
            tuple(item["id"] for item in self.pack["official_sources"]),
            mcp.EXPECTED_OFFICIAL_IDS,
        )
        self.assertEqual(
            tuple(item["id"] for item in self.pack["prospects"]),
            mcp.EXPECTED_PROSPECT_IDS,
        )
        for item in self.pack["official_sources"] + self.pack["prospects"]:
            self.assertRegex(item["commit"], r"^[0-9a-f]{40}$")

    def test_truth_is_explicitly_noncommercial(self):
        self.assertEqual(self.pack["truth"], mcp.EXPECTED_TRUTH)
        self.assertEqual(self.pack["truth"]["cash_received_usd"], 0)
        self.assertEqual(
            self.pack["unapproved_candidate_material"],
            {"present": False, "owner_approved": False},
        )

    def test_private_fields_are_omitted(self):
        self.assertEqual(tuple(self.pack["omitted_private_fields"]), mcp.EXPECTED_OMISSIONS)
        mcp._walk_private_keys(self.pack)

    def test_urls_are_commit_path_cross_checked(self):
        for index, item in enumerate(self.pack["official_sources"] + self.pack["prospects"]):
            mcp._validate_provenance(item, "$[%d]" % index)
            self.assertIn(item["commit"], item["raw_url"])
            self.assertIn(item["commit"], item["commit_url"])

    def test_signals_equal_observation_kinds(self):
        for item in self.pack["prospects"]:
            observed = {mcp.SIGNAL_NAMES[value["signal"]] for value in item["observations"]}
            declared = {name for name, present in item["signals"].items() if present}
            self.assertEqual(observed, declared)

    def test_raw_file_hashes_are_pinned(self):
        schema_raw = mcp._repository_bytes((ROOT / mcp.SCHEMA_PATH).read_bytes(), str(mcp.SCHEMA_PATH))
        pack_raw = mcp._repository_bytes((ROOT / mcp.PACK_PATH).read_bytes(), str(mcp.PACK_PATH))
        self.assertEqual(hashlib.sha256(schema_raw).hexdigest(), mcp.EXPECTED_SCHEMA_SHA256)
        self.assertEqual(hashlib.sha256(pack_raw).hexdigest(), mcp.EXPECTED_PACK_SHA256)
        self.assertEqual(self.pack["schema_sha256"], mcp.EXPECTED_SCHEMA_SHA256)

    def test_duplicate_json_keys_reject(self):
        with self.assertRaisesRegex(mcp.EvidenceError, "duplicate JSON key"):
            mcp._parse_json(b'{"a":1,"a":2}', "duplicate")

    def test_nonfinite_json_rejects(self):
        for raw in (b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(mcp.EvidenceError, "non-finite"):
                    mcp._parse_json(raw, "nonfinite")

    def test_non_utf8_json_rejects(self):
        with self.assertRaisesRegex(mcp.EvidenceError, "not UTF-8"):
            mcp._parse_json(b'{"a":"\xff"}', "encoding")

    def test_extra_root_key_rejects(self):
        broken = copy.deepcopy(self.pack)
        broken["approval"] = "not allowed"
        self.assert_invalid(broken, "extra keys")

    def test_exclusive_owner_rejects(self):
        broken = copy.deepcopy(self.pack)
        broken["prospects"][0]["owner"] = "REVIEWER_ONLY"
        self.assert_invalid(broken, "nonexclusive")

    def test_private_key_rejects_at_any_depth(self):
        broken = copy.deepcopy(self.pack)
        broken["prospects"][0]["contact_email"] = "private@example.invalid"
        with self.assertRaisesRegex(mcp.EvidenceError, "extra keys|private"):
            mcp.validate(ROOT, broken, self.schema)

    def test_repository_path_traversal_rejects(self):
        broken = copy.deepcopy(self.pack)
        item = broken["prospects"][0]
        item["path"] = "src/../secret.py"
        item["raw_url"] = "https://raw.githubusercontent.com/%s/%s/src/../secret.py" % (
            item["repository"], item["commit"]
        )
        item["commit_url"] = "https://github.com/%s/blob/%s/src/../secret.py" % (
            item["repository"], item["commit"]
        )
        self.assert_invalid(broken, "traversal")

    def test_credentials_ports_queries_and_fragments_reject(self):
        bad_urls = (
            "https://user:secret@raw.githubusercontent.com/x/y/z/p",
            "https://raw.githubusercontent.com:443/x/y/z/p",
            "https://raw.githubusercontent.com/x/y/z/p?q=1",
            "https://raw.githubusercontent.com/x/y/z/p#fragment",
        )
        for bad_url in bad_urls:
            with self.subTest(url=bad_url):
                broken = copy.deepcopy(self.pack)
                broken["prospects"][0]["raw_url"] = bad_url
                with self.assertRaises(mcp.EvidenceError):
                    mcp.validate(ROOT, broken, self.schema)

    def test_cross_field_url_mismatch_rejects(self):
        broken = copy.deepcopy(self.pack)
        broken["prospects"][0]["raw_url"] = broken["prospects"][1]["raw_url"]
        self.assert_invalid(broken, "does not match")

    def test_signal_observation_mismatch_rejects(self):
        broken = copy.deepcopy(self.pack)
        broken["prospects"][0]["signals"]["legacy_initialize"] = False
        self.assert_invalid(broken, "do not match")

    def test_out_of_range_line_rejects(self):
        broken = copy.deepcopy(self.pack)
        broken["prospects"][0]["observations"][0]["line"] = 999999
        self.assert_invalid(broken, "outside source")

    def test_validate_cli_is_canonical(self):
        self.assertEqual(self.run_cli("validate")["status"], "VALID")

    def test_list_cli_is_static_evidence_only(self):
        result = self.run_cli("list")
        self.assertEqual(result["status"], "VERIFIED_STATIC_SIGNAL_LIST")
        self.assertEqual(len(result["prospects"]), 10)
        self.assertTrue(all(item["evidence_state"] == "VERIFIED_STATIC_SIGNAL" for item in result["prospects"]))

    def test_next_cli_is_fail_closed(self):
        self.assertEqual(
            self.run_cli("next"),
            {"status": "NONE_READY", "reason": "STATIC_PROTOCOL_SIGNAL_EVIDENCE_ONLY"},
        )

    def test_offline_commands_never_build_network_opener(self):
        for command in ("validate", "list", "next"):
            with self.subTest(command=command), mock.patch.object(
                mcp, "build_opener", side_effect=AssertionError("network attempted")
            ), mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(mcp.main([command, "--root", str(ROOT)]), 0)

    def _fake_item(self, raw: bytes):
        return {
            "id": "fake-source",
            "raw_url": "https://raw.githubusercontent.com/example/project/0123456789abcdef0123456789abcdef01234567/path.txt",
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1": mcp._git_blob_sha1(raw),
            "line_count": len(raw.decode("utf-8").splitlines()),
            "facts": [{"line": 2, "statement": "test", "excerpt": "beta"}],
        }

    def test_source_verifier_checks_bytes_hash_blob_and_excerpt(self):
        raw = b"alpha\nbeta\n"
        item = self._fake_item(raw)
        opener = FakeOpener(FakeResponse(raw, item["raw_url"]))
        mcp._verify_source(item, opener)
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(opener.requests[0][1], 20)

    def test_source_verifier_rejects_changed_final_url(self):
        raw = b"alpha\nbeta\n"
        item = self._fake_item(raw)
        opener = FakeOpener(FakeResponse(raw, item["raw_url"] + "/redirected"))
        with self.assertRaisesRegex(mcp.EvidenceError, "final URL changed"):
            mcp._verify_source(item, opener)

    def test_source_verifier_rejects_content_length_drift(self):
        raw = b"alpha\nbeta\n"
        item = self._fake_item(raw)
        opener = FakeOpener(FakeResponse(raw, item["raw_url"], content_length="999"))
        with self.assertRaisesRegex(mcp.EvidenceError, "Content-Length drifted"):
            mcp._verify_source(item, opener)

    def test_source_verifier_rejects_crlf(self):
        raw = b"alpha\r\nbeta\r\n"
        item = self._fake_item(raw)
        opener = FakeOpener(FakeResponse(raw, item["raw_url"]))
        with self.assertRaisesRegex(mcp.EvidenceError, "not LF-only"):
            mcp._verify_source(item, opener)

    def test_source_verifier_rejects_excerpt_drift(self):
        raw = b"alpha\nbeta\n"
        item = self._fake_item(raw)
        item["facts"][0]["excerpt"] = "gamma"
        opener = FakeOpener(FakeResponse(raw, item["raw_url"]))
        with self.assertRaisesRegex(mcp.EvidenceError, "excerpt drifted"):
            mcp._verify_source(item, opener)

    def test_redirect_handler_refuses_redirects(self):
        self.assertIsNone(mcp._NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://example.com"))

    def test_load_rejects_raw_pack_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / mcp.PACK_PATH.parent).mkdir(parents=True)
            (root / mcp.SCHEMA_PATH).write_bytes((ROOT / mcp.SCHEMA_PATH).read_bytes())
            (root / mcp.PACK_PATH).write_bytes((ROOT / mcp.PACK_PATH).read_bytes() + b" ")
            with self.assertRaisesRegex(mcp.EvidenceError, "raw SHA-256 drifted"):
                mcp.load(root)

    def test_load_accepts_portable_crlf_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / mcp.PACK_PATH.parent).mkdir(parents=True)
            schema = mcp._repository_bytes((ROOT / mcp.SCHEMA_PATH).read_bytes(), str(mcp.SCHEMA_PATH))
            pack = mcp._repository_bytes((ROOT / mcp.PACK_PATH).read_bytes(), str(mcp.PACK_PATH))
            (root / mcp.SCHEMA_PATH).write_bytes(schema.replace(b"\n", b"\r\n"))
            (root / mcp.PACK_PATH).write_bytes(pack.replace(b"\n", b"\r\n"))
            loaded, _schema = mcp.load(root)
            self.assertEqual(loaded["kind"], "MCP_STATELESS_72_VERIFIED_STATIC_SIGNAL_PACK")

    def test_repository_bytes_reject_lone_carriage_return(self):
        with self.assertRaisesRegex(mcp.EvidenceError, "unsupported carriage return"):
            mcp._repository_bytes(b"alpha\rbeta\n", "fixture")


if __name__ == "__main__":
    unittest.main()
