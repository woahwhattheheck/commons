"""Fail-closed P03 completion and payback certificate.

The canonical fourth-quadrant producer remains the only route generator.  This
module evaluates a represented route and materializes candidate-only config
variants; it never invents an order, a quote, or future cash.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

EPISODE_STEPS = 720
LAST_SETTLED_STEP = EPISODE_STEPS - 2


@dataclass(frozen=True)
class CostLedger:
    land: int
    seed: int
    labor: int
    service: int

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    @property
    def total(self) -> int:
        return self.land + self.seed + self.labor + self.service


@dataclass(frozen=True)
class ProjectedChain:
    start_step: int
    buy_land_step: int
    buy_seed_step: int
    plant_step: int
    service_steps: tuple[int, ...]
    harvest_step: int
    deposit_step: int
    sale_step: int
    units_sold: int
    observed_unit_quote: int
    quote_observed_step: int
    observed_cash: int
    cash_reserve: int
    costs: CostLedger
    product: str = "WHEAT"

    def __post_init__(self) -> None:
        numeric = {
            "start_step": self.start_step,
            "buy_land_step": self.buy_land_step,
            "buy_seed_step": self.buy_seed_step,
            "plant_step": self.plant_step,
            "harvest_step": self.harvest_step,
            "deposit_step": self.deposit_step,
            "sale_step": self.sale_step,
            "units_sold": self.units_sold,
            "observed_unit_quote": self.observed_unit_quote,
            "quote_observed_step": self.quote_observed_step,
            "observed_cash": self.observed_cash,
            "cash_reserve": self.cash_reserve,
        }
        for name, value in numeric.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if any(isinstance(step, bool) or not isinstance(step, int) for step in self.service_steps):
            raise ValueError("service_steps must contain integers")
        if not isinstance(self.product, str) or not self.product.strip():
            raise ValueError("product must be a non-empty string")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProjectedChain":
        raw = dict(value)
        costs = raw.get("costs")
        if not isinstance(costs, Mapping):
            raise ValueError("costs must be an object")
        raw["costs"] = CostLedger(**dict(costs))
        raw["service_steps"] = tuple(raw.get("service_steps", ()))
        return cls(**raw)

    def canonical_payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["service_steps"] = list(self.service_steps)
        return value

    @property
    def digest(self) -> str:
        payload = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class CompletionCertificate:
    admitted: bool
    reason: str
    gross_terminal_proceeds: int
    incremental_cost: int
    net_terminal_value: int
    required_prefunding: int
    last_settled_step: int
    chain_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateVariant:
    variant_id: str
    cash_reserve: int
    max_start_day: int
    product: str = "WHEAT"
    amount: int = 13

    def __post_init__(self) -> None:
        if self.cash_reserve < 0:
            raise ValueError("cash_reserve must be non-negative")
        if self.max_start_day < 0:
            raise ValueError("max_start_day must be non-negative")
        if self.amount <= 0:
            raise ValueError("amount must be positive")


_VARIANTS = tuple(
    CandidateVariant(
        variant_id=f"fq-r{reserve}-d{day}",
        cash_reserve=reserve,
        max_start_day=day,
    )
    for day in (8, 12)
    for reserve in (6000, 7500, 9000)
)


def candidate_variants() -> tuple[CandidateVariant, ...]:
    """Return the immutable six-cell candidate grid."""
    return _VARIANTS


def _decline(chain: ProjectedChain, reason: str) -> CompletionCertificate:
    gross = max(0, chain.units_sold) * max(0, chain.observed_unit_quote)
    total = chain.costs.total
    return CompletionCertificate(
        admitted=False,
        reason=reason,
        gross_terminal_proceeds=gross,
        incremental_cost=total,
        net_terminal_value=gross - total,
        required_prefunding=total + max(0, chain.cash_reserve),
        last_settled_step=LAST_SETTLED_STEP,
        chain_digest=chain.digest,
    )


def certify_completion(
    chain: ProjectedChain,
    *,
    min_net_gain: int = 1,
    last_settled_step: int = LAST_SETTLED_STEP,
) -> CompletionCertificate:
    """Certify one represented land-to-cash chain.

    Admission is deliberately conservative.  The route must already represent
    every physical/economic phase and current observed cash must pay every
    incremental cost plus reserve without using the projected sale receipt.
    """
    if isinstance(min_net_gain, bool) or not isinstance(min_net_gain, int) or min_net_gain < 1:
        raise ValueError("min_net_gain must be a positive integer")
    if chain.start_step < 0:
        return _decline(chain, "negative_start_step")
    if chain.start_step > chain.buy_land_step or chain.start_step > chain.buy_seed_step:
        return _decline(chain, "acquisition_precedes_candidate_start")
    if chain.buy_land_step >= chain.plant_step:
        return _decline(chain, "land_not_owned_before_productive_action")
    if chain.buy_seed_step >= chain.plant_step:
        return _decline(chain, "seed_not_owned_before_plant")
    if chain.costs.land <= 0:
        return _decline(chain, "missing_incremental_land_cost")
    if chain.costs.seed <= 0:
        return _decline(chain, "missing_incremental_seed_cost")
    if chain.units_sold <= 0:
        return _decline(chain, "no_completed_units")
    if chain.observed_unit_quote <= 0:
        return _decline(chain, "missing_positive_observed_quote")
    if chain.quote_observed_step > chain.start_step:
        return _decline(chain, "future_or_unobserved_quote")
    if not chain.service_steps:
        return _decline(chain, "missing_service_chain")
    if tuple(sorted(chain.service_steps)) != chain.service_steps:
        return _decline(chain, "service_steps_not_ordered")
    if any(step < chain.plant_step or step >= chain.harvest_step for step in chain.service_steps):
        return _decline(chain, "service_outside_productive_interval")
    if not (
        chain.plant_step
        < chain.harvest_step
        < chain.deposit_step
        < chain.sale_step
    ):
        return _decline(chain, "physical_completion_order_invalid")
    if chain.sale_step > last_settled_step:
        return _decline(chain, "sale_after_terminal_settlement")
    if chain.observed_cash < 0 or chain.cash_reserve < 0:
        return _decline(chain, "negative_cash_or_reserve")

    required = chain.costs.total + chain.cash_reserve
    if chain.observed_cash < required:
        return _decline(chain, "not_prefunded_without_future_sale")

    gross = chain.units_sold * chain.observed_unit_quote
    net = gross - chain.costs.total
    if gross <= chain.costs.total:
        return _decline(chain, "terminal_value_does_not_exceed_incremental_cost")
    if net < min_net_gain:
        return _decline(chain, "net_gain_below_required_minimum")

    return CompletionCertificate(
        admitted=True,
        reason="complete_prefunded_profitable_chain",
        gross_terminal_proceeds=gross,
        incremental_cost=chain.costs.total,
        net_terminal_value=net,
        required_prefunding=required,
        last_settled_step=last_settled_step,
        chain_digest=chain.digest,
    )


def latest_safe_start_day(
    *,
    productive_latency_steps: int,
    market_settlement_step: int = LAST_SETTLED_STEP,
    steps_per_day: int = 24,
) -> int:
    """Return the last day whose first step can finish the declared chain."""
    if productive_latency_steps < 0 or steps_per_day <= 0:
        raise ValueError("invalid latency or steps_per_day")
    latest_step = market_settlement_step - productive_latency_steps
    if latest_step < 0:
        return -1
    return latest_step // steps_per_day


def patch_titan_config(
    config: Mapping[str, Any], variant: CandidateVariant
) -> dict[str, Any]:
    """Enable only the existing P03 seam and tune its declared leaves."""
    patched = deepcopy(dict(config))
    ledger = patched.setdefault("feature_ledger", {})
    runtime = ledger.setdefault("runtime_features", {})
    runtime["fourth_quadrant"] = True
    fourth = patched.setdefault("fourth_quadrant", {})
    fourth["amount"] = variant.amount
    fourth["cash_reserve"] = variant.cash_reserve
    fourth["max_start_day"] = variant.max_start_day
    fourth["product"] = variant.product
    return patched


def _json_leaf_deltas(before: Any, after: Any, prefix: str = "") -> list[str]:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        result: list[str] = []
        keys = sorted(set(before) | set(after))
        for key in keys:
            child = f"{prefix}/{key}"
            if key not in before or key not in after:
                result.append(child)
            else:
                result.extend(_json_leaf_deltas(before[key], after[key], child))
        return result
    if before != after:
        return [prefix or "/"]
    return []


_ALLOWED_CONFIG_DELTAS = {
    "/feature_ledger/runtime_features/fourth_quadrant",
    "/fourth_quadrant/amount",
    "/fourth_quadrant/cash_reserve",
    "/fourth_quadrant/max_start_day",
    "/fourth_quadrant/product",
}


def assert_candidate_only_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    deltas = _json_leaf_deltas(before, after)
    unexpected = sorted(set(deltas) - _ALLOWED_CONFIG_DELTAS)
    if unexpected:
        raise ValueError(f"unexpected candidate config deltas: {unexpected}")
    if "/feature_ledger/runtime_features/fourth_quadrant" not in deltas:
        raise ValueError("candidate did not enable fourth_quadrant")
    return deltas


def certificates_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[CompletionCertificate]:
    return [certify_completion(ProjectedChain.from_mapping(row)) for row in rows]
