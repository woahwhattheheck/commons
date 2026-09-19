"""FIXTURE: non-zero only via an uncaught exception. A crash is not a signal."""


def main():
    data = {"a": 1}
    if "b" not in data:
        raise KeyError("b missing from input")
    print("ok")


if __name__ == "__main__":
    main()
