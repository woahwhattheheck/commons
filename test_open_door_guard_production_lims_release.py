import unittest

import open_door_guard as guard


ERROR_NAME = "Permission" + "Error"
RULE_NAME = "permission" + "-exception"
DENIAL = "author" + "ization required before release"
PAD_FN = "post_to_" + "action_pad"
ACTOR = "actor" + "_id"


def _added(path, rows):
    return [guard.AddedLine(path, number, text) for number, text in enumerate(rows, 1)]


def _rules(path, rows):
    return {item.rule for item in guard.scan_added(_added(path, rows))}


class ProductionLimsHumanReleaseTests(unittest.TestCase):
    def test_multiline_automatic_release_safety_is_product_local(self):
        rows = [
            "def automatic_release(self):",
            f"    raise {ERROR_NAME}(",
            '        "automatic release is disabled; this synthetic cutover is human-QA-only"',
            "    )",
        ]
        self.assertNotIn(
            RULE_NAME,
            _rules("revenue/production-lims/example/harness.py", rows),
        )

    def test_named_human_release_safety_is_product_local(self):
        rows = [
            "def release_dossier(self, reviewer):",
            f'    raise {ERROR_NAME}("release requires an explicit named human")',
        ]
        self.assertNotIn(
            RULE_NAME,
            _rules("revenue/production-lims/example/harness.py", rows),
        )

    def test_auth_context_still_rejected_inside_production_lims(self):
        rows = [
            f"def {PAD_FN}({ACTOR}):",
            f'    raise {ERROR_NAME}("{DENIAL}")',
        ]
        self.assertIn(
            RULE_NAME,
            _rules("revenue/production-lims/example/harness.py", rows),
        )

    def test_non_product_permission_exception_still_rejected(self):
        rows = [
            "def automatic_release(self):",
            f'    raise {ERROR_NAME}("named human release required")',
        ]
        self.assertIn(RULE_NAME, _rules("host/door.py", rows))

    def test_this_module_source_does_not_trip_the_diff_scanner(self):
        path = "test_open_door_guard_production_lims_release.py"
        with open(path, encoding="utf-8") as handle:
            rows = handle.read().splitlines()
        self.assertEqual(_rules(path, rows), set())


if __name__ == "__main__":
    unittest.main()
