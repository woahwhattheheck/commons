from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

SCENARIO_SCHEMA = "darpa-dv026-market-scenario/v1"
OBSERVATION_SCHEMA = "darpa-dv026-black-box-observation/v1"
RECEIPT_SCHEMA = "darpa-dv026-market-poc-receipt/v1"
ROLES = {"BUYER", "SELLER"}
SIDES = {"BUY", "SELL"}
ADAPTER_KINDS = {"SYNTHETIC_STUB", "EXTERNAL_BLACK_BOX"}
MECHANISMS = {"CONTINUOUS_DOUBLE_AUCTION", "UNIFORM_PRICE_CALL"}
MAX_PARTICIPANTS = 200
MAX_NEWS_EVENTS = 100
MAX_QUANTITY = 1_000
MAX_TOTAL_UNITS = 10_000
DEFAULT_EFFICIENCY_THRESHOLD_BPS = 9_000


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class Participant:
    participant_id: str
    role: str
    reservation_minor: int
    quantity: int
    model_id: str
    adapter_kind: str


@dataclass(frozen=True)
class NewsEvent:
    seq: int
    headline: str
    buyer_value_delta_minor: int
    seller_cost_delta_minor: int


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    asset: str
    participants: tuple[Participant, ...]
    news: tuple[NewsEvent, ...]


@dataclass(frozen=True)
class Order:
    participant_id: str
    side: str
    price_minor: int
    quantity: int


@dataclass(frozen=True)
class Trade:
    buyer_id: str
    seller_id: str
    price_minor: int
    quantity: int = 1


