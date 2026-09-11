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
    def test_field_gated_tuple_is_forced_and_shipped_lanes_survive(self):
        source = base_files()
        original = copy.deepcopy(source)
        out, config = submission.apply_submission_config(source)
        self.assertEqual(source, original)
        self.assertIs(config["r04_sale_window"], True)
        self.assertIs(config["r04_sale_fertilizer"], True)
        self.assertIs(config["r04_cattle_early"], False)
        self.assertEqual(config["r04_sale_horizon"], 8)
        self.assertIs(config["r04_no_late_sale_advance"], True)
        self.assertEqual(config["r04_no_late_sale_advance_step"], 648)
        self.assertIs(config["r04_strawberry_topup"], True)
        self.assertEqual(config["sentinel"], "unchanged")
        self.assertEqual(out["main.py"], source["main.py"])
        self.assertNotEqual(out["TITAN-CONFIG.json"], source["TITAN-CONFIG.json"])

    def test_default_submission_horizon_does_not_inherit_future_base_horizon(self):
        _, config = submission.apply_submission_config(base_files(r04_sale_horizon=10))
        self.assertEqual(config["r04_sale_horizon"], 8)
        self.assertIs(config["r04_no_late_sale_advance"], True)
        self.assertIs(config["r04_strawberry_topup"], True)

    def test_sale_fertilizer_is_forced_on_even_if_base_default_moves(self):
        out, config = submission.apply_submission_config(base_files(r04_sale_fertilizer=False))
        self.assertIs(config["r04_sale_fertilizer"], True)
        self.assertIs(config["r04_cattle_early"], False)
        self.assertIn(b'"r04_sale_fertilizer": true', out["TITAN-CONFIG.json"])

    def test_horizon_override_is_positive_integer_and_preserves_shipped_lanes(self):
        _, config = submission.apply_submission_config(base_files(), 5)
        self.assertEqual(config["r04_sale_horizon"], 5)
        self.assertIs(config["r04_no_late_sale_advance"], True)
        self.assertIs(config["r04_strawberry_topup"], True)
        self.assertEqual(config["sentinel"], "unchanged")
        for bad in (0, -1, True, 5.0, "5"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(AssertionError, "positive integer"):
                    submission.apply_submission_config(base_files(), bad)

    def test_invalid_cli_horizon_fails_before_sys_path_or_package_access(self):
        fake = types.ModuleType("build_v3")

        def forbidden(*_args, **_kwargs):
            self.fail("invalid CLI horizon touched package access")

        fake.package_files = forbidden
        fake.build_bytes = forbidden
        original_path = list(sys.path)
        for raw in ("0", "-1"):
            with self.subTest(raw=raw):
                with mock.patch.dict(sys.modules, {"build_v3": fake}):
                    with self.assertRaisesRegex(AssertionError, "submission horizon must be a positive integer"):
                        submission.main(["poison-v3-path", "canonical.tar.gz", "out.tar.gz", raw])
                self.assertEqual(sys.path, original_path)

    def test_non_integer_cli_horizon_fails_before_package_access(self):
        fake = types.ModuleType("build_v3")

        def forbidden(*_args, **_kwargs):
            self.fail("non-integer CLI horizon touched package access")

        fake.package_files = forbidden
        fake.build_bytes = forbidden
        original_path = list(sys.path)
        with mock.patch.dict(sys.modules, {"build_v3": fake}):
            with self.assertRaises(ValueError):
                submission.main(["poison-v3-path", "canonical.tar.gz", "out.tar.gz", "not-an-int"])
        self.assertEqual(sys.path, original_path)

    def test_invalid_cli_horizon_never_imports_poison_builder_or_creates_output(self):
        original_path = list(sys.path)
        original_builder = sys.modules.pop("build_v3", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "build_v3.py").write_text(
                    "raise RuntimeError('BUILD_PATH_TOUCHED')\n", encoding="utf-8"
                )
                for raw, expected in (
                    ("0", AssertionError),
                    ("-1", AssertionError),
                    ("not-an-int", ValueError),
                ):
                    with self.subTest(raw=raw):
                        output = root / ("out-%s.tar.gz" % raw.replace("-", "neg"))
                        with self.assertRaises(expected) as caught:
                            submission.main([str(root), "canonical.tar.gz", str(output), raw])
                        self.assertNotIn("BUILD_PATH_TOUCHED", str(caught.exception))
                        self.assertFalse(output.exists())
                        self.assertEqual(sys.path, original_path)
                        self.assertNotIn("build_v3", sys.modules)
        finally:
            if original_builder is not None:
                sys.modules["build_v3"] = original_builder
            else:
                sys.modules.pop("build_v3", None)
            sys.path[:] = original_path

    def test_base_horizon_contract_fails_closed_before_transform(self):
        for bad in (None, 0, -1, True, 8.0, "8"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(AssertionError, "base r04_sale_horizon must be a positive integer"):
                    submission.apply_submission_config(base_files(r04_sale_horizon=bad))

    def test_submission_boolean_contracts_fail_closed(self):
        keys = (
            "r04_sale_window",
            "r04_sale_fertilizer",
            "r04_cattle_early",
            "r04_no_late_sale_advance",
            "r04_strawberry_topup",
        )
        for key in keys:
            for bad in (None, 0, 1, "false", [], {}):
                with self.subTest(key=key, bad=bad):
                    with self.assertRaisesRegex(AssertionError, "JSON boolean"):
                        submission.apply_submission_config(base_files(**{key: bad}))

    def test_base_route_must_still_ship_off_before_submission_transform(self):
        with self.assertRaisesRegex(AssertionError, "must ship with r04_sale_window=false"):
            submission.apply_submission_config(base_files(r04_sale_window=True))

    def test_shipped_h4_and_gated_l3_must_be_on_before_transform(self):
        with self.assertRaisesRegex(AssertionError, "rival-gated L3"):
            submission.apply_submission_config(base_files(r04_no_late_sale_advance=False))
        with self.assertRaisesRegex(AssertionError, "H4 strawberry"):
            submission.apply_submission_config(base_files(r04_strawberry_topup=False))

    def test_missing_config_member_fails(self):
        with self.assertRaises(KeyError):
            submission.apply_submission_config({"main.py": b"x"})


if __name__ == "__main__":
    unittest.main()
