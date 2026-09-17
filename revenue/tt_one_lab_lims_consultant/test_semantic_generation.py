from __future__ import annotations

import dis
import types
import unittest

import revenue.tt_one_lab_lims_consultant.carrier as carrier
from revenue.tt_one_lab_lims_consultant.test_carrier import complete_input


ROOTS = (
    carrier.compile_packet,
    carrier.verify_packet,
    carrier.source_manifest_digest,
    carrier.example_owner_input,
    carrier.loads_strict,
)


def _carrier_functions():
    queue = list(ROOTS)
    seen: set[int] = set()
    found: list[types.FunctionType] = []
    while queue:
        fn = queue.pop()
        if not isinstance(fn, types.FunctionType):
            continue
        if fn.__module__ != carrier.__name__:
            continue
        identity = id(fn)
        if identity in seen:
            continue
        seen.add(identity)
        found.append(fn)
        for cell in fn.__closure__ or ():
            try:
                value = cell.cell_contents
            except ValueError:
                continue
            if isinstance(value, types.FunctionType) and value.__module__ == carrier.__name__:
                queue.append(value)
    return found


def _freevar(fn: types.FunctionType, name: str):
    closure = fn.__closure__ or ()
    cells = dict(zip(fn.__code__.co_freevars, closure))
    if name not in cells:
        raise AssertionError(f"{fn.__qualname__} has no freevar {name!r}")
    return cells[name].cell_contents


class SemanticGenerationTest(unittest.TestCase):
    def test_reachable_runtime_generation_has_no_global_opcode(self):
        offenders = []
        for fn in _carrier_functions():
            for instruction in dis.get_instructions(fn):
                if instruction.opname in {"LOAD_GLOBAL", "STORE_GLOBAL", "DELETE_GLOBAL"}:
                    offenders.append(
                        (fn.__qualname__, instruction.opname, instruction.argval)
                    )
        self.assertEqual(offenders, [])

    def test_reachable_runtime_generation_captures_no_mutable_builtin_container(self):
        offenders = []
        for fn in _carrier_functions():
            for name, cell in zip(fn.__code__.co_freevars, fn.__closure__ or ()):
                try:
                    value = cell.cell_contents
                except ValueError:
                    continue
                if type(value) in {dict, list, set, bytearray}:
                    offenders.append((fn.__qualname__, name, type(value).__name__))
        self.assertEqual(offenders, [])

    def test_verifier_closes_over_the_same_compiler_generation(self):
        public_compile_impl = _freevar(carrier.compile_packet, "compile_impl")
        verify_impl = _freevar(carrier.verify_packet, "verify_impl")
        verifier_compile_impl = _freevar(verify_impl, "compile_impl")
        self.assertIs(verifier_compile_impl, public_compile_impl)

    def test_active_compiler_impl_is_not_exported_as_module_global(self):
        public_compile_impl = _freevar(carrier.compile_packet, "compile_impl")
        exported_aliases = [
            name for name, value in vars(carrier).items() if value is public_compile_impl
        ]
        self.assertEqual(exported_aliases, [])

    def test_global_namespace_poison_does_not_change_bytecode_proven_packet(self):
        owner = complete_input()
        baseline = carrier.compile_packet(owner)
        poison = {
            "type": lambda value: object,
            "dict": lambda *args, **kwargs: {"forged": True},
            "set": lambda *args, **kwargs: {"forged"},
            "all": lambda values: True,
            "sorted": lambda values: [("submission_authorized", True)],
            "ValueError": RuntimeError,
        }
        missing = object()
        original = {}
        try:
            for name, value in poison.items():
                original[name] = getattr(carrier, name, missing)
                setattr(carrier, name, value)
            self.assertEqual(carrier.compile_packet(owner), baseline)
            self.assertTrue(carrier.verify_packet(baseline, owner))
        finally:
            for name, value in original.items():
                if value is missing:
                    delattr(carrier, name)
                else:
                    setattr(carrier, name, value)


if __name__ == "__main__":
    unittest.main()
