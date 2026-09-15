from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from revenue.pursuit_portfolio import cli
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import _compile_authorized_at
import revenue.pursuit_portfolio.publisher as publisher
from test_pursuit_portfolio_current import (
    KEY,
    NOW,
    portfolio_source,
    signed_authority_for,
)


@unittest.skipUnless(
    os.name == "posix",
    "retained publication generation requires POSIX directory descriptors",
)
class PublicationGenerationTests(unittest.TestCase):
    def test_final_boundary_revalidates_every_visible_artifact(self):
        value = portfolio_source(max_age=86400 * 5)
        compiled = _compile_authorized_at(value, signed_authority_for(value), KEY, NOW)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir(mode=0o700)
            replacement = out / "replacement.tmp"
            replacement.write_bytes(b"attacker replacement")
            replacement.chmod(0o600)

            original = publisher._write_owned_relative

            def replace_first_after_second(dir_fd, name, data):
                identity = original(dir_fd, name, data)
                if name == "portfolio.md":
                    os.replace(
                        "replacement.tmp",
                        "portfolio.json",
                        src_dir_fd=dir_fd,
                        dst_dir_fd=dir_fd,
                    )
                return identity

            with mock.patch.object(
                publisher,
                "_write_owned_relative",
                side_effect=replace_first_after_second,
            ):
                with self.assertRaisesRegex(
                    PortfolioError,
                    "visible output ownership changed: portfolio.json",
                ):
                    publisher.publish_authorized(compiled, out)

            # Failure preserves filesystem evidence and never pathname-deletes
            # the foreign generation that triggered the custody alarm.
            self.assertEqual(
                (out / "portfolio.json").read_bytes(),
                b"attacker replacement",
            )


class CompileReceiptOutputTests(unittest.TestCase):
    def test_compile_reports_hashes_of_exact_persisted_receipt_bytes(self):
        current_receipt_bytes = b'{"current":"receipt"}\n'
        host_seal_bytes = b'{"host":"seal"}\n'
        authorized = SimpleNamespace(
            current_receipt={
                "authority_sha256": "a" * 64,
                "receipt_sha256": "b" * 64,
            },
            current_receipt_bytes=current_receipt_bytes,
            compiled=SimpleNamespace(
                result={
                    "selected_opportunity_ids": ["alpha"],
                    "selected_priority_units": 11,
                }
            ),
        )
        value = SimpleNamespace(
            authorized=authorized,
            host_seal={"hmac_sha256": "c" * 64},
            host_seal_bytes=host_seal_bytes,
        )
        output = io.StringIO()

        with (
            mock.patch.object(cli, "load_current_input", return_value={}),
            mock.patch.object(cli, "read_regular_bytes", return_value=b"{}\n"),
            mock.patch.object(cli, "load_json_bytes", return_value={}),
            mock.patch.object(cli, "compile_current", return_value=value),
            mock.patch.object(cli, "publish_current"),
            redirect_stdout(output),
        ):
            self.assertEqual(
                cli.main(["compile", "input.json", "authority.json", "out"]),
                0,
            )

        observed = json.loads(output.getvalue())
        self.assertEqual(
            observed["current_receipt_sha256"],
            hashlib.sha256(current_receipt_bytes).hexdigest(),
        )
        self.assertEqual(
            observed["host_seal_sha256"],
            hashlib.sha256(host_seal_bytes).hexdigest(),
        )
        self.assertNotEqual(
            observed["current_receipt_sha256"],
            authorized.current_receipt["receipt_sha256"],
        )
        self.assertNotEqual(
            observed["host_seal_sha256"],
            value.host_seal["hmac_sha256"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
