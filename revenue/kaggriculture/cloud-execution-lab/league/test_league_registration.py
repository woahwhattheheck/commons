# SPDX-License-Identifier: Apache-2.0
"""Contracts for challenger registration and contestant staging."""
import json
import os
import tempfile
import unittest

from registration import (
    RegistrationError,
    check_entrypoint_callable,
    load_registry,
    register_challenger,
    validate_registration,
)


def real_challenger():
    return {
        "name": "v3-final-crop-binding",
        "entry": "cloud-execution-lab/candidates/v3-final-crop-binding/candidate_main.py",
        "callable": "agent",
        "support_modules": [
            "cloud-runtime-pulse/observed_clone.py",
            "cloud-quickstep/seller_snapshot.py",
        ],
        "registered": "2026-09-10",
        "active": True,
        "notes": "test",
    }


class ValidateRegistrationTest(unittest.TestCase):
    def test_real_challenger_validates(self):
        normalized = validate_registration(real_challenger())
        self.assertEqual(len(normalized["sha256"]), 64)

    def test_bad_names_rejected(self):
        for bad in ("", "UPPER", "has space", "-lead", "a" * 70):
            with self.assertRaises(RegistrationError):
                validate_registration(dict(real_challenger(), name=bad))

    def test_missing_entry_rejected(self):
        with self.assertRaises(RegistrationError):
            validate_registration(dict(real_challenger(), entry="nope/missing.py"))

    def test_entry_escape_rejected(self):
        with self.assertRaises(RegistrationError):
            validate_registration(dict(real_challenger(),
                                       entry="../outside.py"))

    def test_missing_support_module_rejected(self):
        data = real_challenger()
        data["support_modules"] = ["cloud-runtime-pulse/nope.py"]
        with self.assertRaises(RegistrationError):
            validate_registration(data)

    def test_sha_drift_fails_closed(self):
        data = real_challenger()
        data["sha256"] = "0" * 64
        with self.assertRaises(RegistrationError):
            validate_registration(data)


class RegistryTest(unittest.TestCase):
    def test_register_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = register_challenger(tmp, "v3-final-crop-binding",
                                       real_challenger()["entry"],
                                       support_modules=real_challenger()["support_modules"])
            self.assertTrue(path.name.endswith(".json"))
            active = load_registry(tmp)
            self.assertEqual([c["name"] for c in active], ["v3-final-crop-binding"])

    def test_double_register_without_force_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            register_challenger(tmp, "v3-final-crop-binding",
                                real_challenger()["entry"])
            with self.assertRaises(RegistrationError):
                register_challenger(tmp, "v3-final-crop-binding",
                                    real_challenger()["entry"])

    def test_inactive_challenger_not_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = register_challenger(tmp, "v3-final-crop-binding",
                                       real_challenger()["entry"])
            data = json.loads(path.read_text())
            data["active"] = False
            path.write_text(json.dumps(data))
            self.assertEqual(load_registry(tmp), [])

    def test_empty_registry_dir_loads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_registry(os.path.join(tmp, "missing")), [])


class EntrypointCheckTest(unittest.TestCase):
    def test_fake_entrypoint_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Build a fake repo root with an entry + support module.
            root = os.path.join(tmp, "root")
            os.makedirs(os.path.join(root, "cand"))
            entry = os.path.join(root, "cand", "main.py")
            with open(entry, "w") as handle:
                handle.write("import helper\ndef agent(obs, cfg=None):\n    return helper.go()\n")
            os.makedirs(os.path.join(root, "sup"))
            with open(os.path.join(root, "sup", "helper.py"), "w") as handle:
                handle.write("def go():\n    return {}\n")
            import registration
            old = registration.REPO_ROOT
            registration.REPO_ROOT = type(old)(root)
            try:
                check_entrypoint_callable("cand/main.py", "agent", ["sup/helper.py"])
            finally:
                registration.REPO_ROOT = old

    def test_missing_callable_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "root")
            os.makedirs(root)
            entry = os.path.join(root, "main.py")
            with open(entry, "w") as handle:
                handle.write("x = 1\n")
            import registration
            old = registration.REPO_ROOT
            registration.REPO_ROOT = type(old)(root)
            try:
                with self.assertRaises(RegistrationError):
                    check_entrypoint_callable("main.py", "agent", [])
            finally:
                registration.REPO_ROOT = old


if __name__ == "__main__":
    unittest.main()
