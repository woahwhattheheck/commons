from __future__ import annotations

import ast
import unittest

from comparison_source_analysis import ComparisonSafeSourceAnalyzer as SourceAnalyzer


def audit(source: str, bindings: dict[str, bool] | None = None) -> set[str]:
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef))
    analyzer = SourceAnalyzer(
        bindings=bindings or {"self.pathing": False, "self.tempo": False},
        protected_calls={"self._continue_weed"},
        protected_writes=set(),
    )
    analyzer.execute_block(method.body)
    return {finding.code for finding in analyzer.findings}


class ComparisonSemanticsTests(unittest.TestCase):
    def assert_blocks(self, condition: str) -> None:
        source = f'''\
class SpatialTempo:
    def transform(self, selected, state):
        if {condition}:
            self._continue_weed(state)
        return selected
'''
        self.assertIn("REACHABLE_PROTECTED_CALL", audit(source), condition)

    def assert_passes(self, condition: str) -> None:
        source = f'''\
class SpatialTempo:
    def transform(self, selected, state):
        if {condition}:
            self._continue_weed(state)
        return selected
'''
        self.assertEqual(set(), audit(source), condition)

    def test_distinct_truthy_literals_do_not_collapse(self) -> None:
        self.assert_blocks("1 != 2")

    def test_bound_false_is_not_none_is_true(self) -> None:
        self.assert_blocks("self.pathing is not None")

    def test_python_equality_not_type_tag_equality(self) -> None:
        self.assert_blocks("1 == True")

    def test_bound_false_equals_false(self) -> None:
        self.assert_blocks("self.pathing == False")

    def test_bound_false_not_equal_false_prunes_body(self) -> None:
        self.assert_passes("self.pathing != False")

    def test_true_chained_ordering_blocks(self) -> None:
        self.assert_blocks("0 < 1 < 2")

    def test_false_chained_ordering_prunes_body(self) -> None:
        self.assert_passes("0 < 1 > 2")

    def test_mixed_chain_uses_python_semantics(self) -> None:
        self.assert_blocks("1 == True is not None")

    def test_literal_membership(self) -> None:
        self.assert_blocks("1 in (0, 1, 2)")
        self.assert_passes("1 not in (0, 1, 2)")

    def test_non_singleton_identity_remains_unknown(self) -> None:
        # Unknown identity means both branches are explored, never a false PASS.
        self.assert_blocks("1000 is 1000")

    def test_comparison_operand_is_still_scanned(self) -> None:
        source = '''\
class SpatialTempo:
    def transform(self, selected, state):
        if self._continue_weed(state) == 1:
            return selected
        return selected
'''
        self.assertIn("REACHABLE_PROTECTED_CALL", audit(source))

    def test_original_short_circuit_contract_still_passes(self) -> None:
        source = '''\
class SpatialTempo:
    def transform(self, selected, state):
        if (self.pathing or self.tempo) and self._continue_weed(state):
            return selected
        return selected
'''
        self.assertEqual(set(), audit(source))

    def test_original_predecessor_still_blocks(self) -> None:
        source = '''\
class SpatialTempo:
    def transform(self, selected, state):
        if self._continue_weed(state):
            return selected
        if not self.pathing and not self.tempo:
            return selected
        return selected
'''
        self.assertIn("REACHABLE_PROTECTED_CALL", audit(source))


if __name__ == "__main__":
    unittest.main()
