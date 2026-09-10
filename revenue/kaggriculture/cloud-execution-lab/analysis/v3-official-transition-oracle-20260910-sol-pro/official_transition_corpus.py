#!/usr/bin/env python3
"""Predecessor-killing corpus for the exact official transition oracle."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

from official_transition_oracle import run_fixture, semantic_hash

Json = Any
FIXTURE_SCHEMA = "titan.v3.official-transition-fixture.v1"
PRIOR_ORACLE = {
    "pr": 11700,
    "head": "253cf3ce62faed47461e517ca56c721a2da60e87",
    "hosted_run": 34403550090,
    "artifact": 10124440153,
    "evidence_sha256": "87b51c0aafa70cdac352d52eae5daba40c9a9eb2ed9cabfea0eb553cab1177ea",
    "atomic_plant_fingerprint": "bcc7f03db8a1403545fd5132b80b8c50f2aaf53e32ed0ebeb5f1d8d88c9b358f",
    "lockstep_market_fingerprint": "7d9988d86c23ee211b464b2ed956c6fb3d45ecdd45bfa7d614930e0c11b4ea2e",
}


def pass_action(market: Json | None = None) -> dict[str, Json]:
    return {
        "farmer": ["PASS"],
        "hands": [],
        "market": [] if market is None else copy.deepcopy(market),
    }


def step(actions0: Json, actions1: Json, number: int | None = None) -> dict[str, Json]:
    row: dict[str, Json] = {"actions": [copy.deepcopy(actions0), copy.deepcopy(actions1)]}
    if number is not None:
        row["step"] = number
    return row


def fixture(
    name: str,
    *,
    start_step: int,
    steps: list[dict[str, Json]],
    configuration: dict[str, Json] | None = None,
    farms: list[dict[str, Json]] | None = None,
    privates: list[dict[str, Json]] | None = None,
    market: dict[str, Json] | None = None,
    town: dict[str, Json] | None = None,
    retain_states: bool = True,
    seed: int = 0,
) -> dict[str, Json]:
    numbered = []
    for offset, row in enumerate(steps):
        item = copy.deepcopy(row)
        item.setdefault("step", start_step + offset)
        numbered.append(item)
    return {
        "schema": FIXTURE_SCHEMA,
        "name": name,
        "seed": seed,
        "configuration": copy.deepcopy(configuration or {}),
        "start_step": start_step,
        "overrides": {
            "farms": copy.deepcopy(farms or [{}, {}]),
            "privates": copy.deepcopy(privates or [{}, {}]),
            "market": copy.deepcopy(market or {}),
            "town": copy.deepcopy(town or {}),
        },
        "steps": numbered,
        "retain_states": retain_states,
    }


def atomic_plant_fixture() -> dict[str, Json]:
    return fixture(
        "official-atomic-same-crop-plant",
        start_step=1,
        farms=[{"money": 0, "hands": [[3, 4]]}, {"money": 0}],
        privates=[
            {"seeds": {"WHEAT": 1}, "inventories": [{}, {}]},
            {},
        ],
        steps=[
            step(
                {
                    "farmer": ["PLANT", "WHEAT"],
                    "hands": [["PLANT", "WHEAT"]],
                    "market": [],
                },
                pass_action(),
            )
        ],
    )


def precommit_quote_fixture() -> dict[str, Json]:
    return fixture(
        "official-two-player-precommit-quote",
        start_step=1,
        farms=[{"money": 0}, {"money": 0}],
        privates=[{"shed": {"WHEAT": 1}}, {"shed": {"WHEAT": 1}}],
        market={"inventory": {"WHEAT": 10000}},
        steps=[
            step(
                pass_action([["SELL", "WHEAT", 1]]),
                pass_action([["SELL", "WHEAT", 1]]),
            )
        ],
    )


def suffix_metamorphism_fixtures() -> tuple[dict[str, Json], dict[str, Json]]:
    common = dict(
        start_step=1,
        configuration={"maxMarketOrdersPerTurn": 1},
        farms=[{"money": 0}, {"money": 0}],
        privates=[{"shed": {"WHEAT": 2}}, {}],
    )
    control = fixture(
        "active-prefix-control",
        steps=[
            step(pass_action([["SELL", "WHEAT", 1]]), pass_action()),
            step(pass_action(), pass_action()),
        ],
        **common,
    )
    candidate = fixture(
        "active-prefix-arbitrary-suffix",
        steps=[
            step(
                pass_action(
                    [
                        ["SELL", "WHEAT", 1],
                        ["SELL", "WHEAT", 1],
                        ["HIRE"],
                        ["BUY_PRODUCT", "FERTILIZER", 999999],
                        ["MALFORMED"],
                    ]
                ),
                pass_action(),
            ),
            step(pass_action(), pass_action()),
        ],
        **common,
    )
    return control, candidate


def current_horizon_suffix_fixtures() -> tuple[dict[str, Json], dict[str, Json]]:
    common = dict(
        start_step=100,
        configuration={"maxMarketOrdersPerTurn": 1},
        farms=[{"money": 0}, {"money": 0}],
        privates=[{}, {}],
    )
    tail = [
        step(pass_action(), pass_action()),
        step(
            {"farmer": ["PICKUP", "FERTILIZER", 1], "hands": [], "market": []},
            pass_action(),
        ),
        step({"farmer": ["DROP"], "hands": [], "market": []}, pass_action()),
    ]
    control = fixture(
        "represented-horizon-current-control",
        steps=copy.deepcopy(tail),
        **common,
    )
    candidate_steps = copy.deepcopy(tail)
    candidate_steps[0]["actions"][0]["market"] = [
        [],
        ["BUY_PRODUCT", "FERTILIZER", 1],
        ["SELL", "FERTILIZER", 1],
    ]
    control["steps"][0]["actions"][0]["market"] = [[]]
    candidate = fixture(
        "represented-horizon-current-inert-suffix",
        steps=candidate_steps,
        **common,
    )
    return control, candidate


def future_horizon_suffix_fixtures() -> tuple[dict[str, Json], dict[str, Json]]:
    common = dict(
        start_step=100,
        configuration={"maxMarketOrdersPerTurn": 1},
        farms=[{"money": 0}, {"money": 0}],
        privates=[{}, {}],
    )
    control_steps = [
        step(pass_action(), pass_action()),
        step(pass_action([[]]), pass_action()),
        step(
            {"farmer": ["PICKUP", "FERTILIZER", 1], "hands": [], "market": []},
            pass_action(),
        ),
        step({"farmer": ["DROP"], "hands": [], "market": []}, pass_action()),
    ]
    candidate_steps = copy.deepcopy(control_steps)
    candidate_steps[1]["actions"][0]["market"] = [
        [],
        ["BUY_PRODUCT", "FERTILIZER", 1],
        ["SELL", "FERTILIZER", 1],
    ]
    return (
        fixture("represented-horizon-future-control", steps=control_steps, **common),
        fixture(
            "represented-horizon-future-inert-suffix",
            steps=candidate_steps,
            **common,
        ),
    )


def unaffordable_hire_fixture() -> dict[str, Json]:
    return fixture(
        "in-prefix-unaffordable-hire",
        start_step=1,
        configuration={"maxMarketOrdersPerTurn": 1, "farmHandCostMult": 100},
        farms=[{"money": 99}, {"money": 0}],
        privates=[{}, {}],
        steps=[step(pass_action([["HIRE"]]), pass_action())],
    )


def town_funding_fixtures() -> tuple[dict[str, Json], dict[str, Json]]:
    common = dict(
        start_step=0,
        configuration={
            "maxMarketOrdersPerTurn": 1,
            "townShopSellInterval": 4,
            "townCenterSellInterval": 24,
        },
        farms=[{"money": 31}, {"money": 0}],
        privates=[{"shed": {"MILK": 1}}, {}],
        town={"unlocked_shops": ["BAKERY"] * 8},
        retain_states=False,
    )
    no_sale_steps = [step(pass_action(), pass_action()) for _ in range(23)]
    no_sale_steps[22] = step(
        pass_action([["BUY_PRODUCT", "WHEAT", 1]]), pass_action()
    )
    with_sale_steps = copy.deepcopy(no_sale_steps)
    with_sale_steps[0] = step(pass_action([["SELL", "MILK", 1]]), pass_action())
    return (
        fixture("town-funding-no-current-sale", steps=no_sale_steps, **common),
        fixture("town-funding-with-current-sale", steps=with_sale_steps, **common),
    )


def hidden_rival_receipt_fixture() -> dict[str, Json]:
    return fixture(
        "hidden-rival-receipt-and-future-cow-failure",
        start_step=1,
        configuration={"maxMarketOrdersPerTurn": 2},
        farms=[{"money": 0}, {"money": 0}],
        privates=[{"shed": {"WOOL": 2}}, {"shed": {"WOOL": 10}}],
        market={"inventory": {"WOOL": 10000}},
        steps=[
            step(
                pass_action([[], ["SELL", "WOOL", 2]]),
                pass_action([["SELL", "WOOL", 10]]),
            ),
            step(pass_action([["BUY_ANIMAL", "COW", 1]]), pass_action()),
        ],
    )


def pressure_fixture(*, candidate: bool) -> dict[str, Json]:
    own_rows = (
        [
            ["SELL", "WHEAT", 78],
            ["SELL", "MILK", 1],
            ["SELL", "WHEAT", 1],
        ]
        if candidate
        else [
            ["SELL", "WHEAT", 78],
            ["SELL", "WHEAT", 1],
            ["SELL", "MILK", 1],
        ]
    )
    rival_rows = [[], ["SELL", "WHEAT", 100], []]
    return fixture(
        "own-prefix-pressure-candidate" if candidate else "own-prefix-pressure-parent",
        start_step=1,
        configuration={"maxMarketOrdersPerTurn": 3},
        farms=[{"money": 0}, {"money": 0}],
        privates=[
            {"shed": {"WHEAT": 79, "MILK": 1}},
            {"shed": {"WHEAT": 100}},
        ],
        market={"inventory": {"WHEAT": 10066, "MILK": 9999}},
        steps=[step(pass_action(own_rows), pass_action(rival_rows))],
    )


def minimum_one_prefix_fixtures() -> tuple[dict[str, Json], dict[str, Json]]:
    common = dict(
        start_step=1,
        configuration={"maxMarketOrdersPerTurn": 0},
        farms=[{"money": 0}, {"money": 0}],
        privates=[{"shed": {"WHEAT": 2}}, {}],
    )
    return (
        fixture(
            "minimum-one-prefix-control",
            steps=[step(pass_action([["SELL", "WHEAT", 1]]), pass_action())],
            **common,
        ),
        fixture(
            "minimum-one-prefix-suffix",
            steps=[
                step(
                    pass_action(
                        [["SELL", "WHEAT", 1], ["SELL", "WHEAT", 1]]
                    ),
                    pass_action(),
                )
            ],
            **common,
        ),
    )


def hidden_affordability_fixture(
    *,
    candidate_sales: int,
    include_cow: bool,
    candidate_seat: int,
) -> dict[str, Json]:
    if candidate_sales not in (2, 3):
        raise ValueError("candidate_sales must be 2 or 3")
    if candidate_seat not in (0, 1):
        raise ValueError("candidate_seat must be 0 or 1")
    rival_seat = 1 - candidate_seat
    candidate_rows: list[Json] = [["SELL", "FERTILIZER", candidate_sales]]
    if include_cow:
        candidate_rows.append(["BUY_ANIMAL", "COW", 1])
    rival_rows: list[Json] = [
        ["SELL", "FERTILIZER", 3],
        ["BUY_ANIMAL", "COW", 1],
    ]
    actions = [pass_action(), pass_action()]
    actions[candidate_seat] = pass_action(candidate_rows)
    actions[rival_seat] = pass_action(rival_rows)
    farms = [{"money": 0}, {"money": 0}]
    farms[candidate_seat] = {"money": 142}
    farms[rival_seat] = {"money": 141}
    privates = [{"shed": {"FERTILIZER": 3}}, {"shed": {"FERTILIZER": 3}}]
    seed = 2609097306 if candidate_seat == 0 else 2609097303
    suffix = "cow" if include_cow else "sale-only"
    return fixture(
        f"hidden-affordability-sell{candidate_sales}-{suffix}-seat{candidate_seat}",
        start_step=88,
        configuration={"maxMarketOrdersPerTurn": 2},
        farms=farms,
        privates=privates,
        market={"inventory": {"FERTILIZER": 10016}},
        steps=[step(actions[0], actions[1])],
        seed=seed,
    )


def _worker(envelope: dict[str, Json]) -> dict[str, Json]:
    return envelope["worker_receipt"]


def _events(envelope: dict[str, Json], stage: str) -> list[dict[str, Json]]:
    return [
        event
        for row in _worker(envelope)["steps"]
        for event in row["events"]
        if event["stage"] == stage
    ]


def _terminal(envelope: dict[str, Json]) -> dict[str, Json]:
    return _worker(envelope)["terminal_state"]


def assert_same_official_transition(
    left: dict[str, Json], right: dict[str, Json], *, label: str
) -> dict[str, Json]:
    a = _worker(left)
    b = _worker(right)
    if a["initial_state_sha256"] != b["initial_state_sha256"]:
        raise AssertionError(f"{label}: fixtures do not share exact initial state")
    if len(a["steps"]) != len(b["steps"]):
        raise AssertionError(f"{label}: trace lengths differ")
    pairs = []
    for index, (arow, brow) in enumerate(zip(a["steps"], b["steps"])):
        if arow["active_market_prefixes_sha256"] != brow["active_market_prefixes_sha256"]:
            raise AssertionError(f"{label}: active prefixes differ at step {index}")
        if arow["post_state_sha256"] != brow["post_state_sha256"]:
            raise AssertionError(f"{label}: poststate differs at step {index}")
        pairs.append(
            {
                "step": arow["step"],
                "active_prefix_sha256": arow["active_market_prefixes_sha256"],
                "post_state_sha256": arow["post_state_sha256"],
            }
        )
    if a["terminal_state_sha256"] != b["terminal_state_sha256"]:
        raise AssertionError(f"{label}: terminal state differs")
    return {
        "label": label,
        "steps": pairs,
        "terminal_state_sha256": a["terminal_state_sha256"],
    }


def build_fixture_map() -> dict[str, dict[str, Json]]:
    suffix_control, suffix_variant = suffix_metamorphism_fixtures()
    current_control, current_variant = current_horizon_suffix_fixtures()
    future_control, future_variant = future_horizon_suffix_fixtures()
    town_no_sale, town_sale = town_funding_fixtures()
    min_control, min_variant = minimum_one_prefix_fixtures()
    return {
        "atomic_plant": atomic_plant_fixture(),
        "precommit_quote": precommit_quote_fixture(),
        "suffix_control": suffix_control,
        "suffix_variant": suffix_variant,
        "current_horizon_control": current_control,
        "current_horizon_variant": current_variant,
        "future_horizon_control": future_control,
        "future_horizon_variant": future_variant,
        "unaffordable_hire": unaffordable_hire_fixture(),
        "town_no_sale": town_no_sale,
        "town_sale": town_sale,
        "hidden_rival": hidden_rival_receipt_fixture(),
        "pressure_parent": pressure_fixture(candidate=False),
        "pressure_candidate": pressure_fixture(candidate=True),
        "minimum_one_control": min_control,
        "minimum_one_variant": min_variant,
        **{
            f"hidden_afford_s{sales}_{'cow' if cow else 'sale'}_seat{seat}":
                hidden_affordability_fixture(
                    candidate_sales=sales,
                    include_cow=cow,
                    candidate_seat=seat,
                )
            for seat in (0, 1)
            for sales, cow in ((3, True), (2, True), (3, False), (2, False))
        },
    }


def run_corpus(
    *,
    engine_path: Path,
    worker_path: Path,
    on_result: Callable[[str, dict[str, Json]], None] | None = None,
) -> tuple[dict[str, Json], dict[str, dict[str, Json]]]:
    fixtures = build_fixture_map()
    envelopes: dict[str, dict[str, Json]] = {}
    for name in sorted(fixtures):
        envelope = run_fixture(
            engine_path=engine_path,
            worker_path=worker_path,
            fixture=fixtures[name],
        )
        envelopes[name] = envelope
        if on_result is not None:
            on_result(name, envelope)

    atomic = _terminal(envelopes["atomic_plant"])
    if atomic["privates"][0]["seeds"]["WHEAT"] != 1:
        raise AssertionError("atomic PLANT consumed a seed")
    if atomic["farms"][0]["tiles"][4][4] is not None:
        raise AssertionError("atomic PLANT changed the main farmer tile")
    if atomic["farms"][0]["tiles"][4][3] is not None:
        raise AssertionError("atomic PLANT changed the hand tile")
    unit_actions = [event["action"] for event in _events(envelopes["atomic_plant"], "unit")]
    if unit_actions[:2] != [["PASS"], ["PASS"]]:
        raise AssertionError("atomic PLANT did not pre-block both requests")

    quote = _terminal(envelopes["precommit_quote"])
    quote_commits = _events(envelopes["precommit_quote"], "market_commit")
    if [quote["farms"][i]["money"] for i in (0, 1)] != [25, 25]:
        raise AssertionError("precommit quote cash mismatch")
    if [event["price"] for event in quote_commits] != [25, 25]:
        raise AssertionError("players did not receive the same precommit quote")
    if quote["market"]["inventory"]["WHEAT"] != 10002:
        raise AssertionError("precommit quote inventory mismatch")

    metamorphisms = [
        assert_same_official_transition(
            envelopes["suffix_control"],
            envelopes["suffix_variant"],
            label="arbitrary-inert-suffix",
        ),
        assert_same_official_transition(
            envelopes["current_horizon_control"],
            envelopes["current_horizon_variant"],
            label="current-represented-horizon-suffix",
        ),
        assert_same_official_transition(
            envelopes["future_horizon_control"],
            envelopes["future_horizon_variant"],
            label="future-represented-horizon-suffix",
        ),
        assert_same_official_transition(
            envelopes["minimum_one_control"],
            envelopes["minimum_one_variant"],
            label="minimum-one-market-cap",
        ),
    ]

    hire = _terminal(envelopes["unaffordable_hire"])
    hire_events = _events(envelopes["unaffordable_hire"], "market_atomic")
    if hire["farms"][0]["money"] != 99 or hire["farms"][0]["hands"]:
        raise AssertionError("unaffordable HIRE mutated cash or actor count")
    if len(hire_events) != 1 or hire_events[0]["success"] is not False:
        raise AssertionError("unaffordable HIRE ledger is not fail-closed")

    no_sale = _terminal(envelopes["town_no_sale"])
    with_sale = _terminal(envelopes["town_sale"])
    no_sale_buys = [
        event
        for event in _events(envelopes["town_no_sale"], "market_commit")
        if event["operation"] == "BUY_PRODUCT" and event["item"] == "WHEAT"
    ]
    with_sale_buys = [
        event
        for event in _events(envelopes["town_sale"], "market_commit")
        if event["operation"] == "BUY_PRODUCT" and event["item"] == "WHEAT"
    ]
    if len(no_sale_buys) != 1 or no_sale_buys[0]["price"] != 32 or no_sale_buys[0]["success"]:
        raise AssertionError("town no-sale funding predecessor mismatch")
    if len(with_sale_buys) != 1 or with_sale_buys[0]["price"] != 32 or not with_sale_buys[0]["success"]:
        raise AssertionError("town sale-funded future buy mismatch")
    if no_sale["privates"][0]["shed"]["WHEAT"] != 0:
        raise AssertionError("unfunded future WHEAT buy unexpectedly filled")
    if with_sale["privates"][0]["shed"]["WHEAT"] != 1:
        raise AssertionError("sale-funded future WHEAT buy did not fill")

    hidden = _terminal(envelopes["hidden_rival"])
    hidden_commits = _events(envelopes["hidden_rival"], "market_commit")
    own_wool_prices = [
        event["price"]
        for event in hidden_commits
        if event["player"] == 0 and event["operation"] == "SELL" and event["item"] == "WOOL"
    ]
    cow = [
        event
        for event in hidden_commits
        if event["player"] == 0 and event["operation"] == "BUY_ANIMAL"
    ]
    if own_wool_prices != [194, 193]:
        raise AssertionError(f"hidden-rival own WOOL prices mismatch: {own_wool_prices}")
    if hidden["farms"][0]["money"] != 387:
        raise AssertionError("hidden-rival own receipt must be 387")
    if len(cow) != 1 or cow[0]["price"] != 400 or cow[0]["success"]:
        raise AssertionError("387 cash must not fund the future COW")
    if hidden["privates"][0]["shed"]["COW"] != 0:
        raise AssertionError("failed COW purchase changed shed")

    parent = _terminal(envelopes["pressure_parent"])
    candidate = _terminal(envelopes["pressure_candidate"])
    parent_cash = [int(parent["farms"][i]["money"]) for i in (0, 1)]
    candidate_cash = [int(candidate["farms"][i]["money"]) for i in (0, 1)]
    if parent_cash != [1828, 2075]:
        raise AssertionError(f"pressure parent mismatch: {parent_cash}")
    if candidate_cash != [1827, 2076]:
        raise AssertionError(f"pressure candidate mismatch: {candidate_cash}")

    affordability: dict[str, Json] = {}
    expected_variants = {
        (3, True): {"cash": 31, "prices": [97, 96, 96], "cow": True},
        (2, True): {"cash": 335, "prices": [97, 96], "cow": False},
        (3, False): {"cash": 431, "prices": [97, 96, 96], "cow": False},
        (2, False): {"cash": 335, "prices": [97, 96], "cow": False},
    }
    for seat in (0, 1):
        seat_rows: dict[str, Json] = {}
        for (sales, include_cow), expected in expected_variants.items():
            key = f"hidden_afford_s{sales}_{'cow' if include_cow else 'sale'}_seat{seat}"
            envelope = envelopes[key]
            terminal = _terminal(envelope)
            commits = [
                event
                for event in _events(envelope, "market_commit")
                if event["player"] == seat
            ]
            sells = [
                event
                for event in commits
                if event["operation"] == "SELL"
                and event["item"] == "FERTILIZER"
            ]
            cows = [
                event
                for event in commits
                if event["operation"] == "BUY_ANIMAL"
                and event["item"] == "COW"
            ]
            prices = [int(event["price"]) for event in sells]
            cash = int(terminal["farms"][seat]["money"])
            acquired = terminal["privates"][seat]["shed"]["COW"] == 1
            if prices != expected["prices"]:
                raise AssertionError(
                    f"hidden-affordability seat{seat} sell{sales} prices {prices}"
                )
            if cash != expected["cash"]:
                raise AssertionError(
                    f"hidden-affordability seat{seat} sell{sales} cash {cash}"
                )
            if acquired is not expected["cow"]:
                raise AssertionError(
                    f"hidden-affordability seat{seat} sell{sales} cow {acquired}"
                )
            if include_cow:
                if len(cows) != 1 or bool(cows[0]["success"]) is not expected["cow"]:
                    raise AssertionError("hidden-affordability COW commit mismatch")
                if sells and max(event["sequence"] for event in sells) >= cows[0]["sequence"]:
                    raise AssertionError("COW debit was not ordered after sale receipts")
            elif cows:
                raise AssertionError("sale-only hidden-affordability case attempted COW")
            seat_rows[f"sell{sales}_{'cow' if include_cow else 'sale_only'}"] = {
                "seed": _worker(envelope)["seed"],
                "prices": prices,
                "sale_receipt": sum(prices),
                "terminal_cash": cash,
                "cow_acquired": acquired,
                "ordered_commit_sequences": [event["sequence"] for event in commits],
            }
        if (
            seat_rows["sell3_cow"]["terminal_cash"]
            - seat_rows["sell2_cow"]["terminal_cash"]
            != -304
        ):
            raise AssertionError("third-sale downstream-debit discontinuity is not -304")
        affordability[f"candidate_seat_{seat}"] = seat_rows

    cases = {
        name: {
            "fixture_sha256": envelope["fixture_sha256"],
            "envelope_sha256": envelope["envelope_sha256"],
            "transition_sha256": _worker(envelope)["transition_sha256"],
            "terminal_state_sha256": _worker(envelope)["terminal_state_sha256"],
        }
        for name, envelope in sorted(envelopes.items())
    }
    evidence: dict[str, Json] = {
        "schema": "titan.v3.official-transition-corpus.v1",
        "source": envelopes["atomic_plant"]["source"],
        "prior_compact_oracle": PRIOR_ORACLE,
        "cases": cases,
        "metamorphic_equalities": metamorphisms,
        "exact_witnesses": {
            "atomic_plant": {
                "remaining_wheat_seed": 1,
                "executed_unit_actions": unit_actions[:2],
            },
            "precommit_quote": {
                "cash": [25, 25],
                "prices": [25, 25],
                "ending_inventory": 10002,
            },
            "unaffordable_hire": {"money": 99, "hands": 0, "success": False},
            "town_funding": {
                "future_wheat_quote": 32,
                "without_current_sale": False,
                "with_current_sale": True,
            },
            "hidden_rival_receipt": {
                "own_wool_prices": own_wool_prices,
                "own_cash": int(hidden["farms"][0]["money"]),
                "future_cow_filled": False,
            },
            "own_prefix_pressure": {
                "parent_cash": parent_cash,
                "candidate_cash": candidate_cash,
                "own_delta": candidate_cash[0] - parent_cash[0],
                "rival_delta": candidate_cash[1] - parent_cash[1],
            },
            "hidden_affordability_discontinuity": affordability,
        },
        "all_contracts_passed": True,
    }
    evidence["evidence_sha256"] = semantic_hash(evidence)
    return evidence, envelopes
