# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import planner_mpc as p


BASE = {
    "farmer": ["NORTH"],
    "hands": [["WATER"]],
    "market": [["BUY_LAND"], ["SELL", "WHEAT", 4], ["HIRE"], []],
}
OBS = {
    "player": 0,
    "step": 24,
    "day": 1,
    "hour": 0,
    "farms": [
        {"farmer": [4, 4], "hands": [[4, 4]], "tiles": [[None]], "money": 3000},
        {"farmer": [4, 4], "hands": [], "tiles": [[None]], "money": 3000},
    ],
    "market": {},
    "town": {},
    "private": {},
}


def canonical(_obs, _cfg=None):
    return json.loads(json.dumps(BASE))


def evaluation(*deltas, equivalent=True, complete=True, exact=True):
    rows = tuple(
        p.ScenarioResult(
            f"s{index}",
            complete,
            exact,
            equivalent,
            100.0,
            100.0 + float(delta),
            float(delta),
            "test",
        )
        for index, delta in enumerate(deltas)
    )
    return p.Evaluation(rows)


def one_permutation(_canonical, _obs, _cfg, limit=8):
    del limit
    candidate = json.loads(json.dumps(_canonical))
    candidate["market"][0], candidate["market"][1] = (
        candidate["market"][1],
        candidate["market"][0],
    )
    return [json.loads(json.dumps(_canonical)), candidate]


def test_structure_accepts_only_exact_market_permutation():
    candidate = one_permutation(BASE, OBS, {}, 8)[1]
    assert p.structural_contract(BASE, candidate) == p.StructureCheck(
        True, "exact_market_permutation"
    )


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda a: a.update(farmer=["PASS"]), "farmer_changed"),
        (lambda a: a.update(hands=[]), "hands_changed"),
        (lambda a: a["market"].append(["HIRE"]), "market_length_changed"),
        (lambda a: a["market"].pop(), "market_length_changed"),
        (lambda a: a["market"][1].__setitem__(2, 2), "market_payload_changed"),
        (lambda a: a["market"].__setitem__(0, ["UNKNOWN"]), "market_payload_changed"),
        (lambda a: a.update(extra="payload"), "non_market_payload_changed"),
    ],
)
def test_structure_rejects_mutation(mutator, reason):
    candidate = json.loads(json.dumps(BASE))
    mutator(candidate)
    assert p.structural_contract(BASE, candidate).reason == reason


def test_structure_rejects_unknown_operation_even_as_permutation():
    base = {"farmer": ["PASS"], "hands": [], "market": [["UNKNOWN", 1], ["SELL", "WHEAT", 1]]}
    candidate = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1], ["UNKNOWN", 1]]}
    assert p.structural_contract(base, candidate).reason == "unknown_market_operation"


def test_generator_preserves_every_payload_and_worker_action():
    candidates = p.generate_candidates(BASE, OBS, {}, limit=8)
    assert candidates[0] == BASE
    assert len(candidates) > 1
    base_rows = sorted(p._json_key(row) for row in BASE["market"])
    for candidate in candidates[1:]:
        assert candidate["farmer"] == BASE["farmer"]
        assert candidate["hands"] == BASE["hands"]
        assert sorted(p._json_key(row) for row in candidate["market"]) == base_rows
        assert p.structural_contract(BASE, candidate).ok


def test_generator_is_deterministic_and_bounded():
    first = p.generate_candidates(BASE, OBS, {}, limit=4)
    second = p.generate_candidates(BASE, OBS, {}, limit=4)
    assert first == second
    assert len(first) <= 4


def test_evaluation_worst_delta_is_actual_minimum():
    result = evaluation(9, 2, 5)
    assert result.complete
    assert result.state_equivalent
    assert result.scenario_count == 3
    assert result.worst_delta == 2


