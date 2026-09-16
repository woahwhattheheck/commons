from __future__ import annotations

import copy
import json
import unittest

from revenue.bidder_qualification_vault.v2.engine import RegistryError, compile_registry, load_json_strict, render_markdown
from revenue.bidder_qualification_vault.v2.test_support import H, evidence, payload, req

class HostileTests(unittest.TestCase):
    def state(self, p):
        return compile_registry(p)["requirements"][0]["state"]

    def test_markdown_never_leaks_private_descriptor_or_issuer(self):
        p = payload([evidence("w9", "W9")], [req("r", "W9")])
        md = render_markdown(compile_registry(p))
        self.assertNotIn("synthetic-private-descriptor", md)
        self.assertNotIn("Synthetic Issuer", md)
        self.assertIn("w9", md)
        self.assertIn(H, md)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(RegistryError, "DUPLICATE_JSON_KEY"):
            load_json_strict('{"a":1,"a":2}')

    def test_bool_not_accepted_as_string_or_list(self):
        p = payload()
        p["evidence"][0]["stages"] = True
        with self.assertRaises(RegistryError):
            compile_registry(p)

    def test_unknown_evidence_field_rejected(self):
        p = payload()
        p["evidence"][0]["secret"] = "nope"
        with self.assertRaisesRegex(RegistryError, "KEYS"):
            compile_registry(p)

    def test_bad_sha_rejected(self):
        p = payload()
        p["evidence"][0]["content_sha256"] = "abc"
        with self.assertRaisesRegex(RegistryError, "INVALID_SHA256"):
            compile_registry(p)

    def test_bad_time_rejected(self):
        p = payload()
        p["as_of"] = "2026-09-14T03:50:00+00:00"
        with self.assertRaisesRegex(RegistryError, "INVALID_UTC_SECONDS"):
            compile_registry(p)

    def test_unsafe_id_rejected(self):
        p = payload()
        p["generation_id"] = "../escape"
        with self.assertRaisesRegex(RegistryError, "UNSAFE_ID"):
            compile_registry(p)

    def test_input_not_mutated(self):
        p = payload()
        original = copy.deepcopy(p)
        compile_registry(p)
        self.assertEqual(p, original)

    def test_no_private_descriptor_in_receipt_json(self):
        p = payload()
        raw = json.dumps(compile_registry(p), sort_keys=True)
        self.assertNotIn("synthetic-private-descriptor", raw)
        self.assertNotIn("Synthetic Issuer", raw)
