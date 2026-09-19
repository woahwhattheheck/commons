"""The four reusable report figures.

  matrix_figure()          twelve-cell assessment matrix (groups x areas)
  cross_group_figure()     cross-group comparison, off-scale lane detached
  evidence_coverage_figure()  how much evidence sits behind each group
  roadmap_figure()         phased roadmap, 0-90 / 90-180 / 180+

Every figure follows the same three rules:
  1. Redundant encoding -- colour + shape + texture + written label.
  2. Not-a-rating states are drawn with their own vocabulary and, where there
     is a scale, are physically separated from it by a rule so they cannot be
     read as "the bottom of the scale".
  3. The <desc> is generated from the same data that drew the picture, by
     alt_text.py, so the text alternative cannot drift out of sync.

Python 3 standard library only.
"""

from __future__ import annotations

import alt_text
import palette
import svg

FONT_TITLE = 17
FONT_SUB = 12
FONT_BODY = 11.5
FONT_SMALL = 10.5
MARGIN = 24


def _theme(theme_name: str) -> dict:
    try:
        return palette.THEMES[theme_name]
    except KeyError:
        raise KeyError(
            f"unknown theme {theme_name!r}; known: {', '.join(palette.THEMES)}"
        ) from None


def _header(fig: svg.Figure, th: dict, title: str, subtitle: str, x: int, y: int) -> int:
    fig.add(svg.text(x, y, title, size=FONT_TITLE, fill=th["ink"], weight="bold"))
    y += 18
    if subtitle:
        fig.add(svg.text(x, y, subtitle, size=FONT_SUB, fill=th["muted"]))
        y += 16
    return y


def _band_paint(fig: svg.Figure, th: dict, b: palette.Band) -> str:
    return fig.texture_fill(b.key, b.texture, b.fill, b.texture_ink, th["hatch_weight"])


def _band_swatch(fig: svg.Figure, th: dict, b: palette.Band, x: float, y: float,
                 w: float = 26, h: float = 16) -> list[str]:
    """A legend swatch that carries texture, border style AND the shape mark."""
    paint = _band_paint(fig, th, b)
    dash = "4 3" if b.border == "dashed" else None
    out = [svg.rect(x, y, w, h, fill=paint, stroke=b.border_ink,
                    stroke_width=th["border_weight"], stroke_dasharray=dash, rx=2)]
    out.append(svg.mark(b.shape, x + w + 13, y + h / 2, 11,
                        b.fill if b.on_scale else "none", b.border_ink, 1.3))
    return out


def _legend(fig: svg.Figure, th: dict, x: float, y: float, width: float,
            keys=palette.BAND_ORDER) -> float:
    """A legend that defines the bands in words.

    A swatch-and-name legend still makes the reader map colour to meaning. This
    one prints what each band asserts, and draws a rule before the two
    not-a-rating states so the break in kind is visible, not just stated.
    """
    fig.add(svg.text(x, y, "How to read this", size=FONT_BODY, fill=th["ink"], weight="bold"))
    y += 15
    for key in keys:
        b = palette.BANDS[key]
        if key == palette.NON_RATING_KEYS[0]:
            y += 4
            fig.add(svg.line(x, y, x + width, y, stroke=th["rule"], stroke_width=1,
                             stroke_dasharray="3 3"))
            y += 5
            fig.add(svg.text(x, y + 9, "Below this line: not ratings.", size=FONT_SMALL,
                             fill=th["muted"], weight="bold"))
            y += 17
        fig.add_all(_band_swatch(fig, th, b, x, y))
        fig.add(svg.text(x + 54, y + 12, b.label, size=FONT_BODY, fill=th["ink"], weight="bold"))
        fig.add(svg.text(x + 54 + 8.2 * len(b.label) + 12, y + 12, b.meaning,
                         size=FONT_SMALL, fill=th["muted"]))
        y += 23
    return y


