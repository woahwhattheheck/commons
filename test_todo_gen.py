#!/usr/bin/env python3
"""Keep todo.html's offline fallback identical to canonical DIRECTIVES.md."""
import os

import todo_gen


HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    directives = open(os.path.join(HERE, "DIRECTIVES.md"), encoding="utf-8").read()
    page = open(os.path.join(HERE, "todo.html"), encoding="utf-8").read()
    projected, rows = todo_gen.project(page, directives)
    by_id = {row["n"]: row for row in rows}

    assert len(rows) >= 22, "late directives disappeared from the fallback"
    assert by_id[7]["word"] == "BUILT", by_id[7]
    assert by_id[9]["word"] == "HALF", by_id[9]
    assert by_id[10]["word"] == "HALF", by_id[10]
    assert by_id[18]["word"] == "MEASURED", by_id[18]
    assert todo_gen.status_word("NOT BUILT") == "NOT BUILT"
    assert todo_gen.status_word("UNBUILT") == "OPEN"
    assert todo_gen.status_word("OPEN. Not LANDED.") == "OPEN"
    assert projected == page, "todo.html fallback drifted; run python3 todo_gen.py"

    for broken_page, broken_directives in (
        ("no rows", directives),
        (page.replace("</tbody>", ""), directives),
        (page, ""),
    ):
        try:
            todo_gen.project(broken_page, broken_directives)
        except ValueError:
            pass
        else:
            raise AssertionError("generator accepted a missing input boundary")
    print("TODO GENERATOR TEST: %d canonical rows, fallback exact" % len(rows))


if __name__ == "__main__":
    main()
