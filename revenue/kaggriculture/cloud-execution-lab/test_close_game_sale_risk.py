# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for the V5 close-game sale-risk selector."""
from copy import deepcopy

from close_game_sale_risk import transform


def quote(item, inventory, _params):
    if item == "MILK":
        return max(1, 100 - 5 * int(inventory))
    if item == "WOOL":
        return 60
    return 10


def observation(*, step=710, own=5100, rival=5000):
    return {
        "step": step,
        "player": 0,
        "farms": [{"money": own}, {"money": rival}],
        "market": {
            "prices": {"MILK": 100, "WOOL": 60},
            "inventory": {"MILK": 0, "WOOL": 0},
            "params": {},
        },
    }


def config(mode, **extra):
    cfg = {
        "episodeSteps": 720,
        "maxMarketOrdersPerTurn": 10,
        "shedCapacity": 10,
        "titanCloseGameWindow": 48,
        "titanCloseGameSaleRisk": mode,
    }
    cfg.update(extra)
    return cfg


def action(first="MILK", second="WOOL"):
    return {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", first, 2], ["SELL", second, 2]],
    }


def check(name, condition):
    if not condition:
        raise AssertionError(name)


def main():
    base = action("WOOL", "MILK")

    # Missing opt-in is exact identity and caller isolation is preserved.
    original = deepcopy(base)
    out = transform(base, observation(), config("legacy"), quote=quote)
    check("legacy identity", out == original)
    check("caller untouched", base == original and out is not base)

    # cash_max prioritizes exact current receipts: MILK=195 > WOOL=120.
    out = transform(base, observation(), config("cash_max"), quote=quote)
    check("cash max engages", out["market"][:2] == [["SELL", "MILK", 2], ["SELL", "WOOL", 2]])

    # Fragile public lead: shed-cap stress is $1000.  Under ten rival units,
    # MILK falls to $95 for the lot while WOOL remains $120, so conservative
    # ordering protects the robust cash row first.
    fragile = action("MILK", "WOOL")
    out = transform(fragile, observation(own=5100, rival=5000),
                    config("ahead_conservative"), quote=quote)
    check("fragile lead stressed order",
          out["market"][:2] == [["SELL", "WOOL", 2], ["SELL", "MILK", 2]])

    # A lead above the deliberately coarse rival liquidation bound is secure;
    # conservative mode collapses back to immediate cash ordering.
    out = transform(base, observation(own=7001, rival=5000),
                    config("ahead_conservative"), quote=quote)
    check("secure lead cash order",
          out["market"][:2] == [["SELL", "MILK", 2], ["SELL", "WOOL", 2]])

    # Behind but within the same liquidation bound, exposed MILK receives the
    # aggressive front-run premium and moves ahead of stable WOOL.
    out = transform(base, observation(own=4900, rival=5000),
                    config("behind_aggressive"), quote=quote)
    check("behind aggressive engages",
          out["market"][:2] == [["SELL", "MILK", 2], ["SELL", "WOOL", 2]])

    # Explicit sign-mismatched policies fail closed rather than silently acting.
    out = transform(base, observation(own=4900, rival=5000),
                    config("ahead_conservative"), quote=quote)
    check("ahead mode while behind identity", out == base)
    out = transform(base, observation(own=5100, rival=5000),
                    config("behind_aggressive"), quote=quote)
    check("behind mode while ahead identity", out == base)

    # Adaptive selects the same public-gap branch without hidden-state guesses.
    out = transform(fragile, observation(own=5100, rival=5000),
                    config("adaptive"), quote=quote)
    check("adaptive ahead",
          out["market"][:2] == [["SELL", "WOOL", 2], ["SELL", "MILK", 2]])
    out = transform(base, observation(own=4900, rival=5000),
                    config("adaptive"), quote=quote)
    check("adaptive behind",
          out["market"][:2] == [["SELL", "MILK", 2], ["SELL", "WOOL", 2]])

    # Outside the close window is identity.
    out = transform(base, observation(step=600), config("cash_max"), quote=quote)
    check("outside window identity", out == base)

    # Economic barriers split blocks; nothing crosses BUY/HIRE/input rows.
    barrier = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [
            ["SELL", "WOOL", 2],
            ["BUY_SEED", "CARROT", 1],
            ["SELL", "MILK", 2],
        ],
    }
    out = transform(barrier, observation(), config("cash_max"), quote=quote)
    check("barrier topology", out == barrier)

    # Row quantities and multiset are invariant whenever a reorder engages.
    before = sorted(map(tuple, base["market"]))
    after = transform(base, observation(), config("cash_max"), quote=quote)
    check("quantity multiset", sorted(map(tuple, after["market"])) == before)

    print("close-game-sale-risk: PASS")


if __name__ == "__main__":
    main()
