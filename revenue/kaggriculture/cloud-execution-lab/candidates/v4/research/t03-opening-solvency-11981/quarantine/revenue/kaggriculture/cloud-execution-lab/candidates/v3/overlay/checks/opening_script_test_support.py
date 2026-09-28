# SPDX-License-Identifier: Apache-2.0
"""Fixtures shared by T03 source-contract tests."""


def observation(*, step=0, money=1000, hires_today=0, prices=None):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"money": money, "hires_today": hires_today, "unlocked_quadrants": ["NW"]},
            {"money": 1000, "hires_today": 0, "unlocked_quadrants": ["NW"]},
        ],
        "market": {"prices": prices or {"WHEAT": 25, "STRAWBERRY": 120, "MELON": 250}},
    }


def action():
    return {
        "farmer": ["MOVE", "NORTH"],
        "hands": [["PASS"]],
        "market": [["SELL", "WHEAT", 1]],
    }
