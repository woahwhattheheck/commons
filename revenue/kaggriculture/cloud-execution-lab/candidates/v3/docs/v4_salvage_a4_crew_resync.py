# SPDX-License-Identifier: Apache-2.0
"""TITAN V4 salvage theorem: crew-owned queues must follow crew membership.

This is the reusable correctness invariant recovered from the V3.1 A4 lane at
7f244af80fb2b770f270a333759f8d1d188753ef.  It deliberately carries no melon
economics, HIRE policy, market mutation, feature key, or default change.

A controller that builds per-worker jobs once per day can strand a hand hired
later in that same day.  Record the exact crew tuple used for the last build and
rebuild whenever the current crew tuple changes.  Consumers should call
``crew_jobs_stale`` immediately before their existing job builder, then record
``jobs_built_day`` and ``jobs_built_crew`` after a successful build.
"""
from __future__ import annotations


def _strict_crew(value):
    """Return a canonical worker-index tuple, or ``None`` for malformed input."""
    if not isinstance(value, (list, tuple)):
        return None
    out = []
    seen = set()
    for worker in value:
        if type(worker) is not int or worker < 0 or worker in seen:
            return None
        out.append(worker)
        seen.add(worker)
    return tuple(out)


def crew_jobs_stale(state, *, day, crew):
    """Whether an existing per-day queue build is stale for ``crew``.

    Malformed controller inputs fail closed to ``False`` so this proof helper
    cannot independently create gameplay.  Missing/invalid *build metadata*
    for an otherwise valid active crew is treated as stale: the safe action is
    to let the owning controller rebuild its own queues rather than reuse an
    unproven ownership assignment.
    """
    if not isinstance(state, dict) or type(day) is not int or day < 0:
        return False
    current = _strict_crew(crew)
    if current is None or not current:
        return False

    built_day = state.get("jobs_built_day")
    built_crew = _strict_crew(state.get("jobs_built_crew", ()))
    if type(built_day) is not int or built_day < 0 or built_crew is None:
        return True
    return built_day != day or built_crew != current


def mark_crew_jobs_built(state, *, day, crew):
    """Record queue ownership after the owning controller successfully builds."""
    if not isinstance(state, dict) or type(day) is not int or day < 0:
        return False
    current = _strict_crew(crew)
    if current is None or not current:
        return False
    state["jobs_built_day"] = day
    state["jobs_built_crew"] = current
    return True
