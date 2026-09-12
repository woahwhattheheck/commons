import unittest

import open_door_guard as guard


RULE_NAME = "".join(("v", "erb", "-", "e", "num"))


def _diff(path, source):
    rows = source.splitlines()
    additions = "\n".join("+" + row for row in rows)
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{len(rows)} @@\n"
        f"{additions}\n"
    )


class OpenDoorArgparseChoicesTests(unittest.TestCase):
    def _rules(self, path, source):
        return {item.rule for item in guard.scan_diff(_diff(path, source))}

    def test_parser_behavior_keyword_does_not_form_structural_rule(self):
        behavior_kw = "act" + "ion"
        selection_kw = "cho" + "ices"
        source = (
            f'parser.add_argument("--optimise", {behavior_kw}="store_true")\n'
            "parser.add_argument(\n"
            '    "--optimizer-distance-units",\n'
            f'    {selection_kw}=("physical",),\n'
            ")"
        )
        self.assertNotIn(RULE_NAME, self._rules("adapter.py", source))

    def test_real_schema_still_rejected(self):
        field = "act" + "ion"
        structural_kw = "en" + "um"
        source = f'{{"{field}": {{"{structural_kw}": ["POST", "DELETE"]}}}}'
        self.assertIn(RULE_NAME, self._rules("schema.json", source))

    def test_named_cli_field_still_rejected(self):
        option = "--" + "action"
        selection_kw = "cho" + "ices"
        source = f'parser.add_argument("{option}", {selection_kw}=("POST", "DELETE"))'
        self.assertIn(RULE_NAME, self._rules("cli.py", source))


if __name__ == "__main__":
    unittest.main()
