"""Binding-aware conservative Python control-flow analysis."""
from __future__ import annotations

import ast
from typing import Iterable, Mapping, Sequence

from gate_common import Finding, _attribute_path, _contains_direct_reference, _node_location

class SourceAnalyzer:
    """Conservative path explorer with binding-aware boolean short-circuiting."""

    def __init__(
        self,
        *,
        bindings: Mapping[str, bool],
        protected_calls: set[str],
        protected_writes: set[str],
    ) -> None:
        self.bindings = dict(bindings)
        self.protected_calls = set(protected_calls)
        self.protected_writes = set(protected_writes)
        self.findings: set[Finding] = set()

    def add(
        self,
        node: ast.AST,
        *,
        code: str,
        kind: str,
        target: str,
        detail: str,
    ) -> None:
        line, column = _node_location(node)
        self.findings.add(Finding(code, line, column, kind, target, detail))

    def truth(self, node: ast.AST) -> frozenset[bool]:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return frozenset({node.value})
            if node.value is None:
                return frozenset({False})
            if isinstance(node.value, (int, float, str, bytes)):
                return frozenset({bool(node.value)})
            return frozenset({True, False})

        path = _attribute_path(node)
        if path in self.bindings:
            return frozenset({self.bindings[path]})

        if isinstance(node, ast.Name):
            return frozenset({True, False})

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return frozenset(not value for value in self.truth(node.operand))

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                possible = frozenset({True})
                for value in node.values:
                    if True not in possible:
                        break
                    rhs = self.truth(value)
                    merged: set[bool] = set()
                    if False in possible:
                        merged.add(False)
                    if True in possible:
                        merged.update(rhs)
                    possible = frozenset(merged)
                return possible
            if isinstance(node.op, ast.Or):
                possible = frozenset({False})
                for value in node.values:
                    if False not in possible:
                        break
                    rhs = self.truth(value)
                    merged = set()
                    if True in possible:
                        merged.add(True)
                    if False in possible:
                        merged.update(rhs)
                    possible = frozenset(merged)
                return possible

        if isinstance(node, ast.IfExp):
            test = self.truth(node.test)
            possible: set[bool] = set()
            if True in test:
                possible.update(self.truth(node.body))
            if False in test:
                possible.update(self.truth(node.orelse))
            return frozenset(possible)

        if isinstance(node, ast.Compare):
            values: list[frozenset[bool]] = [self.scalar_bool(node.left)]
            values.extend(self.scalar_bool(comparator) for comparator in node.comparators)
            if all(len(item) == 1 for item in values) and all(
                isinstance(op, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)) for op in node.ops
            ):
                concrete = [next(iter(item)) for item in values]
                outcome = True
                for index, op in enumerate(node.ops):
                    left, right = concrete[index], concrete[index + 1]
                    if isinstance(op, (ast.Eq, ast.Is)):
                        outcome = outcome and (left == right)
                    else:
                        outcome = outcome and (left != right)
                return frozenset({outcome})
            return frozenset({True, False})

        if isinstance(node, ast.Call):
            # Python evaluates callable, positional arguments, then keywords.
            self._scan_callable_expression(node.func)
            for arg in node.args:
                self.truth(arg)
                ref = _contains_direct_reference(arg, self.protected_calls)
                if ref:
                    self.add(
                        arg,
                        code="PROTECTED_CALLABLE_ESCAPE",
                        kind="call",
                        target=ref,
                        detail="protected callable escapes as an argument",
                    )
            for keyword in node.keywords:
                self.truth(keyword.value)
                ref = _contains_direct_reference(keyword.value, self.protected_calls)
                if ref:
                    self.add(
                        keyword.value,
                        code="PROTECTED_CALLABLE_ESCAPE",
                        kind="call",
                        target=ref,
                        detail="protected callable escapes as a keyword argument",
                    )
            target = _attribute_path(node.func)
            if target in self.protected_calls:
                self.add(
                    node,
                    code="REACHABLE_PROTECTED_CALL",
                    kind="call",
                    target=target or "<dynamic>",
                    detail="protected call is reachable under disabled bindings",
                )
            elif self._looks_dynamic_protected_call(node):
                self.add(
                    node,
                    code="DYNAMIC_PROTECTED_CALL",
                    kind="call",
                    target="<dynamic>",
                    detail="dynamic call may resolve to a protected callable",
                )
            return frozenset({True, False})

        if isinstance(node, ast.NamedExpr):
            possible = self.truth(node.value)
            self._scan_target(node.target, assignment_value=node.value)
            return possible

        if isinstance(node, ast.Lambda):
            # The body is not executed when the lambda is created. A protected
            # reference still escapes if the lambda closes over it dynamically.
            ref = _contains_direct_reference(node.body, self.protected_calls)
            if ref:
                self.add(
                    node,
                    code="PROTECTED_CALLABLE_ALIAS",
                    kind="call",
                    target=ref,
                    detail="protected callable is hidden behind a reachable lambda",
                )
            return frozenset({True})

        # Evaluate children conservatively in source order. This deliberately
        # over-approximates truth while still respecting BoolOp/IfExp above.
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self.truth(child)
        return frozenset({True, False})

    def scalar_bool(self, node: ast.AST) -> frozenset[bool]:
        return self.truth(node)

    def _scan_callable_expression(self, node: ast.AST) -> None:
        if isinstance(node, ast.Attribute):
            # Evaluating an attribute is not a call. Its target is handled once
            # the enclosing ast.Call has evaluated all arguments.
            self.truth(node.value)
            return
        if isinstance(node, ast.Name):
            return
        self.truth(node)

    def _looks_dynamic_protected_call(self, node: ast.Call) -> bool:
        protected_leafs = {target.rsplit(".", 1)[-1] for target in self.protected_calls}
        if not protected_leafs:
            return False
        func_path = _attribute_path(node.func)
        if func_path in {"getattr", "builtins.getattr"} and len(node.args) >= 2:
            name = node.args[1]
            return isinstance(name, ast.Constant) and name.value in protected_leafs
        if isinstance(node.func, ast.Call):
            for child in ast.walk(node.func):
                if isinstance(child, ast.Constant) and child.value in protected_leafs:
                    return True
        return False

    def _scan_target(self, target: ast.AST, assignment_value: ast.AST | None = None) -> None:
        path = _attribute_path(target)
        if path in self.protected_writes:
            self.add(
                target,
                code="REACHABLE_PROTECTED_WRITE",
                kind="write",
                target=path or "<dynamic>",
                detail="protected write is reachable under disabled bindings",
            )
        if path in self.bindings:
            self.add(
                target,
                code="DISABLED_BINDING_MUTATION",
                kind="write",
                target=path or "<dynamic>",
                detail="source mutates a binding whose disabled value is contractual",
            )
        if assignment_value is not None:
            ref = _contains_direct_reference(assignment_value, self.protected_calls)
            if ref:
                self.add(
                    assignment_value,
                    code="PROTECTED_CALLABLE_ALIAS",
                    kind="call",
                    target=ref,
                    detail="protected callable is assigned or aliased on a reachable path",
                )
        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._scan_target(element, assignment_value=assignment_value)
        elif isinstance(target, ast.Subscript):
            self.truth(target.value)
            self.truth(target.slice)

    def execute_block(self, statements: Sequence[ast.stmt], alive: bool = True) -> bool:
        current = alive
        for statement in statements:
            if not current:
                break
            current = self.execute(statement)
        return current

    def execute(self, statement: ast.stmt) -> bool:
        if isinstance(statement, ast.Expr):
            self.truth(statement.value)
            return True

        if isinstance(statement, ast.Return):
            if statement.value is not None:
                self.truth(statement.value)
            return False

        if isinstance(statement, ast.Raise):
            if statement.exc is not None:
                self.truth(statement.exc)
            if statement.cause is not None:
                self.truth(statement.cause)
            return False

        if isinstance(statement, ast.If):
            possibilities = self.truth(statement.test)
            body_alive = False
            else_alive = False
            if True in possibilities:
                body_alive = self.execute_block(statement.body)
            if False in possibilities:
                else_alive = self.execute_block(statement.orelse) if statement.orelse else True
            return body_alive or else_alive

        if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if isinstance(statement, ast.Assign):
                self.truth(statement.value)
                for target in statement.targets:
                    self._scan_target(target, assignment_value=statement.value)
            elif isinstance(statement, ast.AnnAssign):
                if statement.value is not None:
                    self.truth(statement.value)
                self._scan_target(statement.target, assignment_value=statement.value)
            else:
                self.truth(statement.target)
                self.truth(statement.value)
                self._scan_target(statement.target, assignment_value=statement.value)
            return True

        if isinstance(statement, ast.Delete):
            for target in statement.targets:
                self._scan_target(target)
            return True

        if isinstance(statement, ast.While):
            possibilities = self.truth(statement.test)
            if True in possibilities:
                self.execute_block(statement.body)
            if False in possibilities and statement.orelse:
                self.execute_block(statement.orelse)
            # Conservatively retain fallthrough; this cannot create a false PASS.
            return True

        if isinstance(statement, (ast.For, ast.AsyncFor)):
            self.truth(statement.iter)
            self._scan_target(statement.target)
            self.execute_block(statement.body)
            self.execute_block(statement.orelse)
            return True

        if isinstance(statement, (ast.With, ast.AsyncWith)):
            for item in statement.items:
                self.truth(item.context_expr)
                if item.optional_vars is not None:
                    self._scan_target(item.optional_vars)
            return self.execute_block(statement.body)

        if isinstance(statement, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            body_alive = self.execute_block(statement.body)
            handler_alive = False
            for handler in statement.handlers:
                if handler.type is not None:
                    self.truth(handler.type)
                handler_alive = self.execute_block(handler.body) or handler_alive
            else_alive = self.execute_block(statement.orelse) if body_alive else False
            before_finally_alive = body_alive or handler_alive or else_alive
            if statement.finalbody:
                protected = self._syntactic_protected_effect(statement.finalbody)
                if protected:
                    node, kind, target = protected
                    self.add(
                        node,
                        code="PROTECTED_EFFECT_IN_FINALLY",
                        kind=kind,
                        target=target,
                        detail="protected effect occurs in reachable finally control flow",
                    )
                final_alive = self.execute_block(statement.finalbody)
                return before_finally_alive and final_alive
            return before_finally_alive

        if isinstance(statement, ast.Match):
            self.truth(statement.subject)
            alive = False
            for case in statement.cases:
                if case.guard is not None:
                    self.truth(case.guard)
                alive = self.execute_block(case.body) or alive
            return alive or True  # unmatched subject remains possible

        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in statement.decorator_list:
                self.truth(decorator)
            for default in list(statement.args.defaults) + [
                item for item in statement.args.kw_defaults if item is not None
            ]:
                self.truth(default)
            return True

        if isinstance(statement, ast.ClassDef):
            for decorator in statement.decorator_list:
                self.truth(decorator)
            for base in statement.bases:
                self.truth(base)
            for keyword in statement.keywords:
                self.truth(keyword.value)
            return True

        if isinstance(statement, ast.Assert):
            self.truth(statement.test)
            if statement.msg is not None:
                self.truth(statement.msg)
            return True

        if isinstance(
            statement,
            (ast.Pass, ast.Break, ast.Continue, ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal),
        ):
            return True

        protected = self._syntactic_protected_effect([statement])
        if protected:
            node, kind, target = protected
            self.add(
                node,
                code="UNSUPPORTED_CONTROL_FLOW_WITH_PROTECTED_EFFECT",
                kind=kind,
                target=target,
                detail=f"unsupported reachable syntax {type(statement).__name__} contains a protected effect",
            )
        else:
            for child in ast.iter_child_nodes(statement):
                if isinstance(child, ast.expr):
                    self.truth(child)
        return True

    def _syntactic_protected_effect(
        self, statements: Sequence[ast.stmt]
    ) -> tuple[ast.AST, str, str] | None:
        for statement in statements:
            for node in ast.walk(statement):
                if isinstance(node, ast.Call):
                    path = _attribute_path(node.func)
                    if path in self.protected_calls:
                        return node, "call", path or "<dynamic>"
                if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                    targets: Iterable[ast.AST]
                    if isinstance(node, ast.Assign):
                        targets = node.targets
                    else:
                        targets = (node.target,)
                    for target_node in targets:
                        path = _attribute_path(target_node)
                        if path in self.protected_writes:
                            return target_node, "write", path or "<dynamic>"
        return None


