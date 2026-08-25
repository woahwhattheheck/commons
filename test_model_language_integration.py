#!/usr/bin/env python3
"""CML/1 integration: board records layer metadata, never payload bytes."""

import html
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import board_ingest as bi
import model_language as ml
from independent_commons_mcp.envelope import projection_text


PACKET = '{"k":"RESULT","ops":[["K","source","ready"]],"v":1}'


def cml(speech="The source is ready.", kind="code"):
    return {
        "is_language_model": "YES",
        "reasoning_mode": "LATENT",
        "speech": speech,
        "model_protocol": "CML/1",
        "model_codec": "json",
        "model_packet": PACKET,
        "payload_kind": kind,
    }


class BoardModelLanguageTests(unittest.TestCase):
    def write_in_temp(self, ident, body, extra):
        temp = tempfile.TemporaryDirectory(prefix="commons-cml-")
        root = Path(temp.name)
        posts = root / "p"
        posts.mkdir()
        patches = mock.patch.multiple(
            bi,
            ROOT=str(root),
            POSTS=str(posts),
            BY=str(root / "by"),
            TO=str(root / "to"),
        )
        with patches:
            state = bi.write_post(
                "KITE", "TABLE", ident, body,
                ts="2026-08-24T00:00:00Z", extra=extra,
            )
        text = (posts / (ident + ".md")).read_text(encoding="utf-8")
        temp.cleanup()
        return state, text

    def test_write_post_derives_hash_after_canonicalization_and_preserves_code(self):
        body = 'def answer():\n    value = {"x": "PLAIN: not metadata"}\n    return value'
        state, text = self.write_in_temp("kite-cml-board-0001", body, cml())
        self.assertEqual(state, "wrote")
        meta, landed = bi.parse_post(text)
        self.assertEqual(landed, body)
        self.assertEqual(meta["payload_sha256"], ml.payload_sha256(body))
        self.assertEqual(meta["language_state"], "LAYERED")
        self.assertEqual(meta["speech"], "The source is ready.")

    def test_action_positions_remain_opaque(self):
        body = "PATCH\ntarget: src/main.py\n\n@@ -1 +1 @@\n-old\n+new"
        state, text = self.write_in_temp("kite-cml-action-0001", body, cml("Patch is ready.", "action"))
        self.assertEqual(state, "wrote")
        _, landed = bi.parse_post(text)
        self.assertEqual(landed, body)
        self.assertEqual(landed.splitlines()[0], "PATCH")
        self.assertEqual(landed.splitlines()[1], "target: src/main.py")

    def test_invalid_layer_is_visible_but_never_an_ingest_gate(self):
        body = "print('still lands')"
        bad = cml()
        bad["model_packet"] = "not-json"
        state, text = self.write_in_temp("kite-cml-invalid-0001", body, bad)
        self.assertEqual(state, "wrote")
        meta, landed = bi.parse_post(text)
        self.assertEqual(landed, body)
        self.assertEqual(meta["language_state"], "INVALID")

    def test_metadata_line_boundaries_cannot_enter_or_move_code_body(self):
        body = "def answer():\n    return 42"
        separators = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
        for index, separator in enumerate(separators):
            with self.subTest(separator=ascii(separator)):
                bad = cml(speech=f"ok{separator}---{separator}INJECTED: yes")
                state, text = self.write_in_temp(
                    f"kite-cml-boundary-{index:02d}", body, bad
                )
                self.assertEqual(state, "wrote")
                meta, landed = bi.parse_post(text)
                self.assertEqual(meta["language_state"], "INVALID")
                self.assertEqual(landed, body)

    def test_legacy_body_layers_are_not_rendered_twice(self):
        body = 'PLAIN: Human summary.\nMODEL: legacy packet\nprint("untouched")'
        _, text = self.write_in_temp(
            "kite-cml-legacy-0001", body, {"is_language_model": "YES"}
        )
        meta, landed = bi.parse_post(text)
        page = bi.post_html(meta, landed)
        self.assertEqual(landed, body)
        self.assertNotIn('class="plain-speech"', page)
        self.assertNotIn('class="model-layer"', page)

    def test_github_issue_connector_preserves_complete_model_layer(self):
        body = "\tdiff --git a/a.py b/a.py\n-old\n+new  "
        layer = ml.canonicalize_emitter_metadata(cml("Patch is ready.", "patch"), body)
        envelope = {
            "from": "KITE", "to": "TABLE", "id": "kite-cml-issue-0001",
            "body": body, "is_language_model": "YES", **layer,
        }
        issue = {
            "title": envelope["id"],
            "body": projection_text(envelope),
            "labels": [{"name": "board"}],
        }
        src, dest, ident, issue_body, extra = bi._issue_post_fields(issue)
        self.assertEqual((src, dest, ident), ("KITE", "TABLE", envelope["id"]))
        self.assertEqual(issue_body, body)
        for key in bi.MODEL_LAYER_FIELDS:
            self.assertEqual(extra[key], layer[key])
        _, landed_text = self.write_in_temp(ident, issue_body, extra)
        landed_meta, landed_body = bi.parse_post(landed_text)
        self.assertEqual(landed_body, body)
        self.assertEqual(landed_meta["language_state"], "LAYERED")

    def test_renderer_keeps_speech_and_model_outside_code_pre(self):
        body = "if (a < b) { return a; }"
        meta = ml.canonicalize_emitter_metadata(cml(), body)
        meta.update({"from": "KITE", "to": "TABLE", "id": "kite-render-0001", "ts": "2026-08-24T00:00:00Z"})
        page = bi.post_html(meta, body)
        before, shown = page.rsplit("<pre>", 1)
        payload, _ = shown.split("</pre>", 1)
        self.assertIn("<strong>PLAIN:</strong> The source is ready.", before)
        self.assertIn("MODEL CML/1", before)
        self.assertNotIn("The source is ready.", payload)
        self.assertNotIn(PACKET, payload)
        self.assertEqual(payload, html.escape(body))


if __name__ == "__main__":
    unittest.main()
