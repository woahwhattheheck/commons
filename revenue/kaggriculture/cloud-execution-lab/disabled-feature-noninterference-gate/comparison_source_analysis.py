"""Comparison-sound extension for the disabled-feature source analyzer.

The predecessor analyzer projected operands to truth values before evaluating
``==``, ``!=``, ``is`` and ``is not``. That can prune reachable branches, for
example by reducing both ``1`` and ``2`` to ``True``. This extension preserves
bounded concrete literal values and falls back to both truth outcomes whenever
Python semantics cannot be proved exactly.
"""
from __future__ import annotations

import ast
import itertools
import operator

from gate_common import _attribute_path
from source_analysis import SourceAnalyzer

_Concrete = tuple[str, object]
_UNKNOWN_TRUTH = frozenset({True, False})
_SINGLETON_KINDS = frozenset({"none", "bool", "ellipsis"})
_MAX_COMPARISON_COMBINATIONS = 128


class ComparisonSafeSourceAnalyzer(SourceAnalyzer):
    """SourceAnalyzer with value-preserving, fail-closed comparisons."""

    @staticmethod
    def _tag_constant(value: object) -> _Concrete | None:
        # bool must precede int because bool is an int subclass.
        if value is None:
            return ("none", None)
        if value is Ellipsis:
            return ("ellipsis", Ellipsis)
        if isinstance(value, bool):
            return ("bool", value)
        if isinstance(value, int):
            return ("int", value)
        if isinstance(value, float):
            return ("float", value)
        if isinstance(value, complex):
            return ("complex", value)
        if isinstance(value, str):
            return ("str", value)
        if isinstance(value, bytes):
            return ("bytes", value)
        return None

    def _concrete_values(self, node: ast.AST) -> tuple[_Concrete, ...] | None:
        """Return bounded concrete alternatives without executing effects."""
        if isinstance(node, ast.Constant):
            tagged = self._tag_constant(node.value)
            return None if tagged is None else (tagged,)

        path = _attribute_path(node)
        if path in self.bindings:
            return (("bool", self.bindings[path]),)

        if isinstance(node, ast.UnaryOp):
            operand = self._concrete_values(node.operand)
            if operand is None:
                return None
            results: list[_Concrete] = []
            for _, value in operand:
                try:
                    if isinstance(node.op, ast.Not):
                        result: object = not value
                    elif isinstance(node.op, ast.UAdd):
                        result = operator.pos(value)
                    elif isinstance(node.op, ast.USub):
                        result = operator.neg(value)
                    elif isinstance(node.op, ast.Invert):
                        result = operator.invert(value)
                    else:
                        return None
                except (TypeError, ValueError, OverflowError):
                    return None
                tagged = self._tag_constant(result)
                if tagged is None:
                    return None
                if tagged not in results:
                    results.append(tagged)
            return tuple(results)

        if isinstance(node, ast.IfExp):
            test = self.truth(node.test)
            results: list[_Concrete] = []
            branches: list[ast.AST] = []
            if True in test:
                branches.append(node.body)
            if False in test:
                branches.append(node.orelse)
            for branch in branches:
                values = self._concrete_values(branch)
                if values is None:
                    return None
                for value in values:
                    if value not in results:
                        results.append(value)
            return tuple(results)

        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            element_values: list[tuple[_Concrete, ...]] = []
            combinations = 1
            for element in node.elts:
                values = self._concrete_values(element)
                if values is None:
                    return None
                element_values.append(values)
                combinations *= len(values)
                if combinations > _MAX_COMPARISON_COMBINATIONS:
                    return None
            results: list[_Concrete] = []
            for choice in itertools.product(*element_values):
                raw = [item[1] for item in choice]
                try:
                    if isinstance(node, ast.Tuple):
                        container: object = tuple(raw)
                        kind = "tuple"
                    elif isinstance(node, ast.List):
                        container = tuple(raw)  # immutable analysis surrogate
                        kind = "list"
                    else:
                        container = frozenset(raw)
                        kind = "set"
                except TypeError:
                    return None
                tagged = (kind, container)
                if tagged not in results:
                    results.append(tagged)
            return tuple(results)

        return None

    @staticmethod
    def _raw_value(value: _Concrete) -> object:
        kind, raw = value
        if kind == "list":
            return list(raw)  # type: ignore[arg-type]
        if kind == "set":
            return set(raw)  # type: ignore[arg-type]
        return raw

    def _compare_pair(self, left: _Concrete, op: ast.cmpop, right: _Concrete) -> bool | None:
        left_kind, _ = left
        right_kind, _ = right
        left_value = self._raw_value(left)
        right_value = self._raw_value(right)

        # Identity is exact for language singletons. If exactly one side is a
        # singleton, identity is definitely false. Two non-singletons are left
        # unknown because Python may intern them.
        if isinstance(op, (ast.Is, ast.IsNot)):
            if left_kind in _SINGLETON_KINDS or right_kind in _SINGLETON_KINDS:
                identical = (
                    left_kind in _SINGLETON_KINDS
                    and right_kind in _SINGLETON_KINDS
                    and left_kind == right_kind
                    and left_value is right_value
                )
                return identical if isinstance(op, ast.Is) else not identical
            return None

        operations = (
            (ast.Eq, operator.eq),
            (ast.NotEq, operator.ne),
            (ast.Lt, operator.lt),
            (ast.LtE, operator.le),
            (ast.Gt, operator.gt),
            (ast.GtE, operator.ge),
            (ast.In, lambda a, b: a in b),
            (ast.NotIn, lambda a, b: a not in b),
        )
        for op_type, function in operations:
            if isinstance(op, op_type):
                try:
                    return bool(function(left_value, right_value))
                except (TypeError, ValueError, OverflowError):
                    return None
        return None

    def _comparison_truth(self, node: ast.Compare) -> frozenset[bool]:
        operands = [node.left, *node.comparators]

        # Scan every operand for protected effects. Chained comparisons may
        # short-circuit at runtime; scanning later operands over-approximates and
        # can only produce a conservative BLOCK, never an unsafe PASS.
        for operand in operands:
            self.truth(operand)

        alternatives: list[tuple[_Concrete, ...]] = []
        combinations = 1
        for operand in operands:
            values = self._concrete_values(operand)
            if not values:
                return _UNKNOWN_TRUTH
            alternatives.append(values)
            combinations *= len(values)
            if combinations > _MAX_COMPARISON_COMBINATIONS:
                return _UNKNOWN_TRUTH

        outcomes: set[bool] = set()
        for values in itertools.product(*alternatives):
            for index, op in enumerate(node.ops):
                pair = self._compare_pair(values[index], op, values[index + 1])
                if pair is None:
                    outcomes.update((True, False))
                    break
                if not pair:
                    outcomes.add(False)
                    break
            else:
                outcomes.add(True)
            if outcomes == {True, False}:
                break
        return frozenset(outcomes) if outcomes else _UNKNOWN_TRUTH

    def truth(self, node: ast.AST) -> frozenset[bool]:
        if isinstance(node, ast.Compare):
            return self._comparison_truth(node)
        return super().truth(node)
