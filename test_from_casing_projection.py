#!/usr/bin/env python3
"""Read-time from= casing normalization; source records remain immutable."""

from copy import deepcopy

import board_ingest


def main():
    chronological = [
        (
            "2026-08-20T17:00:00Z",
            {"from": "margin", "to": "TABLE", "id": "margin-lower"},
            "lowercase source claim",
        ),
        (
            "2026-08-20T17:01:00Z",
            {"from": "MARGIN", "to": "TABLE", "id": "margin-upper"},
            "uppercase source claim",
        ),
        (
            "2026-08-20T17:02:00Z",
            {"from": "", "to": "TABLE", "id": "blank-source"},
            "blank source claim",
        ),
    ]
    before = deepcopy(chronological)

    presence = board_ingest.presence_state(chronological)
    if [row.get("from") for row in presence] != ["MARGIN"]:
        raise AssertionError("presence projection must contain exactly one MARGIN actor")
    if presence[0].get("id") != "margin-upper":
        raise AssertionError("presence projection must retain the newest mixed-case row")

    newest_first = list(reversed(chronological))
    seen = board_ingest.last_seen(newest_first)
    if [row.get("from") for row in seen] != ["MARGIN"]:
        raise AssertionError("last-seen projection must contain exactly one MARGIN actor")
    if seen[0].get("id") != "margin-upper":
        raise AssertionError("last-seen projection must retain the newest named row")

    if chronological != before:
        raise AssertionError("read-time normalization must not rewrite source records")
    if chronological[0][1]["from"] != "margin" or chronological[2][1]["from"] != "":
        raise AssertionError("lowercase and blank source bytes must remain exact")

    print("ok   from casing projects margin/MARGIN/blank as one MARGIN actor")
    print("ok   source records remain byte-for-byte unchanged")


if __name__ == "__main__":
    main()
