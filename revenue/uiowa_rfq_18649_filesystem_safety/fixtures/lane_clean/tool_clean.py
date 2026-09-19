"""SYNTHETIC FIXTURE. Expected classification: CLEAN."""
import os


def write_report(output_dir, name, text):
    root = os.path.realpath(output_dir)
    target = os.path.realpath(os.path.join(root, name))
    if not target.startswith(root + os.sep):
        raise ValueError("outside output dir")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(text)
    return target


def read_input(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()
