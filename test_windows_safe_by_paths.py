#!/usr/bin/env python3
"""Windows-safe, reversible claim projection paths for rebuild_by."""
from __future__ import annotations

import os
import shutil
import tempfile

import board_ingest


BAD_WINDOWS_CHARS = set('<>:"/\\|?*')
DOS_DEVICE_NAMES = (
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", "CLOCK$"}
    | {"COM%d" % i for i in range(1, 10)}
    | {"LPT%d" % i for i in range(1, 10)}
)


def assert_windows_safe_component(filename):
    assert filename
    assert not any(ch in BAD_WINDOWS_CHARS or ord(ch) < 32 for ch in filename), filename
    assert not filename.endswith((".", " ")), filename
    stem = filename.rstrip(" .").split(".", 1)[0].upper()
    assert stem not in DOS_DEVICE_NAMES, filename


def test_by_claim_filename_is_reversible_and_windows_safe():
    safe = ("ZERO", "PLAYER_1", "A.B-C", "_LEADING")
    for claim in safe:
        filename = board_ingest.by_claim_filename(claim)
        assert filename == claim + ".html"
        assert board_ingest.claim_from_by_filename(filename) == claim
        assert_windows_safe_component(filename)

    hostile = (
        "BRANDED: DISSIDENT - SHAMEFUL",
        "ANGLE<LEFT",
        "ANGLE>RIGHT",
        'DOUBLE"QUOTE',
        "FORWARD/SLASH",
        "BACK\\SLASH",
        "PIPE|NAME",
        "QUESTION?",
        "STAR*NAME",
        "TRAILING.",
        "TRAILING ",
        "~CODEC-NAMESPACE",
        "MÉMOIRE/盒",
    ) + tuple("CONTROL%sNAME" % chr(i) for i in range(32)) + tuple(
        name for device in sorted(DOS_DEVICE_NAMES)
        for name in (device, device.lower() + ".log")
    )
    seen = set()
    for claim in hostile:
        filename = board_ingest.by_claim_filename(claim)
        assert filename.startswith("~"), (claim, filename)
        assert filename not in seen, (claim, filename)
        seen.add(filename)
        assert board_ingest.claim_from_by_filename(filename) == claim
        assert_windows_safe_component(filename)

    expected = "~QlJBTkRFRDogRElTU0lERU5UIC0gU0hBTUVGVUw.html"
    assert board_ingest.by_claim_filename("BRANDED: DISSIDENT - SHAMEFUL") == expected

    for noncanonical in ("CON.html", "TRAILING .html", "../ZERO.html", "~!.html"):
        try:
            board_ingest.claim_from_by_filename(noncanonical)
        except ValueError:
            pass
        else:
            raise AssertionError("non-canonical filename accepted: %s" % noncanonical)


def test_rebuild_by_preserves_claim_and_emits_stable_encoded_route():
    tmp = tempfile.mkdtemp(prefix="commons-windows-by-")
    saved_root, saved_by = board_ingest.ROOT, board_ingest.BY
    saved_mod_state = board_ingest.hub_pages.mod_state
    saved_badge = board_ingest.memory_board.identity_badge_html
    claim = "BRANDED: DISSIDENT - SHAMEFUL"
    filename = board_ingest.by_claim_filename(claim)
    rows = [(
        "2026-08-26T12:00:00Z",
        {
            "from": claim,
            "to": "TABLE",
            "id": "windows-safe-by-fixture",
            "ts": "2026-08-26T12:00:00Z",
        },
        "portable projection proof",
    )]
    try:
        board_ingest.ROOT = tmp
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.hub_pages.mod_state = lambda _rows: {"hidden": []}
        board_ingest.memory_board.identity_badge_html = lambda *_args, **_kwargs: ""

        first_index = board_ingest.rebuild_by(rows)
        target = os.path.join(board_ingest.BY, filename)
        invalid = os.path.join(board_ingest.BY, claim + ".html")
        assert os.path.isfile(target), target
        assert not os.path.exists(invalid), invalid
        with open(target, "rb") as handle:
            first_bytes = handle.read()
        rendered = first_bytes.decode("utf-8")
        assert "<title>%s chronological</title>" % claim in rendered
        assert "Export of posts claimed from=%s." % claim in rendered
        assert any("(./by/%s)" % filename in row for row in first_index)

        second_index = board_ingest.rebuild_by(rows)
        with open(target, "rb") as handle:
            assert handle.read() == first_bytes
        assert second_index == first_index
    finally:
        board_ingest.ROOT, board_ingest.BY = saved_root, saved_by
        board_ingest.hub_pages.mod_state = saved_mod_state
        board_ingest.memory_board.identity_badge_html = saved_badge
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    test_by_claim_filename_is_reversible_and_windows_safe()
    test_rebuild_by_preserves_claim_and_emits_stable_encoded_route()
    print("WINDOWS-SAFE BY PATHS: ALL PASS")


if __name__ == "__main__":
    main()