# --------------------------------------------------------------------------
# 1. Twelve-cell matrix
# --------------------------------------------------------------------------
def matrix_figure(matrix, theme_name: str = palette.DEFAULT_THEME) -> svg.Figure:
    th = _theme(theme_name)
    row_head = 132
    col_w = 150
    row_h = 74
    head_h = 40
    n_cols = len(matrix.area_ids)
    n_rows = len(matrix.group_ids)

    grid_w = row_head + col_w * n_cols
    width = int(MARGIN * 2 + max(grid_w, 720))
    legend_rows = len(palette.BAND_ORDER)
    height = int(MARGIN * 2 + 56 + head_h + row_h * n_rows + 34 + 15 + legend_rows * 23 + 26 + 44)

    fig = svg.Figure(width, height, f"{matrix.title} - assessment matrix",
                     alt_text.matrix_alt(matrix), th["background"], slug="matrix")

    x0 = MARGIN
    y = _header(fig, th, f"{matrix.title}: assessment matrix",
                f"{matrix.subtitle}  |  {matrix.disclaimer}", x0, MARGIN + 14)
    y += 12
    top = y

    # Column headers
    for c, aid in enumerate(matrix.area_ids):
        cx = x0 + row_head + c * col_w
        fig.add(svg.text(cx + 8, top + 16, matrix.area_label(aid), size=FONT_BODY,
                         fill=th["ink"], weight="bold"))
        fig.add(svg.text(cx + 8, top + 30, aid, size=FONT_SMALL, fill=th["muted"]))
    fig.add(svg.line(x0, top + head_h - 6, x0 + grid_w, top + head_h - 6,
                     stroke=th["rule"], stroke_width=1.2))

    # Rows
    for r, gid in enumerate(matrix.group_ids):
        ry = top + head_h + r * row_h
        fig.add(svg.text(x0, ry + 22, matrix.group_label(gid), size=FONT_BODY,
                         fill=th["ink"], weight="bold"))
        fig.add(svg.text(x0, ry + 37, gid, size=FONT_SMALL, fill=th["muted"]))
        ctx = matrix.group_context(gid)
        if ctx:
            fig.add(svg.text(x0, ry + 52, ctx[:26], size=FONT_SMALL, fill=th["muted"]))

        for c, aid in enumerate(matrix.area_ids):
            cx = x0 + row_head + c * col_w
            cell = matrix.cell(gid, aid)
            if cell is None:
                # No record supplied at all. Drawn as an explicit hole, never
                # backfilled with a rating.
                fig.add(svg.rect(cx + 4, ry + 4, col_w - 12, row_h - 12, fill="none",
                                 stroke=th["rule"], stroke_width=1.2,
                                 stroke_dasharray="2 4", rx=3))
                fig.add(svg.text(cx + 14, ry + 38, "no record supplied", size=FONT_SMALL,
                                 fill=th["muted"]))
                continue
            b = cell.band
            paint = _band_paint(fig, th, b)
            dash = "5 3" if b.border == "dashed" else None
            fig.add(svg.rect(cx + 4, ry + 4, col_w - 12, row_h - 12, fill=paint,
                             stroke=b.border_ink, stroke_width=th["border_weight"],
                             stroke_dasharray=dash, rx=3))
            fig.add(svg.mark(b.shape, cx + 22, ry + 26, 14,
                             b.fill if b.on_scale else "none", b.ink, 1.4))
            fig.add(svg.text(cx + 38, ry + 30, b.label, size=FONT_BODY, fill=b.ink,
                             weight="bold"))
            detail = (f"{cell.evidence_total} evidence items"
                      if cell.evidence_collected else "no evidence collected")
            fig.add(svg.text(cx + 14, ry + 50, detail, size=FONT_SMALL, fill=b.ink))

    y = top + head_h + row_h * n_rows + 18
    totals = matrix.totals()
    fig.add(svg.text(x0, y, (f"{totals['rated']} of {totals['cells_expected']} cells carry a "
                             f"rating. {totals['insufficient_evidence']} had insufficient "
                             f"evidence, {totals['not_assessed']} were not assessed"
                             + (f", {totals['cells_missing']} had no record supplied"
                                if totals["cells_missing"] else "") + "."),
                     size=FONT_BODY, fill=th["ink"]))
    y += 22
    y = _legend(fig, th, x0, y, grid_w)
    y += 6
    fig.add(svg.text(x0, y + 10,
                     "Unrated cells describe the evidence available to this review, not the "
                     "performance of the group. They are excluded from every count of ratings.",
                     size=FONT_SMALL, fill=th["muted"]))
    return fig


