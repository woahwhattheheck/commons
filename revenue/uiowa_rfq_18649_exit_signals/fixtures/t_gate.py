"""FIXTURE: a proper gate. Returns 1 when it finds something."""
import sys


def main():
    problems = ["one", "two"]
    for problem in problems:
        print(f"found: {problem}")
    if problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
