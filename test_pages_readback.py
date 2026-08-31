import base64
import json
import unittest

import pages_readback


class PagesReadbackContract(unittest.TestCase):
    def test_exact_bytes_are_live(self):
        self.assertEqual(pages_readback.classify(b"new marker", b"new marker", b"marker")[0], "LIVE")

    def test_missing_marker_is_stale(self):
        status, present, _ = pages_readback.classify(b"new marker", b"old page", b"marker")
        self.assertEqual((status, present), ("STALE", False))

    def test_changed_bytes_with_marker_are_mismatch(self):
        status, present, _ = pages_readback.classify(b"new marker", b"new marker changed", b"marker")
        self.assertEqual((status, present), ("MISMATCH", True))

    def test_marker_must_exist_in_pinned_source(self):
        status, _, detail = pages_readback.classify(b"source", b"source", b"missing")
        self.assertEqual(status, "MISMATCH")
        self.assertIn("pinned source", detail)

    def test_pages_url_quotes_path_components(self):
        self.assertEqual(
            pages_readback.pages_url("owner/repo", "nested/a b.html"),
            "https://owner.github.io/repo/nested/a%20b.html",
        )

    def test_check_pins_main_and_compares_served_bytes(self):
        source = b"<title>marker</title>"
        requested = []

        def fake_fetch(url):
            requested.append(url)
            if url.endswith("commits/main"):
                return json.dumps({"sha": "a" * 40}).encode()
            if "/contents/page.html?ref=" in url:
                encoded = base64.b64encode(source).decode()
                wrapped = encoded[:8] + "\n" + encoded[8:] + "\n"
                return json.dumps({"sha": "b" * 40, "content": wrapped}).encode()
            return source

        result = pages_readback.check("owner/repo", "page.html", "marker", fake_fetch)
        self.assertEqual(result.status, "LIVE")
        self.assertIn("ref=" + "a" * 40, requested[1])
        self.assertEqual(result.blob_sha, "b" * 40)

    def test_cli_transport_failure_is_unavailable(self):
        original = pages_readback.check
        pages_readback.check = lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline"))
        try:
            self.assertEqual(pages_readback.main(["page.html"]), 2)
        finally:
            pages_readback.check = original


if __name__ == "__main__":
    unittest.main()
