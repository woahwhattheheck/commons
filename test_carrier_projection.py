#!/usr/bin/env python3
"""Carrier materialization cannot be confused with an arbitrary remint."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from carrier_projection import (  # noqa: E402
    CARRIER_ONLY,
    DURABLE_ON_MAIN,
    MAX_PROJECTION_BYTES,
    UNVERIFIED_PRESENT,
    measure_slack_projection,
)


POST_ID = "expected-source-20260825-01"
TS = "1787639560.086549"
REL = os.path.join("p", POST_ID + ".md")
RAW_MAIN_CASES = (
    ("demon-cash-now-overdrive-20260825-01", "1787639560.086549", "DEMON", "TAKING", "69b3b8261570ff721b8bb483ab3a898a98ff4c4a23d1253a7f7ffec3fd133cd6"),
    ("gauge-claude-role-proposal-20260825-01", "1787639959.844249", "GAUGE", "PROPOSAL", "53ba8f1c6633e33269975a57de22c3dbd74034d65a076eb183ce059925f6cbc6"),
    ("gauge-p0-compliance-20260825-01", "1787639440.580749", "GAUGE", "CONTAINMENT_COMPLIANCE", "fbe2e1c146c3e7460d9234f42d97bbf01b25cf38236d0035dacb79e39816a8b3"),
    ("jojo-device-queue-collapse-20260825-01", "1787644306.421489", "JOJO", "TAKING", "932f42dd86fbd54515253af71c5277876ee080b7f4fe6a54d6ae1aa71a7cba1a"),
    ("gauge-zero-audit-20260825-01", "1787638031.533189", "GAUGE", "COORDINATION", "6e26558eb325818999d76c75995bb6f44f015c592d985c27c6c841b25ddb763b"),
    ("jojo-muhlnickel-subagent-protocol-20260825-01", "1787642211.512289", "JOJO", "SHIP_RECEIPT", "0b72a2bec00ef74add9b67dd57e623ff70ee5d9a7a3ab424dc9558f035cf8f5f"),
)


def digest(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def projection(**changes):
    outer = {
        "from": "DEMON",
        "to": "TABLE",
        "id": POST_ID,
        "ts": "2026-08-25T06:32:40.086549Z",
        "carrier": "slack-connector",
        "observed_event": "slack:C0BRGMDQB6G:%s:1" % TS,
        "carrier_ts": TS,
        "durable_ts": "2026-08-25T23:59:21Z",
        "state": "DURABLE_PAGE",
        "subject": "expected source",
        "kind": "slack_message",
    }
    outer.update(changes)
    return (
        "---\n"
        + "\n".join("%s: %s" % item for item in outer.items())
        + "\n---\nfrom: DEMON\nid: "
        + POST_ID
        + "\nkind: TAKING\nsubject: expected source\n\nsource body\n"
    )


def call(root, relative_path, expected_sha256):
    return measure_slack_projection(
        root,
        relative_path,
        post_id=POST_ID,
        carrier_ts=TS,
        sender="DEMON",
        inner_kind="TAKING",
        expected_sha256=expected_sha256,
    )


class TestCarrierProjection(unittest.TestCase):
    def measure(self, body=None, *, expected_sha256=None):
        with tempfile.TemporaryDirectory() as root:
            if body is not None:
                os.mkdir(os.path.join(root, "p"))
                with open(os.path.join(root, REL), "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(body)
            return call(root, REL, expected_sha256 or digest(body or ""))

    def assert_unverified(self, row):
        self.assertEqual(row["state"], UNVERIFIED_PRESENT)
        self.assertFalse(row["provenance_ok"])
        self.assertTrue(row["mismatches"])

    def test_absence_remains_carrier_only(self):
        row = self.measure()
        self.assertEqual(row["state"], CARRIER_ONLY)
        self.assertFalse(row["present"])

    def test_exact_connector_projection_is_durable(self):
        body = projection()
        row = self.measure(body)
        self.assertEqual(row["state"], DURABLE_ON_MAIN)
        self.assertTrue(row["provenance_ok"])
        self.assertEqual(row["mismatches"], [])

    def test_all_six_raw_main_blobs_are_exact_lawful_projections(self):
        for post_id, carrier_ts, sender, inner_kind, sha256 in RAW_MAIN_CASES:
            with self.subTest(post_id=post_id):
                row = measure_slack_projection(
                    ROOT,
                    os.path.join("p", post_id + ".md"),
                    post_id=post_id,
                    carrier_ts=carrier_ts,
                    sender=sender,
                    inner_kind=inner_kind,
                    expected_sha256=sha256,
                )
                self.assertEqual(row["state"], DURABLE_ON_MAIN, row)
                self.assertTrue(row["provenance_ok"])
                self.assertEqual(row["mismatches"], [])

    def test_pinned_projection_identity_is_the_raw_git_blob(self):
        for post_id, _carrier_ts, _sender, _inner_kind, expected_sha256 in RAW_MAIN_CASES:
            relative_path = "p/%s.md" % post_id
            with self.subTest(post_id=post_id):
                raw = subprocess.run(
                    ["git", "cat-file", "blob", "HEAD:" + relative_path],
                    cwd=ROOT,
                    capture_output=True,
                    check=True,
                ).stdout
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected_sha256)
                attribute = subprocess.run(
                    ["git", "check-attr", "text", "--", relative_path],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.strip()
                self.assertEqual(attribute, relative_path + ": text: unset")

    def test_pinned_identity_rejects_body_header_and_second_block_tamper(self):
        valid = projection()
        pinned = digest(valid)
        hostile = (
            valid.replace("source body", "replaced body"),
            valid.replace("kind: slack_message\n", "unexpected: value\nkind: slack_message\n", 1),
            valid + "---\nfrom: DEMON\nid: %s\nkind: TAKING\n---\n" % POST_ID,
        )
        for body in hostile:
            with self.subTest(body=body[-100:]):
                self.assert_unverified(self.measure(body, expected_sha256=pinned))

    def test_semantic_hostile_matrix_fails_closed_even_with_matching_hash(self):
        valid = projection()
        hostile = (
            "manual same-id body",
            projection(carrier="manual"),
            projection(observed_event="slack:C0OTHER:%s:1" % TS),
            projection(carrier_ts="1787639560.000000"),
            projection(state="CARRIER_ONLY"),
            projection(**{"from": "OTHER"}),
            projection(kind="TAKING"),
            projection(durable_ts="2026-08-25 23:59:21"),
            projection(ts="2026-08-25T06:32:40Z"),
            projection().replace("ts: 2026-08-25T06:32:40.086549Z\n", ""),
            projection().replace("to: TABLE\n", "", 1),
            projection().replace("subject: expected source\n", "", 1),
            projection(id="wrong-id"),
            projection().replace("kind: slack_message\n", "unknown: value\nkind: slack_message\n", 1),
            projection().replace("---\n", "--\n", 1),
            projection().replace("\n---\nfrom: DEMON", "\nfrom: DEMON", 1),
            projection().replace(
                "carrier: slack-connector\n",
                "id: %s\ncarrier: slack-connector\n" % POST_ID,
            ),
            projection().replace("id: %s\nkind: TAKING" % POST_ID, "id: wrong-inner\nkind: TAKING"),
            projection().replace("kind: TAKING\n", "kind: OTHER\n", 1),
            projection().replace("kind: TAKING\n", "from: DEMON\nkind: TAKING\n", 1),
            projection().replace("kind: TAKING\n", "kind: TAKING\nunknown: value\n", 1),
            projection().replace("\nkind: TAKING\nsubject: expected source\n", "\nkind: TAKING\n"),
            projection().replace("\nid: %s\nkind: TAKING\n" % POST_ID, "\nkind: TAKING\n"),
        )
        self.assertEqual(len(hostile), 23)
        for body in hostile:
            with self.subTest(body=body[:100]):
                self.assert_unverified(self.measure(body, expected_sha256=digest(body)))
        self.assertEqual(self.measure(valid)["state"], DURABLE_ON_MAIN)

    def test_absolute_and_traversal_paths_fail_closed(self):
        body = projection()
        with tempfile.TemporaryDirectory() as base:
            root = os.path.join(base, "root")
            os.mkdir(root)
            outside = os.path.join(base, "outside.md")
            with open(outside, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
            self.assert_unverified(call(root, outside, digest(body)))
            self.assert_unverified(call(root, os.path.join("..", "outside.md"), digest(body)))
            self.assert_unverified(call(root, "C:\\outside.md", digest(body)))

    def test_link_or_junction_component_fails_closed(self):
        body = projection()
        with tempfile.TemporaryDirectory() as base:
            root = os.path.join(base, "root")
            outside = os.path.join(base, "outside")
            os.mkdir(root)
            os.mkdir(outside)
            with open(os.path.join(outside, POST_ID + ".md"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
            link = os.path.join(root, "p")
            if os.name == "nt":
                made = subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", link, outside],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
            else:
                os.symlink(outside, link)
            self.assert_unverified(call(root, REL, digest(body)))

    def test_link_or_junction_root_fails_closed(self):
        body = projection()
        with tempfile.TemporaryDirectory() as base:
            actual = os.path.join(base, "actual")
            os.mkdir(actual)
            os.mkdir(os.path.join(actual, "p"))
            with open(os.path.join(actual, REL), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
            link = os.path.join(base, "linked-root")
            if os.name == "nt":
                made = subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", link, actual],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
            else:
                os.symlink(actual, link)
            self.assert_unverified(call(link, REL, digest(body)))

    def test_invalid_carrier_timestamp_input_fails_closed(self):
        body = projection()
        with tempfile.TemporaryDirectory() as root:
            os.mkdir(os.path.join(root, "p"))
            with open(os.path.join(root, REL), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
            row = measure_slack_projection(
                root,
                REL,
                post_id=POST_ID,
                carrier_ts="invalid",
                sender="DEMON",
                inner_kind="TAKING",
                expected_sha256=digest(body),
            )
            self.assert_unverified(row)

    def test_oversize_and_invalid_expected_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            os.mkdir(os.path.join(root, "p"))
            with open(os.path.join(root, REL), "wb") as handle:
                handle.write(b"x" * (MAX_PROJECTION_BYTES + 1))
            self.assert_unverified(call(root, REL, "0" * 64))
        self.assert_unverified(self.measure(projection(), expected_sha256="not-a-sha256"))

    def test_all_consumers_import_as_package_and_direct_modules(self):
        names = (
            "cash_now", "claude_intermediate", "containment", "device_queue_cap",
            "finder_zero", "foreign_main", "lda_receipt",
        )
        package = subprocess.run(
            [sys.executable, "-B", "-c", ";".join("import host." + name for name in names)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(package.returncode, 0, package.stdout + package.stderr)
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "host"))
        direct = subprocess.run(
            [sys.executable, "-B", "-c", ";".join("import " + name for name in names)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(direct.returncode, 0, direct.stdout + direct.stderr)


if __name__ == "__main__":
    unittest.main()