# --------------------------------------------------------------------------
# 2. Cross-group comparison
# --------------------------------------------------------------------------
def cross_group_figure(matrix, theme_name: str = palette.DEFAULT_THEME) -> svg.Figure:
    """Dot chart: x = assessment area, y = band lane.

    The design decision that matters: the two not-a-rating lanes sit BELOW a
    solid rule, in a shaded region labelled "Off the rating scale". A reader
    scanning downward does not run out of scale and land on "not assessed" --
    they hit a boundary first. Position alone therefore cannot be misread as
    "worst", and every plotted mark is captioned with its group code so group
    identity never depends on the colour of the mark.
    """
    th = _theme(theme_name)
    lane_h = 40
    left = 172
    col_w = 150
    n_cols = len(matrix.area_ids)
    grid_w = left + col_w * n_cols
    width = int(MARGIN * 2 + max(grid_w, 720))

    scale_lanes = len(palette.ORDINAL_KEYS)
    off_lanes = len(palette.NON_RATING_KEYS)
    height = int(MARGIN * 2 + 56 + 34 + lane_h * scale_lanes + 34 + lane_h * off_lanes
                 + 40 + 24 * (len(matrix.group_ids) + 1) + 40)

    fig = svg.Figure(width, height, f"{matrix.title} - comparison across groups",
                     alt_text.cross_group_alt(matrix), th["background"], slug="cross")

    x0 = MARGIN
    y = _header(fig, th, f"{matrix.title}: comparison across groups",
                f"{matrix.subtitle}  |  {matrix.disclaimer}", x0, MARGIN + 14)
    y += 10

    for c, aid in enumerate(matrix.area_ids):
        cx = x0 + left + c * col_w
        fig.add(svg.text(cx + col_w / 2, y + 14, matrix.area_label(aid), size=FONT_BODY,
                         fill=th["ink"], weight="bold", anchor="middle"))
    y += 26
    fig.add(svg.line(x0, y, x0 + grid_w, y, stroke=th["rule"], stroke_width=1.2))

    def draw_lane(ly: float, b: palette.Band) -> None:
        fig.add_all(_band_swatch(fig, th, b, x0, ly + lane_h / 2 - 8, 22, 15))
        fig.add(svg.text(x0 + 48, ly + lane_h / 2 + 4, b.label, size=FONT_BODY,
                         fill=th["ink"], weight="bold"))
        fig.add(svg.line(x0 + left, ly + lane_h, x0 + grid_w, ly + lane_h,
                         stroke=th["rule"], stroke_width=0.6, stroke_dasharray="2 4"))

    lane_y = {}
    ly = y
    for key in palette.ORDINAL_KEYS:  # STRENGTH at the top
        lane_y[key] = ly
        draw_lane(ly, palette.BANDS[key])
        ly += lane_h

    # The break. Solid rule + a shaded band + a heading in words.
    fig.add(svg.line(x0, ly + 8, x0 + grid_w, ly + 8, stroke=th["ink"], stroke_width=2))
    fig.add(svg.text(x0, ly + 26, "Off the rating scale - these are statements about the "
                                  "evidence, not lower ratings",
                     size=FONT_SMALL, fill=th["ink"], weight="bold"))
    ly += 34
    off_top = ly
    fig.add(svg.rect(x0, off_top, grid_w, lane_h * off_lanes, fill=palette.BANDS["UNASSESSED"].fill,
                     stroke="none", opacity=0.45))
    for key in palette.NON_RATING_KEYS:
        lane_y[key] = ly
        draw_lane(ly, palette.BANDS[key])
        ly += lane_h

    # Plot every cell, direct-labelled with its group code.
    for gi, gid in enumerate(matrix.group_ids):
        style = palette.group_style(gi)
        for c, aid in enumerate(matrix.area_ids):
            cell = matrix.cell(gid, aid)
            if cell is None:
                continue
            b = cell.band
            slot_w = col_w / (len(matrix.group_ids) + 1)
            cx = x0 + left + c * col_w + slot_w * (gi + 1)
            cy = lane_y[b.key] + lane_h / 2
            fig.add(svg.mark(style["shape"], cx, cy, 13, style["colour"], style["colour"], 1.2))
            fig.add(svg.text(cx, cy + 20, gid, size=FONT_SMALL, fill=th["ink"],
                             anchor="middle", weight="bold"))

    y = off_top + lane_h * off_lanes + 26
    fig.add(svg.text(x0, y, "Groups (shape and printed code identify the group; colour is a "
                            "secondary cue only)", size=FONT_BODY, fill=th["ink"], weight="bold"))
    y += 20
    for gi, gid in enumerate(matrix.group_ids):
        style = palette.group_style(gi)
        fig.add(svg.mark(style["shape"], x0 + 8, y - 4, 13, style["colour"], style["colour"], 1.2))
        summary = matrix.summarize_group(gid)
        fig.add(svg.text(x0 + 22, y, f"{gid} - {summary.label}", size=FONT_BODY,
                         fill=th["ink"], weight="bold"))
        ctx = summary.context
        if ctx:
            fig.add(svg.text(x0 + 22 + 8.2 * len(f"{gid} - {summary.label}") + 12, y,
                             ctx, size=FONT_SMALL, fill=th["muted"]))
        y += 22
    fig.add(svg.text(x0, y + 12,
                     "Groups differ in size, funding and service model. Read a difference as a "
                     "prompt for a question, not as a ranking.",
                     size=FONT_SMALL, fill=th["muted"]))
    return fig


