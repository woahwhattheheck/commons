"""Per-candidate terminal payback admission for TITAN P22.

The official Kaggriculture configuration records 720 episode steps and its
interpreter settles when the previous step reaches ``episodeSteps - 2``. At
that point reward is actual farm money: irreversible assets and unfinished
production receive no terminal credit.

This helper deliberately does *not* choose a global early/mid/late mode.
Instead each represented candidate supplies executable completion events. New
investment is admitted only when at least one complete event can be liquidated
by the true terminal boundary and the conservative value of all represented
complete events strictly exceeds the candidate's remaining incremental cost.
Already-sunk productive assets are evaluated on remaining service cost only, so
closing new investment does not accidentally abandon a still-profitable final
harvest/feed/deposit/sale chain.

The caller owns path feasibility, market quotes, rival scenarios, and event
construction. This module never invents future shop unlocks, future prices, or
hidden rival state.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Literal, Sequence

DEFAULT_EPISODE_STEPS = 720
CandidateKind = Literal["new_investment", "sunk_service"]
EconomicMode = Literal["invest", "service", "liquidate"]


@dataclass(frozen=True)
class CompletionEvent:
    """One distinct represented production-to-cash completion."""

    event_id: str
    ready_step: int
    delivery_step: int
    sale_step: int
    gross_value: float
    incremental_cost: float = 0.0


@dataclass(frozen=True)
class TerminalCandidate:
    """A candidate commitment evaluated only on remaining executable value."""

    name: str
    kind: CandidateKind
    events: Sequence[CompletionEvent]
    entry_cost: float = 0.0


@dataclass(frozen=True)
class TerminalDecision:
    """Auditable per-candidate horizon result."""

    candidate: str
    mode: EconomicMode
    terminal_step: int
    complete_event_ids: tuple[str, ...]
    incomplete_event_ids: tuple[str, ...]
    gross_value: float
    remaining_cost: float
    net_value: float
    reason: str


def terminal_decision_step(episode_steps: int = DEFAULT_EPISODE_STEPS) -> int:
    """Return the final prior-step value whose interpreter call settles cash."""

    steps = int(episode_steps)
    if steps < 2:
        raise ValueError("episode_steps must be at least 2")
    return steps - 2


def _finite_nonnegative(value: float, name: str) -> float:
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return out


def _validated_events(
    events: Iterable[CompletionEvent],
    *,
    current_step: int,
) -> tuple[CompletionEvent, ...]:
    seen: set[str] = set()
    validated: list[CompletionEvent] = []
    for event in events:
        event_id = str(event.event_id)
        if not event_id:
            raise ValueError("event_id must be non-empty")
        if event_id in seen:
            raise ValueError(f"duplicate event_id: {event_id}")
        seen.add(event_id)

        ready = int(event.ready_step)
        delivery = int(event.delivery_step)
        sale = int(event.sale_step)
        if ready < current_step:
            raise ValueError(f"{event_id}: ready_step precedes current_step")
        if not (ready <= delivery <= sale):
            raise ValueError(f"{event_id}: require ready_step <= delivery_step <= sale_step")
        _finite_nonnegative(event.gross_value, f"{event_id}.gross_value")
        _finite_nonnegative(event.incremental_cost, f"{event_id}.incremental_cost")
        validated.append(event)
    return tuple(validated)


def evaluate_candidate(
    candidate: TerminalCandidate,
    *,
    current_step: int,
    episode_steps: int = DEFAULT_EPISODE_STEPS,
    minimum_net: float = 0.0,
) -> TerminalDecision:
    """Classify one candidate as invest, service, or liquidate.

    Complete event value is credited only when the whole represented chain
    reaches its sale step by the exact terminal boundary. Incomplete event
    gross_value and event-specific cost are both excluded because the decision
    is to not start that unreachable completion. ``entry_cost`` is charged only
    for new irreversible investment; sunk capital cannot bias remaining service.

    Admission is strict: ``net_value`` must exceed ``minimum_net``. Exact ties
    therefore preserve the caller's canonical/no-new-commitment behavior.
    """

    current = int(current_step)
    terminal = terminal_decision_step(episode_steps)
    if current < 0:
        raise ValueError("current_step must be non-negative")
    threshold = float(minimum_net)
    if not math.isfinite(threshold):
        raise ValueError("minimum_net must be finite")
    if candidate.kind not in ("new_investment", "sunk_service"):
        raise ValueError("kind must be 'new_investment' or 'sunk_service'")

    entry_cost = _finite_nonnegative(candidate.entry_cost, "entry_cost")
    if candidate.kind == "sunk_service" and entry_cost != 0:
        raise ValueError("sunk_service entry_cost must be zero; sunk capital has no terminal credit")

    # Once settlement is reached there is no future commitment to validate or
    # credit. Returning immediately also prevents a stale pre-terminal event
    # description from masquerading as a new post-terminal obligation.
    if current > terminal:
        return TerminalDecision(
            candidate=str(candidate.name),
            mode="liquidate",
            terminal_step=terminal,
            complete_event_ids=(),
            incomplete_event_ids=tuple(str(event.event_id) for event in candidate.events),
            gross_value=0.0,
            remaining_cost=0.0,
            net_value=0.0,
            reason="terminal boundary already reached",
        )

    events = _validated_events(candidate.events, current_step=current)
    complete = tuple(event for event in events if event.sale_step <= terminal)
    incomplete = tuple(event for event in events if event.sale_step > terminal)

    gross = sum(float(event.gross_value) for event in complete)
    event_cost = sum(float(event.incremental_cost) for event in complete)
    remaining_cost = event_cost + (entry_cost if candidate.kind == "new_investment" else 0.0)
    net = gross - remaining_cost

    if not complete:
        mode: EconomicMode = "liquidate"
        reason = "no represented completion can liquidate by terminal step"
    elif net <= threshold:
        mode = "liquidate"
        reason = "complete represented events do not clear conservative remaining cost"
    elif candidate.kind == "new_investment":
        mode = "invest"
        reason = "new commitment has strictly positive executable terminal net value"
    else:
        mode = "service"
        reason = "sunk asset has strictly positive remaining executable service value"

    return TerminalDecision(
        candidate=str(candidate.name),
        mode=mode,
        terminal_step=terminal,
        complete_event_ids=tuple(event.event_id for event in complete),
        incomplete_event_ids=tuple(event.event_id for event in incomplete),
        gross_value=gross,
        remaining_cost=remaining_cost,
        net_value=net,
        reason=reason,
    )


def compare_candidates(
    candidates: Sequence[TerminalCandidate],
    *,
    current_step: int,
    episode_steps: int = DEFAULT_EPISODE_STEPS,
    minimum_net: float = 0.0,
) -> tuple[TerminalDecision, ...]:
    """Evaluate independently so one global calendar cutoff cannot mask differences."""

    return tuple(
        evaluate_candidate(
            candidate,
            current_step=current_step,
            episode_steps=episode_steps,
            minimum_net=minimum_net,
        )
        for candidate in candidates
    )
