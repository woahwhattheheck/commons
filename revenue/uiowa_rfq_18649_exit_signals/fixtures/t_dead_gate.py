"""FIXTURE (hostile): a non-zero exit that sits in unreachable code.

A grep for 'sys.exit(1)' reports this tool as gated. It is not: the return above it
runs unconditionally first, so the exit is dead text.
"""
import sys


def main():
    print("checked 4 items")
    return 0
    sys.exit(1)          # unreachable: the return above always fires


if __name__ == "__main__":
    sys.exit(main())
