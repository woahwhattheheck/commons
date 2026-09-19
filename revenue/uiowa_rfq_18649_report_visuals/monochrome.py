"""Convert a rendered SVG to true monochrome, so the claim can be tested.

UIOWA-126 asks that readers distinguish these states "in color, monochrome, and
exported output". A promise that a figure "would still work in black and white"
is untestable. So the colour is actually removed: every hex value in the
document is replaced with its WCAG luminance-preserving grey, producing a real
artifact a reviewer can open, print, and compare.

This is the same transform a monochrome printer or a fully colour-blind reader
applies, so `figure.mono.svg` is not an approximation of the worst case -- it is
the worst case, on disk.

What survives the conversion is exactly what this package treats as
load-bearing: shape, texture, border style and the written label. What does not
survive is hue. That is the point.

Python 3 standard library only.
"""

from __future__ import annotations

import re

import contrast

# Matches #rgb and #rrggbb inside attribute values.
_HEX = re.compile(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b')


def to_monochrome(svg_text: str) -> str:
    """Replace every colour in an SVG document with its grayscale equivalent."""
    def swap(match: re.Match) -> str:
        try:
            return contrast.to_grayscale(match.group(0))
        except contrast.ColorError:  # pragma: no cover - regex already constrains this
            return match.group(0)
    return _HEX.sub(swap, svg_text)


def colours_in(svg_text: str) -> list[str]:
    """Every distinct colour a document uses, uppercased and normalised."""
    seen: list[str] = []
    for raw in _HEX.findall(svg_text):
        value = contrast.to_hex(contrast.parse_hex(raw))
        if value not in seen:
            seen.append(value)
    return seen


def is_monochrome(svg_text: str) -> bool:
    """True when no colour in the document carries any hue at all."""
    for value in colours_in(svg_text):
        r, g, b = contrast.parse_hex(value)
        if not (r == g == b):
            return False
    return True


def separation_report(fills: dict) -> list[tuple[str, str, float]]:
    """Pairwise monochrome separation for a set of named fills.

    Returned sorted worst-first, because the interesting number is always the
    closest pair, not the average.
    """
    names = list(fills)
    rows: list[tuple[str, str, float]] = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            rows.append((a, b, contrast.grayscale_contrast(fills[a], fills[b])))
    rows.sort(key=lambda row: row[2])
    return rows
