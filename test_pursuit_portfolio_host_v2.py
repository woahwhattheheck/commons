from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import cli, host
import revenue.pursuit_portfolio.core_v2 as core
from revenue.pursuit_portfolio.core import PortfolioError
from test_pursuit_portfolio import NOW, authority_rows, opp, source

KEY_ID = "owner-root-v2"
KEY_BYTES = b"k" * 32
LATER = "2026-09-13T14:00:01Z"


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


class HostV2Tests(unittest.TestCase):
    def _key_file(self, root: Path, *, key_bytes: bytes = KEY_BYTES) -> Path:
        path = root / "authority-key.json"
        path.write_bytes(
            canonical(
                {
                    "schema": host.KEY_SCHEMA,
                    "key_id": KEY_ID,
                    "key_hex": key_bytes.hex(),
                }
            )
        )
        if os.name == "posix":
            path.chmod(0o600)
        return path

    def _floor_file(
        self,
        root: Path,
        authority: dict,
        *,
        key_bytes: bytes = KEY_BYTES,
        updated_at: str = NOW,
    ) -> Path:
        normalized = core.normalize_upstream_authority(authority)
        unsigned = {
            "authority_sha256": core.upstream_authority_sha256(normalized),
            "key_id": KEY_ID,
            "revision": normalized["revision"],
            "schema": host.FLOOR_SCHEMA,
            "updated_at": updated_at,
        }
        value = {
            **unsigned,
            "hmac_sha256": hmac.new(
                key_bytes, canonical(unsigned), hashlib.sha256
            ).hexdigest(),
        }
        path = root / "authority-floor.json"
        path.write_bytes(canonical(value))
        if os.name == "posix":
            path.chmod(0o600)
        return path

    def _state(self, root: Path, authority: dict):
        return self._key_file(root), self._floor_file(root, authority)

    def _one(self, *, max_age=86400):
        row = opp("A", 10, {"proposal": 1})
        data = source([row], max_age=max_age)
        authority = authority_rows(data["opportunities"], captured="2026-09-13T13:00:00Z")
        return data, authority

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_fixed_host_floor_compile_and_verify(self):
        data, authority = self._one()
        with tempfile.TemporaryDirectory() as tmp:
            key_path, floor_path = self._state(Path(tmp), authority)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                value = host.compile_current(data, authority)
                verified = host.verify_current_bytes(
                    value.compiled.result_bytes,
                    value.compiled.markdown_bytes,
                    value.compiled.receipt_bytes,
                    value.host_seal_bytes,
                )
        self.assertEqual(value.compiled.result["selected_opportunity_ids"], ["A"])
        self.assertTrue(verified["host_seal_verified"])
        self.assertTrue(verified["verified_current"])
        self.assertEqual(verified["authority_floor_revision"], 1)

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_caller_selected_authority_digest_cannot_replace_fixed_floor(self):
        data, legitimate = self._one()
        forged = deepcopy(legitimate)
        forged["rows"][0]["upstream_state"] = "CURABLE"
        with tempfile.TemporaryDirectory() as tmp:
            key_path, floor_path = self._state(Path(tmp), legitimate)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                with self.assertRaisesRegex(PortfolioError, "superseded"):
                    host.compile_current(data, forged)

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_g1_ready_replay_fails_after_g2_withdrawal_while_g1_is_fresh(self):
        data, authority_g1 = self._one(max_age=86400)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._state(root, authority_g1)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                historical = host.compile_current(data, authority_g1)

            authority_g2 = authority_rows(
                data["opportunities"],
                states={"A": "HOLD"},
                captured="2026-09-13T14:01:00Z",
            )
            authority_g2["revision"] = 2
            self._floor_file(root, authority_g2, updated_at="2026-09-13T14:02:00Z")
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value="2026-09-13T14:03:00Z"):
                with self.assertRaisesRegex(PortfolioError, "superseded"):
                    host.verify_current_bytes(
                        historical.compiled.result_bytes,
                        historical.compiled.markdown_bytes,
                        historical.compiled.receipt_bytes,
                        historical.host_seal_bytes,
                    )

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_same_revision_authority_fork_does_not_revalidate_old_package(self):
        data, authority_a = self._one()
        authority_b = authority_rows(
            data["opportunities"],
            states={"A": "CURABLE"},
            captured="2026-09-13T13:30:00Z",
        )
        self.assertEqual(authority_a["revision"], authority_b["revision"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._state(root, authority_a)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                historical = host.compile_current(data, authority_a)
            self._floor_file(root, authority_b, updated_at=NOW)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                with self.assertRaisesRegex(PortfolioError, "superseded"):
                    host.verify_current_bytes(
                        historical.compiled.result_bytes,
                        historical.compiled.markdown_bytes,
                        historical.compiled.receipt_bytes,
                        historical.host_seal_bytes,
                    )

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_floor_hmac_tamper_fails_closed(self):
        data, authority = self._one()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._state(root, authority)
            floor = json.loads(floor_path.read_text(encoding="utf-8"))
            floor["revision"] += 1
            floor_path.write_bytes(canonical(floor))
            floor_path.chmod(0o600)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                with self.assertRaisesRegex(PortfolioError, "authority floor: HMAC mismatch"):
                    host.compile_current(data, authority)

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_floor_move_during_compile_fails_closed(self):
        data, authority_a = self._one()
        authority_b = deepcopy(authority_a)
        authority_b["rows"][0]["upstream_state"] = "CURABLE"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._state(root, authority_a)
            key = host.load_host_key(key_path)
            floor_a = host._load_floor_at(floor_path, key, NOW)
            self._floor_file(root, authority_b, updated_at=NOW)
            floor_b = host._load_floor_at(floor_path, key, NOW)
            self._floor_file(root, authority_a, updated_at=NOW)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW), mock.patch.object(
                host, "_load_floor_at", side_effect=[floor_a, floor_b]
            ):
                with self.assertRaisesRegex(PortfolioError, "changed during"):
                    host.compile_current(data, authority_a)

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_fresh_current_verification_rejects_newly_stale_evidence(self):
        data, authority = self._one(max_age=3600)
        with tempfile.TemporaryDirectory() as tmp:
            key_path, floor_path = self._state(Path(tmp), authority)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                historical = host.compile_current(data, authority)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=LATER):
                with self.assertRaisesRegex(PortfolioError, "allocation decision is stale"):
                    host.verify_current_bytes(
                        historical.compiled.result_bytes,
                        historical.compiled.markdown_bytes,
                        historical.compiled.receipt_bytes,
                        historical.host_seal_bytes,
                    )

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_host_seal_binds_full_owner_planning_generation(self):
        data, authority = self._one()
        with tempfile.TemporaryDirectory() as tmp:
            key_path, floor_path = self._state(Path(tmp), authority)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                legitimate = host.compile_current(data, authority)
                modified = deepcopy(data)
                modified["opportunities"][0]["priority_units"] = 999
                altered = core.compile_portfolio(
                    modified,
                    upstream_authority=authority,
                    trusted_upstream_authority_sha256=core.upstream_authority_sha256(authority),
                    evaluated_at=NOW,
                )
                with self.assertRaisesRegex(PortfolioError, "package/current-floor binding"):
                    host.verify_current_bytes(
                        altered.result_bytes,
                        altered.markdown_bytes,
                        altered.receipt_bytes,
                        legitimate.host_seal_bytes,
                    )

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_ancestor_symlink_is_refused_for_candidate_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            target = real / "input.json"
            target.write_text("{}", encoding="utf-8")
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaises(Exception):
                host.load_candidate_json(alias / "input.json", "input")

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_publish_round_trip_uses_preexisting_retained_directory(self):
        data, authority = self._one()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._state(root, authority)
            out = root / "out"
            out.mkdir(mode=0o700)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                value = host.compile_current(data, authority)
                host.publish_current(value, out)
                verified = host.verify_current_directory(out)
            self.assertTrue(verified["verified_current"])
            self.assertEqual((out / "host-seal.json").read_bytes(), value.host_seal_bytes)

    @unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
    def test_late_publication_failure_preserves_prior_visible_truth(self):
        data, authority = self._one()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._state(root, authority)
            out = root / "out"
            out.mkdir(mode=0o700)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                value = host.compile_current(data, authority)
            real_write = host._write_owned_relative
            calls = {"count": 0}

            def fail_second(dir_fd, name, payload):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise PortfolioError("injected late failure")
                return real_write(dir_fd, name, payload)

            with mock.patch.object(host, "_write_owned_relative", side_effect=fail_second):
                with self.assertRaisesRegex(PortfolioError, "already-published files: portfolio.json"):
                    host.publish_current(value, out)
            self.assertEqual((out / "portfolio.json").read_bytes(), value.compiled.result_bytes)
            self.assertFalse((out / "portfolio.md").exists())

    @unittest.skipUnless(os.name == "posix", "permission test requires POSIX")
    def test_group_readable_host_key_is_rejected(self):
        data, authority = self._one()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._state(root, authority)
            key_path.chmod(0o640)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                with self.assertRaisesRegex(PortfolioError, "owner-only permissions"):
                    host.compile_current(data, authority)

    def test_cli_has_no_caller_selected_trust_digest_or_floor(self):
        with self.assertRaises(SystemExit) as caught:
            cli.main(
                [
                    "compile",
                    "input.json",
                    "authority.json",
                    "out",
                    "--trusted-authority-sha256",
                    "a" * 64,
                    "--floor",
                    "candidate-floor.json",
                ]
            )
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
