from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("make_submission", HERE / "make_submission.py")
assert SPEC and SPEC.loader
submission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(submission)


def base_files(**patch):
    config = {
        "r03_full_router": False,
        "r04_sale_window": False,
        "r04_sale_horizon": 8,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": True,
        "r04_no_late_sale_advance": True,
        "r04_no_late_sale_advance_step": 648,
        "r04_strawberry_topup": True,
        "r01_shop_router": False,
        "r02_route_bank": False,
        "sentinel": "unchanged",
    }
    config.update(patch)
    return {
        "TITAN-CONFIG.json": (json.dumps(config, indent=2) + "\n").encode("utf-8"),
        "main.py": b"# unchanged\n",
    }


class SubmissionConfigTests(unittest.TestCase):
    def test_field_gated_tuple_is_forced_and_input_is_unchanged(self):
        source = base_files()
        original = copy.deepcopy(source)
        out, config = submission.apply_submission_config(source)
        self.assertEqual(source, original)
        self.assertIs(config["r04_sale_window"], True)
        self.assertIs(config["r04_sale_fertilizer"], True)
        self.assertIs(config["r04_cattle_early"], False)
        self.assertEqual(config["r04_sale_horizon"], 8)
        self.assertIs(config["r04_no_late_sale_advance"], True)
        self.assertIs(config["r04_strawberry_topup"], True)
        self.assertEqual(config["r04_no_late_sale_advance_step"], 648)
        self.assertEqual(config["sentinel"], "unchanged")
        self.assertEqual(out["main.py"], source["main.py"])
        self.assertNotEqual(out["TITAN-CONFIG.json"], source["TITAN-CONFIG.json"])

    def test_shipped_h4_and_l3_keys_are_preserved_not_forced(self):
        _, config = submission.apply_submission_config(
            base_files(r04_strawberry_topup=False, r04_no_late_sale_advance=False)
        )
        self.assertIs(config["r04_strawberry_topup"], False)
        self.assertIs(config["r04_no_late_sale_advance"], False)

    def test_field_gated_tuple_does_not_inherit_future_base_horizon(self):
        _, config = submission.apply_submission_config(base_files(r04_sale_horizon=10))
        self.assertEqual(config["r04_sale_horizon"], 8)
        self.assertIs(config["r04_sale_fertilizer"], True)
        self.assertIs(config["r04_cattle_early"], False)

    def test_sale_fertilizer_is_forced_on_even_if_base_default_moves(self):
        out, config = submission.apply_submission_config(base_files(r04_sale_fertilizer=False))
        self.assertIs(config["r04_sale_fertilizer"], True)
        self.assertIs(config["r04_cattle_early"], False)
        self.assertIn(b'"r04_sale_fertilizer": true', out["TITAN-CONFIG.json"])

    def test_horizon_override_is_positive_integer_and_does_not_touch_other_keys(self):
        _, config = submission.apply_submission_config(base_files(), 5)
        self.assertEqual(config["r04_sale_horizon"], 5)
        self.assertEqual(config["sentinel"], "unchanged")
        self.assertIs(config["r04_strawberry_topup"], True)
        self.assertIs(config["r04_no_late_sale_advance"], True)
        for bad in (0, -1, True, 5.0, "5"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(AssertionError, "positive integer"):
                    submission.apply_submission_config(base_files(), bad)

    def test_invalid_cli_horizon_fails_before_package_access(self):
        fake = types.ModuleType("build_v3")

        def forbidden(*_args, **_kwargs):
            self.fail("invalid CLI horizon touched package access")

        fake.package_files = forbidden
        fake.build_bytes = forbidden
        for raw in ("0", "-1"):
            with self.subTest(raw=raw):
                with mock.patch.dict(sys.modules, {"build_v3": fake}):
                    with self.assertRaisesRegex(SystemExit, "sale horizon"):
                        submission.main(["unused-v3", "canonical.tar.gz", "out.tar.gz", raw])

    def test_bad_cli_horizon_fails_before_build_import_or_package_access(self):
        # Freeze the reviewed #12380 boundary: malformed CLI input must die before
        # sys.path mutation or a builder module can import/execute.
        for raw in ("0", "-1", "not-an-int"):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "build_v3.py").write_text(
                    "raise RuntimeError('BUILD_PATH_TOUCHED')\n", encoding="utf-8"
                )
                original_path = list(sys.path)
                previous_build = sys.modules.pop("build_v3", None)
                try:
                    with self.assertRaisesRegex(SystemExit, "sale horizon"):
                        submission.main([
                            str(root),
                            str(root / "canonical-does-not-exist.tar.gz"),
                            str(root / "submission.tar.gz"),
                            raw,
                        ])
                    self.assertEqual(sys.path, original_path)
                    self.assertNotIn("build_v3", sys.modules)
                    self.assertFalse((root / "submission.tar.gz").exists())
                finally:
                    sys.path[:] = original_path
                    sys.modules.pop("build_v3", None)
                    if previous_build is not None:
                        sys.modules["build_v3"] = previous_build

    def test_base_horizon_contract_fails_closed_before_transform(self):
        for bad in (None, 0, -1, True, 8.0, "8"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(AssertionError, "base r04_sale_horizon must be a positive integer"):
                    submission.apply_submission_config(base_files(r04_sale_horizon=bad))

    def test_submission_boolean_contracts_fail_closed(self):
        for key in ("r04_sale_window", "r04_sale_fertilizer", "r04_cattle_early"):
            for bad in (None, 0, 1, "false", [], {}):
                with self.subTest(key=key, bad=bad):
                    files = base_files(**{key: bad})
                    with self.assertRaisesRegex(AssertionError, "JSON boolean"):
                        submission.apply_submission_config(files)

    def test_base_route_must_still_ship_off_before_submission_transform(self):
        with self.assertRaisesRegex(AssertionError, "must ship with r04_sale_window=false"):
            submission.apply_submission_config(base_files(r04_sale_window=True))

    def test_missing_config_member_fails(self):
        with self.assertRaises(KeyError):
            submission.apply_submission_config({"main.py": b"x"})


if __name__ == "__main__":
    unittest.main()
