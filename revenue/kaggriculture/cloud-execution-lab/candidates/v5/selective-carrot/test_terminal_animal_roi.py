# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib

import build_terminal_animal_roi as build
from terminal_animal_roi import filter_action


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_filter_is_identity_before_horizon():
    action = {"units": [["WAIT"]], "market": [["BUY_ANIMAL", "GOOSE", 2]]}
    assert filter_action({"step": 717}, action) is action


def test_filter_drops_only_well_formed_animal_buys_and_preserves_order():
    action = {
        "units": [["WAIT"]],
        "market": [
            ["BUY", "FEED", 3],
            ["BUY_ANIMAL", "GOOSE", 2],
            ["SELL", "EGG", 4],
            ["BUY_ANIMAL", "COW", 1],
            ["BUY_ANIMAL", "DRAGON", 1],
            ["BUY_ANIMAL", "SHEEP", 0],
        ],
        "other": {"keep": True},
    }
    original = copy.deepcopy(action)
    out = filter_action({"step": 718}, action)
    assert out is not action
    assert action == original
    assert out["units"] == action["units"]
    assert out["other"] == action["other"]
    assert out["market"] == [
        ["BUY", "FEED", 3],
        ["SELL", "EGG", 4],
        ["BUY_ANIMAL", "DRAGON", 1],
        ["BUY_ANIMAL", "SHEEP", 0],
    ]


def test_filter_fails_to_identity_on_uncertain_shapes():
    examples = [
        ({}, {"market": [["BUY_ANIMAL", "GOOSE", 1]]}),
        ({"step": "718"}, {"market": [["BUY_ANIMAL", "GOOSE", 1]]}),
        ({"step": 718}, {"market": None}),
        ({"step": 718}, [["BUY_ANIMAL", "GOOSE", 1]]),
    ]
    for obs, action in examples:
        assert filter_action(obs, action) is action


def test_filter_identity_when_no_target_row():
    action = {"market": [["SELL", "EGG", 4], ["BUY", "FEED", 1]]}
    assert filter_action({"step": 718}, action) is action


def test_filter_supports_only_bounded_declared_horizons_by_builder():
    for step in build.HORIZONS:
        assert build._horizon(step) == step
    for step in (-1, 0, 717, 719, True):
        try:
            build._horizon(step)
        except ValueError:
            pass
        else:
            raise AssertionError(step)


def test_compose_disabled_is_exact_identity(monkeypatch):
    entry = b"def agent(observation, configuration=None):\n    returned = {}\n    return returned\n"
    monkeypatch.setattr(build, "PRODUCTION_MAIN_SHA", _digest(entry))
    parent = {"main.py": entry, "x.py": b"x = 1\n"}
    helper = b"arbitrary helper bytes\n"
    out = build.compose(parent, helper, 718, enabled=False)
    assert out == parent
    assert out is not parent
    assert set(out) == set(parent)


def test_compose_enabled_changes_only_entry_and_adds_helper(monkeypatch):
    entry = b"def agent(observation, configuration=None):\n    returned = {}\n    return returned\n"
    helper = b"arbitrary helper bytes\n"
    monkeypatch.setattr(build, "PRODUCTION_MAIN_SHA", _digest(entry))
    monkeypatch.setattr(build, "HELPER_SHA", _digest(helper))
    parent = {"main.py": entry, "x.py": b"x = 1\n"}
    out = build.compose(parent, helper, 718, enabled=True)
    assert out["x.py"] == parent["x.py"]
    assert out["terminal_animal_roi.py"] == helper
    assert b"filter_action(observation, returned, min_step=718)" in out["main.py"]
    assert out["main.py"].count(b"return returned") == 1


def test_patch_refuses_identity_drift(monkeypatch):
    entry = b"def agent(observation, configuration=None):\n    return returned\n"
    helper = b"helper\n"
    monkeypatch.setattr(build, "PRODUCTION_MAIN_SHA", "0" * 64)
    monkeypatch.setattr(build, "HELPER_SHA", _digest(helper))
    try:
        build.patch_entry(entry, helper, 718)
    except ValueError as exc:
        assert "identity drift" in str(exc)
    else:
        raise AssertionError("expected identity refusal")