def test_evaluation_needs_complete_equivalent_minimum_scenarios_and_gain():
    assert evaluation(3, 2, 1).admitted(min_scenarios=3, min_cash_gain=1)
    assert not evaluation(3, 2).admitted(min_scenarios=3, min_cash_gain=1)
    assert not evaluation(3, 2, 0).admitted(min_scenarios=3, min_cash_gain=1)
    assert not evaluation(3, 2, 1, equivalent=False).admitted(
        min_scenarios=3, min_cash_gain=1
    )
    assert not evaluation(3, 2, 1, complete=False).admitted(
        min_scenarios=3, min_cash_gain=1
    )
    assert not evaluation(3, 2, 1, exact=False).admitted(
        min_scenarios=3, min_cash_gain=1
    )


def test_off_mode_returns_canonical_without_generating():
    def explode(*_args, **_kwargs):
        raise AssertionError("candidate generator must not run")

    planner = p.Planner(canonical, mode="off", candidate_fn=explode)
    assert planner.act(OBS, {}) == BASE


def test_shadow_mode_never_executes_admitted_recommendation(tmp_path):
    seen = {"calls": 0}

    def evaluator(*_args, **_kwargs):
        seen["calls"] += 1
        return evaluation(5, 4, 3)

    log = tmp_path / "shadow.jsonl"
    planner = p.Planner(
        canonical,
        mode="shadow",
        min_scenarios=3,
        min_cash_gain=1,
        candidate_fn=one_permutation,
        evaluator=evaluator,
        log_path=str(log),
    )
    assert planner.act(OBS, {}) == BASE
    assert seen["calls"] == 1
    row = json.loads(log.read_text().splitlines()[-1])
    assert row["recommended"] is True
    assert row["executed"] is False
    assert row["evaluation_horizon"] == 1


def test_execute_mode_requires_and_uses_strict_certificate(tmp_path):
    candidate = one_permutation(BASE, OBS, {}, 8)[1]
    planner = p.Planner(
        canonical,
        mode="execute",
        min_scenarios=3,
        min_cash_gain=1,
        candidate_fn=one_permutation,
        evaluator=lambda *_args, **_kwargs: evaluation(2, 5, 1),
        log_path=str(tmp_path / "execute.jsonl"),
    )
    assert planner.act(OBS, {}) == candidate


@pytest.mark.parametrize(
    "result",
    [
        evaluation(2, 5),
        evaluation(2, 5, 0),
        evaluation(2, 5, 1, equivalent=False),
        evaluation(2, 5, 1, complete=False),
    ],
)
def test_execute_mode_fails_closed_on_weak_evidence(result, tmp_path):
    planner = p.Planner(
        canonical,
        mode="execute",
        min_scenarios=3,
        min_cash_gain=1,
        candidate_fn=one_permutation,
        evaluator=lambda *_args, **_kwargs: result,
        log_path=str(tmp_path / "reject.jsonl"),
    )
    assert planner.act(OBS, {}) == BASE


def test_timeout_returns_canonical(tmp_path):
    def timeout(*_args, **_kwargs):
        raise TimeoutError("test")

    planner = p.Planner(
        canonical,
        mode="execute",
        candidate_fn=one_permutation,
        evaluator=timeout,
        log_path=str(tmp_path / "timeout.jsonl"),
    )
    assert planner.act(OBS, {}) == BASE


def test_evaluator_exception_returns_canonical(tmp_path):
    def explode(*_args, **_kwargs):
        raise RuntimeError("test")

    planner = p.Planner(
        canonical,
        mode="execute",
        candidate_fn=one_permutation,
        evaluator=explode,
        log_path=str(tmp_path / "error.jsonl"),
    )
    assert planner.act(OBS, {}) == BASE


def test_deadline_before_candidate_returns_canonical(tmp_path):
    planner = p.Planner(
        canonical,
        mode="execute",
        budget_s=0,
        candidate_fn=one_permutation,
        evaluator=lambda *_args, **_kwargs: evaluation(9, 9, 9),
        log_path=str(tmp_path / "deadline.jsonl"),
    )
    assert planner.act(OBS, {}) == BASE


