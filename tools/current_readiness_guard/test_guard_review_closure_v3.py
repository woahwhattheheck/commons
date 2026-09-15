from __future__ import annotations

import unittest

from .guard import analyze_source


class ReviewClosureV3Tests(unittest.TestCase):
    def rules(self, source: str) -> list[str]:
        return [finding.rule for finding in analyze_source(source, path="revenue/x.py")]

    def test_local_composed_readiness_strings_fail_closed(self):
        samples = (
            '''
def evaluate(packet):
    state = "PRIME_" + "READY"
    return state
''',
            '''
def evaluate(packet):
    prefix = "PRIME_"
    state = f"{prefix}READY"
    return state
''',
        )
        for source in samples:
            with self.subTest(source=source):
                self.assertIn("CRG003", self.rules(source))

    def test_public_method_boolean_and_computed_string_surfaces_fail_closed(self):
        samples = (
            '''
class Gate:
    def verify_current(self, packet):
        return True
''',
            '''
class Gate:
    def is_ready(self, packet):
        return packet["state"] == "READY"
''',
            '''
class Gate:
    def evaluate(self, packet):
        return "PRIME_" + "READY"
''',
        )
        for source in samples:
            with self.subTest(source=source):
                self.assertIn("CRG003", self.rules(source))

        controlled = '''
class Gate:
    def is_ready(self, packet, authority_root):
        return bool(authority_root)
'''
        self.assertNotIn("CRG003", self.rules(controlled))

    def test_local_validator_alias_must_consume_authority(self):
        ignored = '''
def validate_authority(packet, authority_root):
    return packet["verified"]

def evaluate(packet, authority_root):
    verify = validate_authority
    if verify(packet, authority_root):
        return "PRIME_READY"
    return "HOLD"
'''
        consumed = '''
def validate_authority(packet, authority_root):
    return bool(authority_root)

def evaluate(packet, authority_root):
    verify = validate_authority
    if verify(packet, authority_root):
        return "PRIME_READY"
    return "HOLD"
'''
        self.assertIn("CRG003", self.rules(ignored))
        self.assertNotIn("CRG003", self.rules(consumed))

    def test_module_validator_alias_must_consume_authority(self):
        ignored = '''
def validate_authority(packet, authority_root):
    return packet["verified"]

verify = validate_authority

def evaluate(packet, authority_root):
    if verify(packet, authority_root):
        return "PRIME_READY"
    return "HOLD"
'''
        self.assertIn("CRG003", self.rules(ignored))

    def test_method_validator_alias_must_consume_authority(self):
        ignored = '''
class Gate:
    def validate_authority(self, packet, authority_root):
        return packet["verified"]

    def evaluate(self, packet, authority_root):
        verify = self.validate_authority
        if verify(packet, authority_root):
            return "PRIME_READY"
        return "HOLD"
'''
        consumed = '''
class Gate:
    def validate_authority(self, packet, authority_root):
        return bool(authority_root)

    def evaluate(self, packet, authority_root):
        verify = self.validate_authority
        if verify(packet, authority_root):
            return "PRIME_READY"
        return "HOLD"
'''
        self.assertIn("CRG003", self.rules(ignored))
        self.assertNotIn("CRG003", self.rules(consumed))


if __name__ == "__main__":
    unittest.main()
