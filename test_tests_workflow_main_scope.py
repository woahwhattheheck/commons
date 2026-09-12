#!/usr/bin/env python3
"""Engine battery stays on main; frozen titan PRs keep dedicated gates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("ok  ", name)
        return
    FAILED.append(name)
    print("FAIL", name, detail)


def main():
    check(
        "push already lists main",
        "branches:\n      - main" in TEXT,
    )
    check(
        "battery job scoped to main pull requests",
        "github.base_ref == 'main'" in TEXT
        or 'github.base_ref == "main"' in TEXT,
        "job if or equivalent main-base predicate missing",
    )
    check(
        "non-main pull requests still bind a success job",
        "github.base_ref != 'main'" in TEXT
        or 'github.base_ref != "main"' in TEXT,
        "companion success path missing",
    )
    check(
        "battery still discovers root test_*.py",
        "find . -maxdepth 1 -type f -name 'test_*.py'" in TEXT,
    )
    check(
        "battery still discovers infra tests",
        "find infra -type f -name 'test_*.py'" in TEXT,
    )
    check(
        "one failure still fails the run",
        "the whole battery, one failure fails the run" in TEXT,
    )
    check(
        "vanished-test hole remains",
        "a test file that vanished is a hole" in TEXT,
    )
    check(
        "scope is not an auth or admission lock",
        "login" not in TEXT.lower()
        and "allowlist" not in TEXT.lower()
        and "approval" not in TEXT.lower(),
    )
    if FAILED:
        raise SystemExit("FAILED: " + ", ".join(FAILED))
    print("TESTS_WORKFLOW_MAIN_SCOPE_OK", 8)


if __name__ == "__main__":
    main()
