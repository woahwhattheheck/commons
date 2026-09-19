"""FIXTURE: exit value that cannot be resolved statically -> INDETERMINATE.

Not assumed to be a gate, and not assumed to be report-only.
"""
import os
import sys


def main():
    return os.environ.get("EXIT_WITH", "0")


if __name__ == "__main__":
    sys.exit(int(main()))