def test_default_mode_is_shadow(monkeypatch):
    monkeypatch.delenv("TITAN_MPC_MODE", raising=False)
    monkeypatch.delenv("TITAN_MPC_EXECUTE", raising=False)
    monkeypatch.setenv("TITAN_MPC", "1")
    assert p.Planner(canonical).mode == "shadow"


def test_explicit_disable_is_off(monkeypatch):
    monkeypatch.setenv("TITAN_MPC", "0")
    assert p.Planner(canonical).mode == "off"


def test_source_contains_no_original_pass_suffix_or_mutators():
    source = Path(p.__file__).read_text(encoding="utf-8")
    assert "if t==0 else legal_pass(own_obs)" not in source
    assert "self.last_rival=legal_pass(obs)" not in source
    assert "def _vary_hire" not in source
    assert "def _vary_sale" not in source
    assert "def _vary_harvest" not in source


def test_telemetry_failure_cannot_change_action(monkeypatch):
    monkeypatch.setattr(p, "_write_jsonl", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk")))
    planner = p.Planner(
        canonical,
        mode="shadow",
        candidate_fn=one_permutation,
        evaluator=lambda *_args, **_kwargs: evaluation(9, 9, 9),
    )
    assert planner.act(OBS, {}) == BASE


def test_invalid_engine_status_fails_closed():
    from types import SimpleNamespace

    valid = [
        SimpleNamespace(status="ACTIVE", observation={}),
        SimpleNamespace(status="DONE", observation={}),
    ]
    invalid = [
        SimpleNamespace(status="ERROR", observation={}),
        SimpleNamespace(status="ACTIVE", observation={}),
    ]
    assert p._states_valid(valid)
    assert not p._states_valid(invalid)


def test_live_visibility_rejects_missing_rival_private_and_day_rng():
    cert = p.live_visibility_certificate(OBS, {})
    assert not cert.exact
    assert "missing_rival_private_for_exact_reacting_transition" in cert.reasons
    boundary = dict(OBS)
    boundary["step"] = 23
    boundary["hour"] = 23
    cert2 = p.live_visibility_certificate(boundary, {"turnsPerDay": 24})
    assert "hidden_end_of_day_rng_seed" in cert2.reasons


def test_default_scenario_is_sensitivity_not_exact():
    scenarios = p.default_scenarios(OBS, {})
    assert len(scenarios) == 1
    assert scenarios[0].certified_exact is False


def test_typed_canonicalization_never_aliases_stringified_keys():
    assert p._json_key({1: "x", "1": "y"}) != p._json_key({"1": "y"})
    assert p._json_key({True: "x"}) != p._json_key({1: "x"})


def test_structure_fails_closed_on_unsupported_key_type():
    class Key:
        pass

    candidate = one_permutation(BASE, OBS, {}, 8)[1]
    candidate[Key()] = "opaque"
    assert p.structural_contract(BASE, candidate).reason == "unserializable_action"


def test_bounded_scenarios_rejects_duplicate_names():
    scenarios = (
        p.RivalScenario("same", {"farmer": ["PASS"], "hands": [], "market": []}),
        p.RivalScenario("same", {"farmer": ["PASS"], "hands": [], "market": []}),
    )
    rows, reason = p._bounded_scenarios(scenarios, time.perf_counter() + 1)
    assert len(rows) == 1
    assert reason == "duplicate_scenario_name"


def test_bounded_scenarios_caps_raw_pulls():
    pulls = {"n": 0}

    def source():
        while True:
            pulls["n"] += 1
            yield p.RivalScenario(
                f"s{pulls['n']}",
                {"farmer": ["PASS"], "hands": [], "market": []},
            )

    rows, reason = p._bounded_scenarios(source(), time.perf_counter() + 1, limit=4)
    assert len(rows) == 4
    assert pulls["n"] == 5
    assert reason == "scenario_limit_exceeded"
