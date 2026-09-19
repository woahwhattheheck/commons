"""FIXTURE: contract-conformant. Emits a KIT-STATUS line and exits by the contract."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contract  # noqa: E402


def main():
    findings = 2
    indeterminate = 1
    print(f"checked 9 items; {findings} need attention; {indeterminate} not assessable")
    return contract.emit("t_contract", findings=findings, indeterminate=indeterminate,
                         note="fixture run")


if __name__ == "__main__":
    sys.exit(main())