# --------------------------------------------------------------------------
# 3. Evidence coverage
# --------------------------------------------------------------------------
def evidence_coverage_figure(matrix, theme_name: str = palette.DEFAULT_THEME) -> svg.Figure:
    """Stacked bars of evidence actually collected, per group.

    The caption beside each bar is doing as much work as the bar: a longer bar
    means better evidenced, never better performing, and the sentence says that
    in words so the length cannot be read as a score.
    """
    th = _theme(theme_name)
    left = 150
    bar_h = 30
    row_h = 62
    plot_w = 420
    width = int(MARGIN * 2 + left + plot_w + 200)
    n = len(matrix.group_ids)
    height = int(MARGIN * 2 + 56 + 26 + row_h * n + 30
                 + 20 + 22 * len(palette.EVIDENCE_KINDS) + 56)

    fig = svg.Figure(width, height, f"{matrix.title} - evidence behind each group",
                     alt_text.evidence_alt(matrix), th["background"], slug="evidence")

    x0 = MARGIN
    y = _header(fig, th, f"{matrix.title}: evidence behind each rating",
                f"{matrix.subtitle}  |  {matrix.disclaimer}", x0, MARGIN + 14)
    y += 10

    summaries = [matrix.summarize_group(g) for g in matrix.group_ids]
    max_total = max([s.evidence_total for s in summaries] + [1])
    scale = plot_w / max_total

    fig.add(svg.text(x0, y + 12, "Evidence items collected (each segment labelled with its count)",
                     size=FONT_BODY, fill=th["ink"], weight="bold"))
    y += 24

    for s in summaries:
        fig.add(svg.text(x0, y + 18, f"{s.group} - {s.label}", size=FONT_BODY,
                         fill=th["ink"], weight="bold"))
        bx = x0 + left
        if s.evidence_total == 0:
            # Zero evidence is drawn as an explicit dashed placeholder with the
            # words, never as an absent bar a reader would scroll past.
            fig.add(svg.rect(bx, y, 190, bar_h, fill=palette.BANDS["UNASSESSED"].fill,
                             stroke=palette.BANDS["UNASSESSED"].border_ink,
                             stroke_width=th["border_weight"], stroke_dasharray="5 3", rx=2))
            fig.add(svg.text(bx + 10, y + 20, "no evidence collected", size=FONT_SMALL,
                             fill=th["ink"]))
        else:
            for kind in palette.EVIDENCE_KINDS:
                count = s.evidence[kind["key"]]
                if count == 0:
                    continue
                seg_w = count * scale
                paint = fig.texture_fill(f"ev-{kind['key']}", kind["texture"], kind["fill"],
                                         kind["ink"], th["hatch_weight"])
                fig.add(svg.rect(bx, y, seg_w, bar_h, fill=paint, stroke=th["background"],
                                 stroke_width=1.2))
                label = f"{kind['short']} {count}"
                if seg_w >= 8.0 * len(label):
                    fig.add(svg.text(bx + seg_w / 2, y + 20, label, size=FONT_SMALL,
                                     fill=kind["ink"], anchor="middle", weight="bold"))
                else:
                    # Too narrow for readable text inside: put it above, with a
                    # leader, rather than shrinking type below legibility.
                    fig.add(svg.text(bx + seg_w / 2, y - 3, label, size=FONT_SMALL,
                                     fill=th["ink"], anchor="middle"))
                bx += seg_w
        fig.add(svg.text(x0 + left + plot_w + 14, y + 12, f"{s.evidence_total} items",
                         size=FONT_BODY, fill=th["ink"], weight="bold"))
        fig.add(svg.text(x0 + left, y + bar_h + 16, s.coverage_sentence,
                         size=FONT_SMALL, fill=th["muted"]))
        y += row_h

    y += 8
    fig.add(svg.text(x0, y, "Evidence kinds", size=FONT_BODY, fill=th["ink"], weight="bold"))
    y += 16
    for kind in palette.EVIDENCE_KINDS:
        paint = fig.texture_fill(f"ev-{kind['key']}", kind["texture"], kind["fill"],
                                 kind["ink"], th["hatch_weight"])
        fig.add(svg.rect(x0, y, 26, 15, fill=paint, stroke=th["rule"], stroke_width=1, rx=2))
        fig.add(svg.text(x0 + 34, y + 12, f"{kind['short']} - {kind['label']}",
                         size=FONT_BODY, fill=th["ink"]))
        y += 22
    fig.add(svg.text(x0, y + 14,
                     "A longer bar means the area is better evidenced, not that the group "
                     "performs better. Areas not assessed contribute no evidence and are not "
                     "shown as zero.", size=FONT_SMALL, fill=th["muted"]))
    return fig


