"""Additive observability doors. Old tools stay. New land has no VERDICT."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def test_old_artifacts_still_there():
    assert os.path.isfile(os.path.join(HERE, "muhl_png.py"))
    assert os.path.isfile(os.path.join(HERE, "imgdiff.py"))
    assert os.path.isfile(os.path.join(HERE, "host", "muhl_copy_leftover_button.py"))
    assert os.path.isfile(os.path.join(HERE, "host", "muhl_fold_surface_add.py"))
    img = read("imgdiff.py")
    assert "NOW OPEN BOTH IMAGES AND LOOK AT THAT BOX" in img
    png = read("muhl_png.py")
    assert "if mode == 'watch':" in png
    assert "if mode == 'vdiff':" in png


def test_new_doors_exist():
    for name in (
        "look.html", "look.js", "look.css",
        "shots.html", "face.html", "face.js",
        "flipbook.html", "flipbook.js",
        "loop.html", "net159.html", "width200.js",
        "host/muhl_operator_loop.py",
        "ground/WIDTH200.md", "ground/PREDICATE_JAIL.md",
        "ground/PRTSCN.md", "ground/OBS_ADDITIVE.md",
    ):
        assert os.path.isfile(os.path.join(HERE, name)), name


def test_new_js_has_no_verdict():
    for name in ("look.js", "face.js", "flipbook.js", "width200.js"):
        text = read(name)
        assert "VERDICT" not in text, name


def test_width200_is_200():
    text = read("width200.js")
    assert re.search(r"WIDTH:\s*200", text)
    assert "STRIDE: 25" in text


def test_loop_refuses_submit():
    text = read("host/muhl_operator_loop.py")
    assert "--submit" in text
    assert "muhl_copy_leftover_button.py" in text
    assert "muhl_fold_surface_add.py" in text
    assert "VERDICT" not in text


def test_catalog_lists_look():
    hub = read("hub_pages.py")
    assert 'href="./look.html"' in hub
    assert 'href="./net159.html"' in hub
    boards = read("boards.html")
    assert 'href="./look.html"' in boards


def test_net159_is_not_a_claim_seat():
    text = read("net159.html")
    assert "not a Commons" in text or "not a from=" in text
    visual = read("visual.js")
    assert "NET 159" not in visual
