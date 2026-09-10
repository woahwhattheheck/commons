# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json

import pytest

from validate_panel import load_schedule, validate_rows


def row(variant, seed, seat, own, rival, *, opponent="arlene", status="complete"):
    scores = [0.0, 0.0]
    scores[seat] = float(own)
    scores[1 - seat] = float(rival)
    return {
        "variant": variant,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": status,
        "scores": scores,
    }


def panel(pairs=4, candidate_delta=1):
    rows = []
    for index in range(pairs):
        seat = index % 2
        rows.append(row("baseline", index, seat, 100, 90))
        rows.append(row("candidate", index, seat, 100 + candidate_delta, 90))
    return rows


def schedule(rows):
    return {
        (str(item["opponent"]), int(item["seed"]), int(item["candidate_seat"]))
        for item in rows
        if item.get("variant") in {"baseline", "candidate"}
    }


def verdict(rows, *, expected=None, min_pairs=4):
    return validate_rows(
        rows,
        expected_pairs=schedule(rows) if expected is None else expected,
        min_pairs=min_pairs,
    )


def test_admits_complete_improving_both_seat_panel():
    rows = panel()
    result = verdict(rows)
    assert result.admitted
    assert result.schedule_bound
    assert result.complete_pairs == 4
    assert result.seats == (0, 1)


def test_rejects_unbound_schedule_even_when_counts_look_complete():
    result = validate_rows(panel(), min_pairs=4)
    assert not result.admitted
    assert "schedule_unbound" in result.reasons


def test_rejects_observed_s02_style_collapse():
    rows = []
    base = [(126220, 124828), (126220, 124828), (112488, 110894), (112409, 111059)]
    cand = [(17953, 86486), (17953, 86486), (24226, 132924), (24226, 132924)]
    for index, ((bo, br), (co, cr)) in enumerate(zip(base, cand)):
        seat = index % 2
        rows.append(row("baseline", index, seat, bo, br))
        rows.append(row("candidate", index, seat, co, cr))
    result = verdict(rows)
    assert not result.admitted
    assert result.baseline_wtl[0] == 4
    assert result.candidate_wtl[2] == 4
    assert any(reason.startswith("mean_margin_delta:") for reason in result.reasons)


def test_rejects_missing_candidate_row():
    full = panel()
    expected = schedule(full)
    rows = full[:-1]
    result = verdict(rows, expected=expected, min_pairs=3)
    assert not result.admitted
    assert "missing_variant_rows:1" in result.reasons


def test_rejects_entirely_omitted_pair_that_aggregate_discovery_cannot_see():
    full = panel()
    expected = schedule(full)
    rows = full[:-2]
    result = verdict(rows, expected=expected, min_pairs=3)
    assert not result.admitted
    assert "missing_expected_pairs:1" in result.reasons
    assert "missing_variant_rows:2" in result.reasons


def test_rejects_unexpected_pair():
    rows = panel()
    expected = schedule(rows)
    rows.extend([row("baseline", 999, 0, 100, 90), row("candidate", 999, 0, 101, 90)])
    result = verdict(rows, expected=expected)
    assert not result.admitted
    assert "unexpected_pairs:1" in result.reasons


def test_rejects_unexpected_variant():
    rows = panel()
    expected = schedule(rows)
    rows.append(row("experimental", 0, 0, 100, 90))
    result = verdict(rows, expected=expected)
    assert not result.admitted
    assert "unexpected_variants:1" in result.reasons


def test_rejects_duplicate():
    rows = panel()
    expected = schedule(rows)
    rows.append(copy.deepcopy(rows[0]))
    result = verdict(rows, expected=expected)
    assert not result.admitted
    assert any(reason.startswith("duplicate_rows:") for reason in result.reasons)


def test_rejects_noncomplete():
    rows = panel()
    expected = schedule(rows)
    rows[0]["status"] = "timeout"
    result = verdict(rows, expected=expected, min_pairs=3)
    assert not result.admitted
    assert any(reason.startswith("noncomplete_pairs:") for reason in result.reasons)


def test_rejects_one_seat_only():
    rows = []
    for seed in range(4):
        rows.append(row("baseline", seed, 0, 100, 90))
        rows.append(row("candidate", seed, 0, 101, 90))
    result = verdict(rows)
    assert not result.admitted
    assert any(reason.startswith("missing_required_seat:") for reason in result.reasons)


def test_rejects_worst_pair_regression_even_with_positive_mean():
    rows = panel(candidate_delta=10)
    expected = schedule(rows)
    rows[1] = row("candidate", 0, 0, 80, 90)
    result = verdict(rows, expected=expected)
    assert not result.admitted
    assert result.mean_margin_delta > 0
    assert result.worst_margin_delta < 0


def test_rejects_insufficient_pairs():
    rows = panel(pairs=2)
    result = verdict(rows, min_pairs=4)
    assert not result.admitted
    assert "insufficient_pairs:2<4" in result.reasons


def test_schedule_loader_rejects_duplicate_pairs(tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(
        json.dumps(
            {
                "pairs": [
                    {"opponent": "arlene", "seed": 1, "candidate_seat": 0},
                    {"opponent": "arlene", "seed": 1, "candidate_seat": 0},
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="duplicate expected pair"):
        load_schedule(path)
