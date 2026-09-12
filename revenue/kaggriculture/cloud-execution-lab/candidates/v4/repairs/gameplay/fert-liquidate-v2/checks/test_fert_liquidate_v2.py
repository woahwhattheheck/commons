"""OFF-identity + mechanism tests for r04_fert_liquidate v2 (overflow dump)."""
import copy
import sys

sys.path.insert(0, "/home/hatch/workspace/build/v4/fertliq-hybrid/CAND")
import r04_fert_liquidate as fl


def fresh_obs():
    return {"step": 100, "day": 4, "hour": 4, "player": 0}


def fresh_market():
    return [["SELL", "WHEAT", 50]]


def test_off_identity():
    m = fresh_market()
    before = copy.deepcopy(m)
    out = fl.apply(fresh_obs(), m, enabled=False,
                   shed_stock={"FERTILIZER": 50, "WHEAT": 60})
    assert out == before, "OFF must not touch the market"


def test_no_engage_below_threshold():
    m = fresh_market()
    out = fl.apply(fresh_obs(), m, enabled=True,
                   shed_stock={"FERTILIZER": 30, "WHEAT": 60})  # total 90
    assert out == [["SELL", "WHEAT", 50]], "no dump below 98"


def test_dump_at_near_full():
    m = fresh_market()
    shed = {"FERTILIZER": 20, "WHEAT": 80}  # total 100
    out = fl.apply(fresh_obs(), m, enabled=True, shed_stock=shed)
    assert out[0] == ["SELL", "FERTILIZER", 10], f"dump to 90, got {out[0]}"
    assert out[1] == ["SELL", "WHEAT", 50], "base rows preserved"


def test_dump_capped_by_fertilizer():
    m = fresh_market()
    shed = {"FERTILIZER": 5, "WHEAT": 95}  # total 100, only 5 fert
    out = fl.apply(fresh_obs(), m, enabled=True, shed_stock=shed)
    assert out[0] == ["SELL", "FERTILIZER", 5], f"got {out[0]}"


def test_no_fertilizer_no_dump():
    m = fresh_market()
    out = fl.apply(fresh_obs(), m, enabled=True,
                   shed_stock={"WHEAT": 99})  # full but no fertilizer
    assert out == [["SELL", "WHEAT", 50]]


def test_respects_row_cap():
    m = [["SELL", "WHEAT", i] for i in range(10)]
    shed = {"FERTILIZER": 20, "WHEAT": 80}
    out = fl.apply(fresh_obs(), m, enabled=True, shed_stock=shed,
                   max_orders=10)
    assert len(out) == 10, "no row added at cap"
    assert not any(o[1] == "FERTILIZER" for o in out)


def test_fail_closed_no_stock():
    m = fresh_market()
    out = fl.apply(fresh_obs(), m, enabled=True, shed_stock=None)
    assert out == [["SELL", "WHEAT", 50]]


def test_never_strips_buys():
    m = [["BUY_PRODUCT", "FERTILIZER", 10], ["SELL", "WHEAT", 50]]
    shed = {"FERTILIZER": 20, "WHEAT": 80}
    out = fl.apply(fresh_obs(), m, enabled=True, shed_stock=shed,
                   max_orders=10)
    kinds = [tuple(o[:2]) for o in out]
    assert ("BUY_PRODUCT", "FERTILIZER") in kinds, "v2 never strips buys"


def test_report_tracks():
    fl._report["engaged"] = 0
    fl._report["dumped"] = 0
    m = fresh_market()
    shed = {"FERTILIZER": 20, "WHEAT": 80}
    fl.apply(fresh_obs(), m, enabled=True, shed_stock=shed)
    r = fl.last_report()
    assert r["engaged"] == 1 and r["dumped"] == 10, r


if __name__ == "__main__":
    test_off_identity()
    test_no_engage_below_threshold()
    test_dump_at_near_full()
    test_dump_capped_by_fertilizer()
    test_no_fertilizer_no_dump()
    test_respects_row_cap()
    test_fail_closed_no_stock()
    test_never_strips_buys()
    test_report_tracks()
    print("ALL V2 TESTS PASS")