# --------------------------------------------------------------------------
# 4. Phased roadmap
# --------------------------------------------------------------------------
def roadmap_figure(matrix, theme_name: str = palette.DEFAULT_THEME) -> svg.Figure:
    th = _theme(theme_name)
    col_w = 236
    gap = 18
    card_h = 92
    n_phases = len(palette.PHASES)
    width = int(MARGIN * 2 + col_w * n_phases + gap * (n_phases - 1))

    by_phase = {p["key"]: [] for p in palette.PHASES}
    for item in matrix.roadmap:
        by_phase[item["phase"]].append(item)
    rows = max([len(v) for v in by_phase.values()] + [1])
    height = int(MARGIN * 2 + 56 + 40 + rows * (card_h + 14) + 74)

    fig = svg.Figure(width, height, f"{matrix.title} - phased roadmap",
                     alt_text.roadmap_alt(matrix), th["background"], slug="roadmap")
    fig.add_def(svg.ARROW_MARKER_ID, svg.arrow_marker(th["ink"]))

    x0 = MARGIN
    y = _header(fig, th, f"{matrix.title}: phased roadmap",
                f"{matrix.subtitle}  |  {matrix.disclaimer}", x0, MARGIN + 14)
    y += 10
    top = y

    # Phase headers: numbered badge + written window. The number is redundant
    # with the position and the words, so a reader who sees only one still knows.
    for pi, p in enumerate(palette.PHASES):
        px = x0 + pi * (col_w + gap)
        paint = fig.texture_fill(f"ph-{p['key']}", p["texture"], p["fill"], p["ink"],
                                 th["hatch_weight"])
        fig.add(svg.rect(px, top, col_w, 30, fill=paint, stroke=p["fill"],
                         stroke_width=th["border_weight"], rx=3))
        fig.add(svg.circle(px + 17, top + 15, 10, fill=p["ink"]))
        fig.add(svg.text(px + 17, top + 19, p["badge"], size=FONT_BODY, fill=p["fill"],
                         anchor="middle", weight="bold"))
        fig.add(svg.text(px + 34, top + 19, f"Phase {p['badge']}: {p['label']}",
                         size=FONT_BODY, fill=p["ink"], weight="bold"))

    centres: dict[str, tuple[float, float]] = {}
    positions: dict[str, tuple[float, float]] = {}
    for pi, p in enumerate(palette.PHASES):
        px = x0 + pi * (col_w + gap)
        cy = top + 44
        for item in by_phase[p["key"]]:
            positions[item["id"]] = (px, cy)
            centres[item["id"]] = (px + col_w / 2, cy + card_h / 2)
            cy += card_h + 14

    # Dependency arrows first, so cards sit on top of them.
    for item in matrix.roadmap:
        for dep in item.get("depends_on", []) or []:
            if dep not in centres or item["id"] not in centres:
                continue
            x1, y1 = centres[dep]
            x2, y2 = centres[item["id"]]
            fig.add(svg.path(f"M{x1},{y1} C{(x1 + x2) / 2},{y1} {(x1 + x2) / 2},{y2} {x2},{y2}",
                             fill="none", stroke=th["ink"], stroke_width=1.4,
                             marker_end=f"url(#{svg.ARROW_MARKER_ID})", opacity=0.75))

    for item in matrix.roadmap:
        px, py = positions[item["id"]]
        p = palette.phase(item["phase"])
        fig.add(svg.rect(px, py, col_w, card_h, fill=th["background"], stroke=p["fill"],
                         stroke_width=th["border_weight"], rx=4))
        fig.add(svg.rect(px, py, 5, card_h, fill=p["fill"], stroke="none"))
        fig.add(svg.circle(px + 22, py + 18, 9, fill=p["fill"]))
        fig.add(svg.text(px + 22, py + 22, p["badge"], size=FONT_SMALL, fill=p["ink"],
                         anchor="middle", weight="bold"))
        fig.add(svg.text(px + 38, py + 22, item["id"], size=FONT_BODY, fill=th["ink"],
                         weight="bold"))
        title = item["title"]
        fig.add(svg.text(px + 14, py + 40, title[:40], size=FONT_BODY, fill=th["ink"]))
        if len(title) > 40:
            fig.add(svg.text(px + 14, py + 54, title[40:80], size=FONT_BODY, fill=th["ink"]))
        fig.add(svg.text(px + 14, py + 68, f"from {item['recommendation']}", size=FONT_SMALL,
                         fill=th["muted"]))

        effort = item.get("effort")
        if effort:
            fig.add(svg.text(px + 14, py + 84, f"Effort: {effort}", size=FONT_SMALL,
                             fill=th["ink"]))
        else:
            # Unknown effort gets the not-a-rating vocabulary: dashed edge,
            # neutral fill, spelled out. Never a guessed number.
            u = palette.UNKNOWN_EFFORT
            paint = fig.texture_fill("unknown-effort", u["texture"], u["fill"],
                                     palette.BANDS["UNASSESSED"].texture_ink,
                                     th["hatch_weight"])
            fig.add(svg.rect(px + 12, py + 72, 152, 16, fill=paint, stroke=u["border_ink"],
                             stroke_width=1.2, stroke_dasharray="4 3", rx=2))
            fig.add(svg.text(px + 18, py + 84, u["label"], size=FONT_SMALL, fill=u["ink"]))

        deps = item.get("depends_on", []) or []
        if deps:
            # The arrow is a visual cue; the words are the accessible one.
            fig.add(svg.text(px + col_w - 12, py + 84, "after " + ", ".join(deps),
                             size=FONT_SMALL, fill=th["muted"], anchor="end"))

    y = top + 44 + rows * (card_h + 14) + 12
    fig.add(svg.text(x0, y, "Arrows show prerequisites. Each card also names its prerequisite in "
                            "words, so the sequence survives being read without the arrows.",
                     size=FONT_SMALL, fill=th["muted"]))
    fig.add(svg.text(x0, y + 16, "Phase windows are planning horizons, not commitments. Items "
                                 "with no effort estimate are marked as such and not scheduled "
                                 "by guesswork.", size=FONT_SMALL, fill=th["muted"]))
    return fig


FIGURES = {
    "matrix": matrix_figure,
    "cross-group": cross_group_figure,
    "evidence-coverage": evidence_coverage_figure,
    "roadmap": roadmap_figure,
}
