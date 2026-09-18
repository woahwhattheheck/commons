"""Additive compression doors. Old tools stay. New land has no VERDICT."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def test_old_compress_artifacts_still_there():
    assert os.path.isfile(os.path.join(HERE, "foldpack.py"))
    assert os.path.isfile(os.path.join(HERE, "stackpack.py"))
    assert os.path.isfile(os.path.join(HERE, "evolve.py"))
    ev = read("evolve.py")
    assert "NOTHING IS EVER PERMANENTLY PRUNED" in ev
    assert "TRANSPOSE" in ev
    fp = read("foldpack.py")
    assert "adjacent" in fp
    assert "TRUE bit width" in fp or "true bit width" in fp


def test_new_compress_doors_exist():
    for name in (
        "compress.html", "rooms.html", "glyphs.html", "glyphs.js",
        "program.html", "program.js", "accordion.html", "accordion.js",
        "breath.html", "breath.js", "stringmail.html", "stringmail.js",
        "foldbook.html", "foldbook.js", "cweather.html", "cweather.js",
        "pack.js", "compress.json", "compress_measured.json",
        "host/muhl_compress_doors.py",
        "ground/COMPRESS_DOORS.md", "ground/TWO_ROOMS.md",
        "ground/ACCORDION.md", "ground/BREATH.md",
    ):
        assert os.path.isfile(os.path.join(HERE, name)), name


def test_new_js_has_no_verdict():
    for name in (
        "pack.js", "glyphs.js", "program.js", "accordion.js",
        "breath.js", "stringmail.js", "foldbook.js", "cweather.js",
    ):
        text = read(name)
        assert "VERDICT" not in text, name


def test_program_is_the_product():
    text = read("program.html") + read("pack.js")
    for op in ("TRANSPOSE", "REV_COLS", "XOR_COL", "ROT4"):
        assert op in text
    assert "do not hunt" in read("program.html").lower() or "Do not hunt" in read("program.html")


def test_two_rooms_not_one_scoreboard():
    text = read("rooms.html")
    assert "ARCHIVE" in text
    assert "COMPUTER" in text
    assert "SEED0" in text
    assert "8,192" in text or "8192" in text


def test_host_script_refuses_go():
    text = read("host/muhl_compress_doors.py")
    assert "--go" in text
    assert "foldpack.py" in text
    assert "VERDICT" not in text


def test_catalog_lists_compress():
    hub = read("hub_pages.py")
    assert 'href="./compress.html"' in hub
    assert 'href="./cweather.html"' in hub
    boards = read("boards.html")
    assert 'href="./compress.html"' in boards
    assert 'href="./look.html"' in boards


def test_published_computers_in_repo():
    dist = os.path.join(HERE, "muhl", "containers", "MUHLNICKEL_DISTRO")
    assert os.path.isfile(os.path.join(dist, "SEED0.mno"))
    assert os.path.isfile(os.path.join(dist, "SEED0_GERM.mno"))
    assert os.path.isfile(os.path.join(dist, "muhlnickel.mno"))


def test_loop_has_program_step():
    text = read("loop.html")
    assert "program.html" in text
    assert re.search(r"5 · program", text)
