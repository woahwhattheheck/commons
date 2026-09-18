from pathlib import Path


DOORS = (
    "reach.html",
    "reply.html",
    "todo.html",
    "live.html",
    "mirror.html",
    "open-door.html",
    "owner.html",
    "plug.html",
)


def test_shipped_doors_have_larger_fixed_note():
    for door in DOORS:
        text = Path(door).read_text(encoding="utf-8")
        assert text.count("Larger fixed engagements") == 1, door
        assert '<a href="./diagnostic.html">' in text, door
        assert '<a href="./commercial.html">' in text, door
