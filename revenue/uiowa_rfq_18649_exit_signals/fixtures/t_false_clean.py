"""FIXTURE: the dangerous one. Announces failure on stdout and exits 0 anyway.

A runner records this as a clean run. The problem is visible only to a human who
reads the output.
"""


def main():
    print("FAIL: 3 records could not be reconciled")
    print("ERROR: 1 locator is broken")


if __name__ == "__main__":
    main()
