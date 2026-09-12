# SPDX-License-Identifier: Apache-2.0
from close_game_margin import build_margin_context, rank_option


def _info(own, carry, rival=0, score=1):
    return {
        "forced_feasibility": False,
        "accepted": True,
        "acceptance_score": score,
        "scenarios": {
            "a": {"own_receipts": own, "rival_receipts": rival, "carry_units": carry},
            "b": {"own_receipts": own + 2, "rival_receipts": rival + 1, "carry_units": carry},
        },
    }


def test_off_and_outside_window_are_exact_identity():
    base = (False, 3.25)
    off = build_margin_context(mode="off", now=650, last=718, own_cash=20,
                               rival_cash=10, rival_liquidation_bound=5)
    assert rank_option(_info(4, 8), off, base)[0] == base
    early = build_margin_context(mode="ahead", now=100, last=718, own_cash=20,
                                 rival_cash=10, rival_liquidation_bound=5, window=96)
    assert rank_option(_info(4, 8), early, base)[0] == base


def test_ahead_preserves_more_carry_after_liquidation_certificate():
    ctx = build_margin_context(mode="ahead", now=680, last=718, own_cash=40,
                               rival_cash=20, rival_liquidation_bound=8, buffer=2)
    assert ctx["mode"] == "ahead" and ctx["safe_ahead"]
    low_carry = rank_option(_info(12, 1), ctx, (False, 99.0))[0]
    high_carry = rank_option(_info(5, 7), ctx, (False, 1.0))[0]
    assert high_carry > low_carry


def test_ahead_degrades_to_cash_when_public_lead_is_exposed():
    ctx = build_margin_context(mode="ahead", now=680, last=718, own_cash=30,
                               rival_cash=25, rival_liquidation_bound=8)
    assert ctx["mode"] == "cash_max" and not ctx["safe_ahead"]
    high_cash = rank_option(_info(9, 6), ctx, (False, 1.0))[0]
    low_cash = rank_option(_info(4, 0), ctx, (False, 100.0))[0]
    assert high_cash > low_cash


def test_behind_prioritizes_receipt_floor_then_less_carry():
    ctx = build_margin_context(mode="behind", now=700, last=718, own_cash=11,
                               rival_cash=20, rival_liquidation_bound=6)
    assert ctx["mode"] == "behind"
    a = rank_option(_info(10, 9), ctx, (False, 1.0))[0]
    b = rank_option(_info(11, 12), ctx, (False, 0.1))[0]
    c = rank_option(_info(11, 3), ctx, (False, 0.01))[0]
    assert b > a and c > b


def test_auto_partitions_safe_ahead_and_exposed_cells():
    ahead = build_margin_context(mode="auto", now=700, last=718, own_cash=40,
                                 rival_cash=20, rival_liquidation_bound=10)
    exposed = build_margin_context(mode="auto", now=700, last=718, own_cash=26,
                                   rival_cash=20, rival_liquidation_bound=10)
    assert ahead["mode"] == "ahead"
    assert exposed["mode"] == "behind"


def test_forced_feasibility_still_dominates_policy_rank():
    ctx = build_margin_context(mode="behind", now=700, last=718, own_cash=10,
                               rival_cash=20, rival_liquidation_bound=4)
    normal = rank_option(_info(100, 0), ctx, (False, 100.0))[0]
    forced_info = _info(1, 20)
    forced_info["forced_feasibility"] = True
    forced = rank_option(forced_info, ctx, (True, -999.0))[0]
    assert forced > normal


def test_active_policy_fails_closed_on_unsupported_report():
    ctx = build_margin_context(mode="behind", now=700, last=718, own_cash=10,
                               rival_cash=20, rival_liquidation_bound=4)
    unsupported, report = rank_option({"accepted": True}, ctx, (False, 12.0))
    supported, _ = rank_option(_info(1, 50), ctx, (False, -100.0))
    assert report["reason"] == "unsupported_report"
    assert supported > unsupported


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS")