class AgentAdapter(Protocol):
    model_id: str
    adapter_kind: str

    def decide(self, observation: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _object(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError(f"{name} must be an object")
    return value


def _exact_keys(obj: Mapping[str, Any], keys: set[str], name: str) -> None:
    actual = set(obj)
    if actual != keys:
        raise ContractError(
            f"{name} keys mismatch missing={sorted(keys - actual)} extra={sorted(actual - keys)}"
        )


def _text(value: Any, name: str, *, maximum: int = 256) -> str:
    if type(value) is not str or not value or value != value.strip() or len(value) > maximum:
        raise ContractError(f"{name} must be non-empty trimmed text <= {maximum}")
    if any(ord(ch) < 32 for ch in value):
        raise ContractError(f"{name} contains control characters")
    return value


def _integer(value: Any, name: str, *, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ContractError(f"{name} must be an integer in [{low}, {high}]")
    return value


def parse_scenario(value: Any) -> Scenario:
    root = _object(value, "scenario")
    _exact_keys(root, {"schema", "scenario_id", "asset", "participants", "news"}, "scenario")
    if root["schema"] != SCENARIO_SCHEMA:
        raise ContractError(f"scenario.schema must equal {SCENARIO_SCHEMA}")

    raw_participants = root["participants"]
    if type(raw_participants) is not list or not 2 <= len(raw_participants) <= MAX_PARTICIPANTS:
        raise ContractError(f"scenario.participants must contain 2..{MAX_PARTICIPANTS} entries")

    participants: list[Participant] = []
    ids: set[str] = set()
    total_units = 0
    for index, raw in enumerate(raw_participants):
        obj = _object(raw, f"participants[{index}]")
        _exact_keys(
            obj,
            {"participant_id", "role", "reservation_minor", "quantity", "model_id", "adapter_kind"},
            f"participants[{index}]",
        )
        participant_id = _text(obj["participant_id"], f"participants[{index}].participant_id", maximum=96)
        if participant_id in ids:
            raise ContractError(f"duplicate participant_id: {participant_id}")
        ids.add(participant_id)
        role = _text(obj["role"], f"participants[{index}].role", maximum=6)
        if role not in ROLES:
            raise ContractError(f"participants[{index}].role must be BUYER or SELLER")
        reservation = _integer(
            obj["reservation_minor"],
            f"participants[{index}].reservation_minor",
            low=0,
            high=10**12,
        )
        quantity = _integer(
            obj["quantity"], f"participants[{index}].quantity", low=1, high=MAX_QUANTITY
        )
        total_units += quantity
        model_id = _text(obj["model_id"], f"participants[{index}].model_id", maximum=160)
        adapter_kind = _text(obj["adapter_kind"], f"participants[{index}].adapter_kind", maximum=32)
        if adapter_kind not in ADAPTER_KINDS:
            raise ContractError(
                f"participants[{index}].adapter_kind must be one of {sorted(ADAPTER_KINDS)}"
            )
        participants.append(
            Participant(participant_id, role, reservation, quantity, model_id, adapter_kind)
        )

    if total_units > MAX_TOTAL_UNITS:
        raise ContractError(f"participant units exceed {MAX_TOTAL_UNITS}")

    raw_news = root["news"]
    if type(raw_news) is not list or len(raw_news) > MAX_NEWS_EVENTS:
        raise ContractError(f"scenario.news must be a list with <= {MAX_NEWS_EVENTS} events")
    news: list[NewsEvent] = []
    expected_seq = 1
    for index, raw in enumerate(raw_news):
        obj = _object(raw, f"news[{index}]")
        _exact_keys(
            obj,
            {"seq", "headline", "buyer_value_delta_minor", "seller_cost_delta_minor"},
            f"news[{index}]",
        )
        seq = _integer(obj["seq"], f"news[{index}].seq", low=1, high=MAX_NEWS_EVENTS)
        if seq != expected_seq:
            raise ContractError("news.seq must be contiguous and start at 1")
        expected_seq += 1
        news.append(
            NewsEvent(
                seq=seq,
                headline=_text(obj["headline"], f"news[{index}].headline", maximum=500),
                buyer_value_delta_minor=_integer(
                    obj["buyer_value_delta_minor"],
                    f"news[{index}].buyer_value_delta_minor",
                    low=-(10**12),
                    high=10**12,
                ),
                seller_cost_delta_minor=_integer(
                    obj["seller_cost_delta_minor"],
                    f"news[{index}].seller_cost_delta_minor",
                    low=-(10**12),
                    high=10**12,
                ),
            )
        )

    scenario = Scenario(
        scenario_id=_text(root["scenario_id"], "scenario.scenario_id", maximum=128),
        asset=_text(root["asset"], "scenario.asset", maximum=128),
        participants=tuple(participants),
        news=tuple(news),
    )
    for participant in scenario.participants:
        effective_reservation(scenario, participant)
    return scenario


def scenario_to_dict(scenario: Scenario) -> dict[str, Any]:
    return {
        "schema": SCENARIO_SCHEMA,
        "scenario_id": scenario.scenario_id,
        "asset": scenario.asset,
        "participants": [
            {
                "participant_id": p.participant_id,
                "role": p.role,
                "reservation_minor": p.reservation_minor,
                "quantity": p.quantity,
                "model_id": p.model_id,
                "adapter_kind": p.adapter_kind,
            }
            for p in scenario.participants
        ],
        "news": [
            {
                "seq": event.seq,
                "headline": event.headline,
                "buyer_value_delta_minor": event.buyer_value_delta_minor,
                "seller_cost_delta_minor": event.seller_cost_delta_minor,
            }
            for event in scenario.news
        ],
    }


def effective_reservation(scenario: Scenario, participant: Participant) -> int:
    if participant.role == "BUYER":
        delta = sum(event.buyer_value_delta_minor for event in scenario.news)
    else:
        delta = sum(event.seller_cost_delta_minor for event in scenario.news)
    result = participant.reservation_minor + delta
    if not 0 <= result <= 10**12:
        raise ContractError(
            f"news-adjusted reservation out of range for participant {participant.participant_id}"
        )
    return result


def build_observation(scenario: Scenario, participant: Participant) -> dict[str, Any]:
    return {
        "schema": OBSERVATION_SCHEMA,
        "scenario_id": scenario.scenario_id,
        "asset": scenario.asset,
        "participant_id": participant.participant_id,
        "role": participant.role,
        "reservation_minor": effective_reservation(scenario, participant),
        "quantity": participant.quantity,
        "public_news": [
            {
                "seq": event.seq,
                "headline": event.headline,
                "buyer_value_delta_minor": event.buyer_value_delta_minor,
                "seller_cost_delta_minor": event.seller_cost_delta_minor,
            }
            for event in scenario.news
        ],
    }


def _parse_order(value: Any, name: str) -> Order:
    obj = _object(value, name)
    _exact_keys(obj, {"participant_id", "side", "price_minor", "quantity"}, name)
    side = _text(obj["side"], f"{name}.side", maximum=4)
    if side not in SIDES:
        raise ContractError(f"{name}.side must be BUY or SELL")
    return Order(
        participant_id=_text(obj["participant_id"], f"{name}.participant_id", maximum=96),
        side=side,
        price_minor=_integer(obj["price_minor"], f"{name}.price_minor", low=0, high=10**12),
        quantity=_integer(obj["quantity"], f"{name}.quantity", low=1, high=MAX_QUANTITY),
    )


def parse_orders(scenario: Scenario, value: Any) -> tuple[Order, ...]:
    if type(value) is not list:
        raise ContractError("orders must be a list")
    participants = {p.participant_id: p for p in scenario.participants}
    seen: set[str] = set()
    orders: list[Order] = []
    total = 0
    for index, raw in enumerate(value):
        order = _parse_order(raw, f"orders[{index}]")
        participant = participants.get(order.participant_id)
        if participant is None:
            raise ContractError(f"unknown participant_id in orders: {order.participant_id}")
        if order.participant_id in seen:
            raise ContractError(f"duplicate order for participant: {order.participant_id}")
        seen.add(order.participant_id)
        expected_side = "BUY" if participant.role == "BUYER" else "SELL"
        if order.side != expected_side:
            raise ContractError(
                f"order side {order.side} conflicts with participant role {participant.role}"
            )
        if order.quantity > participant.quantity:
            raise ContractError(
                f"order quantity exceeds participant capacity: {order.participant_id}"
            )
        total += order.quantity
        orders.append(order)
    if total > MAX_TOTAL_UNITS:
        raise ContractError(f"order units exceed {MAX_TOTAL_UNITS}")
    return tuple(orders)


def collect_black_box_orders(
    scenario: Scenario, adapters: Mapping[str, AgentAdapter]
) -> tuple[Order, ...]:
    responses: list[Mapping[str, Any]] = []
    for participant in sorted(scenario.participants, key=lambda p: p.participant_id):
        adapter = adapters.get(participant.participant_id)
        if adapter is None:
            continue
        if getattr(adapter, "model_id", None) != participant.model_id:
            raise ContractError(f"adapter model_id mismatch for {participant.participant_id}")
        if getattr(adapter, "adapter_kind", None) != participant.adapter_kind:
            raise ContractError(f"adapter kind mismatch for {participant.participant_id}")
        response = adapter.decide(build_observation(scenario, participant))
        responses.append(response)
    return parse_orders(scenario, responses)


@dataclass(frozen=True)
class _UnitOrder:
    participant_id: str
    price_minor: int
    unit_index: int


def _unit_books(orders: Sequence[Order]) -> tuple[list[_UnitOrder], list[_UnitOrder]]:
    buys: list[_UnitOrder] = []
    sells: list[_UnitOrder] = []
    for order in orders:
        target = buys if order.side == "BUY" else sells
        target.extend(
            _UnitOrder(order.participant_id, order.price_minor, unit)
            for unit in range(order.quantity)
        )
    buys.sort(key=lambda item: (-item.price_minor, item.participant_id, item.unit_index))
    sells.sort(key=lambda item: (item.price_minor, item.participant_id, item.unit_index))
    return buys, sells


def clear_market(orders: Sequence[Order], mechanism: str) -> tuple[Trade, ...]:
    if mechanism not in MECHANISMS:
        raise ContractError(f"mechanism must be one of {sorted(MECHANISMS)}")
    buys, sells = _unit_books(orders)
    crossing = 0
    for buy, sell in zip(buys, sells):
        if buy.price_minor < sell.price_minor:
            break
        crossing += 1
    if crossing == 0:
        return ()

    if mechanism == "UNIFORM_PRICE_CALL":
        uniform_price = (
            buys[crossing - 1].price_minor + sells[crossing - 1].price_minor
        ) // 2
    else:
        uniform_price = None

    trades: list[Trade] = []
    for index in range(crossing):
        buy = buys[index]
        sell = sells[index]
        price = (
            uniform_price
            if uniform_price is not None
            else (buy.price_minor + sell.price_minor) // 2
        )
        trades.append(Trade(buy.participant_id, sell.participant_id, price, 1))
    return tuple(trades)


def _optimal_surplus(scenario: Scenario) -> int:
    buyers: list[tuple[int, str, int]] = []
    sellers: list[tuple[int, str, int]] = []
    for participant in scenario.participants:
        value = effective_reservation(scenario, participant)
        target = buyers if participant.role == "BUYER" else sellers
        target.extend((value, participant.participant_id, unit) for unit in range(participant.quantity))
    buyers.sort(key=lambda item: (-item[0], item[1], item[2]))
    sellers.sort(key=lambda item: (item[0], item[1], item[2]))
    surplus = 0
    for buyer, seller in zip(buyers, sellers):
        delta = buyer[0] - seller[0]
        if delta <= 0:
            break
        surplus += delta
    return surplus


def _realized_surplus(scenario: Scenario, trades: Sequence[Trade]) -> int:
    participants = {p.participant_id: p for p in scenario.participants}
    surplus = 0
    for trade in trades:
        buyer = participants[trade.buyer_id]
        seller = participants[trade.seller_id]
        surplus += effective_reservation(scenario, buyer) - effective_reservation(scenario, seller)
    return surplus


def model_panel_receipt(scenario: Scenario) -> dict[str, Any]:
    distinct = sorted({p.model_id for p in scenario.participants})
    external = sorted(
        {p.model_id for p in scenario.participants if p.adapter_kind == "EXTERNAL_BLACK_BOX"}
    )
    synthetic = sorted(
        {p.model_id for p in scenario.participants if p.adapter_kind == "SYNTHETIC_STUB"}
    )
    return {
        "distinct_model_ids": distinct,
        "distinct_model_count": len(distinct),
        "external_black_box_model_ids": external,
        "external_black_box_model_count": len(external),
        "synthetic_stub_model_ids": synthetic,
        "ten_distinct_external_model_contract_met": len(external) >= 10,
        "ten_llm_milestone_claimed": False,
    }


def evaluate(
    scenario: Scenario,
    orders: Sequence[Order],
    *,
    mechanism: str,
    efficiency_threshold_bps: int = DEFAULT_EFFICIENCY_THRESHOLD_BPS,
) -> dict[str, Any]:
    if type(efficiency_threshold_bps) is not int or not 0 <= efficiency_threshold_bps <= 10_000:
        raise ContractError("efficiency_threshold_bps must be an integer in [0, 10000]")
    trades = clear_market(orders, mechanism)
    optimal = _optimal_surplus(scenario)
    realized = _realized_surplus(scenario, trades)
    if optimal == 0:
        efficiency_bps = 10_000 if realized == 0 else 0
    else:
        efficiency_bps = (realized * 10_000) // optimal

    panel = model_panel_receipt(scenario)
    scenario_dict = scenario_to_dict(scenario)
    order_dicts = [
        {
            "participant_id": order.participant_id,
            "side": order.side,
            "price_minor": order.price_minor,
            "quantity": order.quantity,
        }
        for order in orders
    ]
    trade_dicts = [
        {
            "buyer_id": trade.buyer_id,
            "seller_id": trade.seller_id,
            "price_minor": trade.price_minor,
            "quantity": trade.quantity,
        }
        for trade in trades
    ]
    news_dicts = scenario_dict["news"]
    core = {
        "schema": RECEIPT_SCHEMA,
        "scenario_id": scenario.scenario_id,
        "asset": scenario.asset,
        "mechanism": mechanism,
        "scenario_sha256": digest(scenario_dict),
        "orders_sha256": digest(order_dicts),
        "public_news_sha256": digest(news_dicts),
        "trades": trade_dicts,
        "trade_count": len(trades),
        "realized_surplus_minor": realized,
        "optimal_surplus_minor": optimal,
        "allocative_efficiency_bps": efficiency_bps,
        "efficiency_threshold_bps": efficiency_threshold_bps,
        "efficiency_gate_pass": efficiency_bps >= efficiency_threshold_bps,
        "model_panel": panel,
        "claim_ceiling": {
            "phase_i_complete": False,
            "direct_to_phase_ii_ready": False,
            "ten_llm_milestone_satisfied": False,
            "darpa_submission_made": False,
            "award_or_revenue_earned": False,
        },
        "external_authority": {
            "network_call": False,
            "model_provider_call": False,
            "sponsor_contact": False,
            "proposal_submission": False,
            "registration_or_signature": False,
            "spend": False,
        },
    }
    receipt = dict(core)
    receipt["receipt_sha256"] = digest(core)
    return receipt


def verify_receipt(
    scenario: Scenario,
    orders: Sequence[Order],
    receipt: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    try:
        mechanism = receipt["mechanism"]
        threshold = receipt["efficiency_threshold_bps"]
        expected = evaluate(
            scenario,
            orders,
            mechanism=mechanism,
            efficiency_threshold_bps=threshold,
        )
    except (KeyError, ContractError):
        return False
    return receipt == expected
