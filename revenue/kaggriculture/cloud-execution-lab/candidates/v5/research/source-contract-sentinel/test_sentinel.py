#!/usr/bin/env python3
from pathlib import Path
import tempfile

from sentinel import (
    RULE_EXACT_ROW_LEN3,
    RULE_PUBLIC_OBS_COERCION,
    RULE_RAW_OPCODE_INDEX,
    RULE_TRUTHY_CONFIG_COERCION,
    scan_paths,
    scan_source,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def rules(source):
    return [finding.rule for finding in scan_source(source)]


def main():
    check(RULE_RAW_OPCODE_INDEX in rules("def f(order):\n    return order[0]\n"), "raw opcode")
    check(RULE_EXACT_ROW_LEN3 in rules("def f(order):\n    return len(order) == 3\n"), "len3")
    check(
        RULE_PUBLIC_OBS_COERCION in rules(
            "def f(observation):\n    return int(observation['step'])\n"
        ),
        "observation subscript coercion",
    )
    check(
        RULE_PUBLIC_OBS_COERCION in rules(
            "def f(obs):\n    return int(obs.get('player', 0))\n"
        ),
        "observation get coercion",
    )
    check(
        RULE_TRUTHY_CONFIG_COERCION in rules(
            "def f(feature_data):\n    return bool(feature_data['town_procurement'])\n"
        ),
        "truthy config coercion",
    )

    guarded = """\
def f(order):
    if not isinstance(order, list) or not order:
        return None
    # contract-sentinel: ignore=RAW_OPCODE_INDEX
    return order[0]
"""
    check(RULE_RAW_OPCODE_INDEX not in rules(guarded), "single suppression")

    multi = """\
def f(order):
    # contract-sentinel: ignore=EXACT_ROW_LEN3
    if len(order) == 3:
        # contract-sentinel: ignore=RAW_OPCODE_INDEX
        return order[0]
"""
    check(rules(multi) == [], "multiple suppressions")

    safe = """\
def f(observation, configuration):
    step = observation['step']
    if isinstance(step, bool) or not isinstance(step, int):
        return None
    enabled = configuration['feature']
    if type(enabled) is not bool:
        return None
    return step, enabled
"""
    check(rules(safe) == [], "exact-type safe fixture")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "b.py").write_text("def f(order):\n    return order[0]\n", encoding="utf-8")
        (root / "a.py").write_text("def f(obs):\n    return int(obs['day'])\n", encoding="utf-8")
        findings = scan_paths([root], display_root=root)
        check(
            [(f.path, f.rule) for f in findings] == [
                ("a.py", RULE_PUBLIC_OBS_COERCION),
                ("b.py", RULE_RAW_OPCODE_INDEX),
            ],
            "deterministic path/rule ordering",
        )

    print("source-contract-sentinel: 9/9 OK")


if __name__ == "__main__":
    main()
