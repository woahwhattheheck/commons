"""Canonical task operations over the existing atomic Commons claims branch.

The shared command center and CLI call this same reducer. Provider collection is
bounded and separate from the compare-and-write, so a ref race never repeats an
external provider request. A stale read can inform a screen, never grant custody.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .identity import task_key
from .projector import _landed_artifact, _merged, _time, normalize_equivalent, project
from .routing import context_bundle, route, select_tasks, status
from .store import GitStore

TERMINAL = {"SHIPPED", "BLOCKED", "SUPERSEDED", "ABANDONED"}


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def seat_map(payload):
    if isinstance(payload, list):
        return {str(row.get("seat") or row.get("id")): row for row in payload
                if isinstance(row, dict) and (row.get("seat") or row.get("id"))}
    if isinstance(payload, dict):
        if isinstance(payload.get("seats"), list):
            result = seat_map(payload["seats"])
            for row in payload.get("roster", []):
                if isinstance(row, dict) and row.get("seat") not in result:
                    result[str(row["seat"])] = row
            return result
        return {str(k): v for k, v in payload.items() if isinstance(v, dict)}
    return {}


def _seats(state):
    result = seat_map(state.get("seats", {}))
    for name, worker in state.get("workers", {}).items():
        old = result.get(name, {})
        declared = dict(old.get("declared") or old)
        observed, previous = _time(worker.get("heartbeat")), _time(declared.get("heartbeat"))
        if previous is None or (observed is not None and observed >= previous):
            declared.update(worker)
        result[name] = {**old, "seat": name, "declared": declared,
                        "heartbeat": declared.get("heartbeat", "UNKNOWN")}
    return result


def _append(state, events):
    journal = state.setdefault("events", [])
    known = {event["id"]: event for event in journal}
    added = 0
    for original in events:
        event = copy.deepcopy(original)
        if not isinstance(event.get("id"), str) or not event["id"]:
            raise ValueError("Every event requires a stable id")
        old = known.get(event["id"])
        if old:
            # seq is assigned by the shared store, not an upstream carrier.
            if {k: v for k, v in old.items() if k != "seq"} != {
                    k: v for k, v in event.items() if k != "seq"}:
                raise ValueError("Event id reused with different content: " + event["id"])
            continue
        event["seq"] = len(journal) + 1
        journal.append(event)
        known[event["id"]] = event
        added += 1
    return added


def _project(state, moment):
    view = project(state.get("events", []), now=moment, seats=_seats(state),
                   provider_facts=state.get("provider_facts", {}))
    state["tasks"] = view["tasks"]
    return view


def _merge_facts(state, incoming):
    facts = state.setdefault("provider_facts", {})
    for key, fact in incoming.items():
        old = copy.deepcopy(facts.get(key, {}))
        fact = copy.deepcopy(fact)
        for row in (old, fact):
            for field in ("equivalent", "superseded_by"):
                if field in row:
                    row[field] = normalize_equivalent(row[field])
        if old:
            facts[key] = old
        # A failed or older refresh cannot erase a landed immutable fact.
        if _merged(old) or _landed_artifact(old):
            continue
        observed, previous = _time(fact.get("observed_at")), _time(old.get("observed_at"))
        # Baked listings deliberately carry UNKNOWN observations. Text ordering
        # would pin those facts forever and misorder equivalent timezone offsets.
        if previous is None or (observed is not None and observed >= previous):
            for field in ("equivalent", "superseded_by"):
                previous = old.get(field)
                current = fact.get(field)
                if isinstance(previous, dict) and (_merged(previous) or _landed_artifact(previous)):
                    if not isinstance(current, dict) or not (_merged(current) or _landed_artifact(current)):
                        fact[field] = previous
            facts[key] = fact


class Runtime:
    def __init__(self, root, *, store=None, state_dir=None):
        self.root = Path(root).resolve()
        self.store = store or GitStore(self.root)
        if state_dir:
            self.state_dir = Path(state_dir)
        else:
            # A linked worktree's .git is a file. Share the cache across local
            # worktrees through Git's actual common directory.
            common = Path(self.store.git.out("rev-parse", "--git-common-dir").strip())
            self.state_dir = (common if common.is_absolute() else self.root / common) / "swarm-cache"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _dispatch_facts(self, action, payload, moment, *, worker_activity=True):
        """Refresh only exact candidate identifiers, once outside CAS retries."""
        if action not in {"take", "next", "ship", "block", "abandon"}:
            return {}, []
        from .sources import legacy_events
        from .providers import enrich
        _, state = self.store.read(refresh=False)
        _append(state, legacy_events(state.get("legacy_holdings", {})))
        worker = str(payload.get("worker") or "")
        if worker and worker_activity:
            state.setdefault("workers", {}).setdefault(worker, {}).update(
                {**(payload.get("seat") or {}), "seat": worker, "heartbeat": moment})
        if not worker_activity:
            current = _project(state, moment)
            worker_route = route(current["tasks"], worker, _seats(state), moment)
            if worker_route.get("reason") in {"worker_unknown", "worker_not_live"}:
                return {}, []
        selected = task_key(payload["task_key"]) if payload.get("task_key") else None
        facts, deferred, remaining, attempted = {}, [], 4, set()
        # The selected owner command may need no provider call; still leave
        # room to refresh the next candidate within the same four-call budget.
        for _ in range(5):
            view = _project(state, moment)
            target = selected if selected and selected not in attempted else None
            if target is None:
                candidates = copy.deepcopy(view["tasks"])
                if selected and action in {"ship", "block", "abandon"} and selected in candidates:
                    # Preview next work without changing the actual task.
                    candidates[selected]["state"] = "BLOCKED"
                for key, row in candidates.items():
                    if row.get("reconciliation_needed") in {"provider_state", "merge_sha", "closure_evidence"}:
                        row["dispatchable"] = key not in attempted
                target = route(candidates, worker, _seats(state), moment).get("task_key")
            if not target or target in attempted:
                break
            row = view["tasks"].get(target, {"task_key": target, "state": "OPEN"})
            if target == selected and payload.get("artifact"):
                row = {**row, "artifact": payload["artifact"], "repo": payload.get("repo") or row.get("repo")}
            artifact = row.get("artifact")
            attempted.add(target)
            if not target.startswith("github:") and not (
                    isinstance(artifact, dict) and artifact.get("complete") is True):
                will_roll = row.get("state") in TERMINAL or action in {"block", "abandon"} or (
                    action == "take" and row.get("state") == "ACTIVE"
                    and row.get("worker") != worker and not row.get("recoverable"))
                if target == selected and will_roll:
                    continue
                break
            if row.get("provider_freshness") in {"CURRENT", "IMMUTABLE"} and row.get("reconciliation_needed") in (None, "UNKNOWN", ""):
                if action in {"take", "next"} and row.get("state") not in TERMINAL:
                    break
                continue
            enriched = enrich({target: row}, self.state_dir, max_calls=remaining, now=moment)
            remaining -= enriched.get("calls", 0)
            facts.update(enriched.get("provider_facts", {}))
            deferred.extend(enriched.get("deferred", []))
            _merge_facts(state, enriched.get("provider_facts", {}))
            if remaining <= 0:
                break
        return facts, deferred

    def read(self, *, refresh=False, worker=None, limit=100,
             task=None, states=None, owner=None, after=None):
        tip, state = self.store.read(refresh=refresh)
        moment = now_iso()
        view = _project(state, moment)
        page = select_tasks(view["tasks"], limit=limit, task=task,
                            states=states, owner=owner, after=after)
        return {"ok": True, "authority": "state/claims", "tip": tip,
                "observed_at": moment, "summary": status(view["tasks"], _seats(state), moment),
                "tasks": page["rows"], "total": page["total"], "matched": page["matched"],
                "truncated": page["truncated"], "next_cursor": page["next_cursor"],
                "collisions": view.get("collisions", [])[-50:],
                "rejected": view.get("rejected", [])[-20:],
                "coverage": state.get("coverage", {}),
                "feed_cursor": state.get("cursors", {}).get("commons", {}).get("feed_cursor", "UNKNOWN"),
                "next": route(view["tasks"], worker, _seats(state), moment) if worker else None}

    def sync(self, *, work_snapshot=None, provider_facts=None, events=None,
             max_calls=4, refresh_providers=True, push=True):
        from .sources import collect
        _, prior = self.store.read(refresh=True)
        imported = collect(self.root, prior.get("cursors", {}), work_snapshot=work_snapshot)
        incoming = list(imported.get("events", [])) + list(events or [])
        try:
            from .sources import legacy_events
        except ImportError:
            legacy_events = None
        if legacy_events:
            incoming += legacy_events(prior.get("legacy_holdings", {}))
        candidate = copy.deepcopy(prior)
        _append(candidate, incoming)
        candidate["seats"] = imported.get("seats", candidate.get("seats", {}))
        _merge_facts(candidate, imported.get("provider_facts", {}))
        _merge_facts(candidate, provider_facts or {})
        moment = now_iso()
        projection = _project(candidate, moment)
        fresh = {"provider_facts": {}, "calls": 0, "deferred": []}
        if refresh_providers and max_calls:
            from .providers import enrich
            fresh = enrich(projection["tasks"], self.state_dir, max_calls=max_calls, now=moment)
        facts = {**imported.get("provider_facts", {}), **(provider_facts or {}),
                 **fresh.get("provider_facts", {})}

        def mutation(state):
            before = _project(state, moment)["tasks"]
            added = _append(state, incoming)
            if legacy_events:
                # Collection/provider I/O preceded this CAS read. A direct
                # release or take may have changed a sibling holding meanwhile;
                # replay that exact current custody after the collected inputs.
                added += _append(state, legacy_events(state.get("legacy_holdings", {})))
            _merge_facts(state, facts)
            state["seats"] = imported.get("seats", state.get("seats", {}))
            # Do not overwrite a concurrent sync's newer boundary with this read.
            if state.get("cursors", {}) == prior.get("cursors", {}):
                state["cursors"] = imported.get("cursors", state.get("cursors", {}))
                state["coverage"] = imported.get("coverage", {})
            view = _project(state, moment)
            assignments = []
            for closed_key, previous in sorted(before.items()):
                closed = view["tasks"].get(closed_key, {})
                worker = previous.get("worker")
                if previous.get("state") != "ACTIVE" or closed.get("state") not in TERMINAL or not worker or worker == "UNKNOWN":
                    continue
                choice = route(view["tasks"], worker, _seats(state), moment)
                target = choice.get("task_key")
                if not target:
                    continue
                row = view["tasks"][target]
                event = {"id": "reconcile-next:" + digest([closed_key, closed.get("merge_sha"), worker, target]),
                         "action": "TAKE", "task_key": target, "worker": worker,
                         "at": moment, "source": "swarm-reconciler"}
                if row.get("recoverable"):
                    _append(state, [{**event, "id": event["id"] + ":recover", "action": "RECOVER",
                                     "expected_worker": row.get("worker"), "expected_heartbeat": row.get("heartbeat")}])
                _append(state, [event])
                # Taking actual next work is meaningful worker activity. Keep
                # automatic assignment and explicit take on the same seat lease.
                state.setdefault("workers", {}).setdefault(worker, {}).update(
                    seat=worker, heartbeat=moment,
                    dispatch_cursor=state.get("cursors", {}).get("commons", {}).get("feed_cursor", "UNKNOWN"))
                view = _project(state, moment)
                assignments.append(context_bundle(view["tasks"][target], state["events"]))
            return {"action": "sync", "ingested": added, "tasks": len(view["tasks"]),
                    "summary": status(view["tasks"], _seats(state), moment),
                    "provider_calls": fresh.get("calls", 0),
                    "deferred": fresh.get("deferred", []), "coverage": state.get("coverage", {}),
                    "assignments": assignments}
        return self.store.update(mutation, push=push)

    def operate(self, action, payload, *, push=True, worker_activity=True):
        if type(worker_activity) is not bool:
            raise ValueError("worker_activity must be a boolean")
        action = str(action).lower()
        if action not in {"open", "take", "heartbeat", "ship", "block", "abandon", "next"}:
            raise ValueError("Unknown swarm action: " + action)
        if not isinstance(payload, dict):
            raise ValueError("Expected operation object")
        from integrations.command_center.schema import _no_secret_fields, _metadata
        _no_secret_fields(payload)
        payload = _metadata(payload)
        operation_id = payload.get("operation_id")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id is required; reuse it and the exact payload after interruption")
        worker = str(payload.get("worker") or "").strip()
        if action != "open" and not worker:
            raise ValueError("worker is required for custody/activity")
        key = task_key(payload["task_key"]) if payload.get("task_key") else None
        if action not in {"next", "heartbeat"} and not key:
            raise ValueError("task_key is required")
        if action == "block" and (not payload.get("blocker") or not payload.get("next_action")):
            raise ValueError("BLOCKED requires blocker and exact next_action")
        request_identity = {"action": action, "payload": payload}
        if not worker_activity:
            # A coordinator choosing a seat is not evidence that seat is live.
            # Preserve the historical hash for direct worker operations.
            request_identity["worker_activity"] = False
        request_hash = digest(request_identity)
        moment = now_iso()
        # Replaying a completed operation performs no provider reads.
        _, cached = self.store.read(refresh=False)
        prior_operation = cached.get("operations", {}).get(operation_id)
        fresh_facts, deferred = ({}, []) if prior_operation else self._dispatch_facts(
            action, payload, moment, worker_activity=worker_activity)

        def mutation(state):
            from .sources import legacy_events
            _append(state, legacy_events(state.get("legacy_holdings", {})))
            _merge_facts(state, fresh_facts)
            operations = state.setdefault("operations", {})
            old = operations.get(operation_id)
            if old:
                if old["request_hash"] != request_hash:
                    raise ValueError("operation_id reused with different payload")
                # Preserve the operation's assignments without presenting an
                # obsolete ACTIVE receipt as current custody after shipment or
                # recovery. A retry never takes an additional task.
                current_view = _project(state, moment)
                result = copy.deepcopy(old["result"])
                for field in ("task", "next"):
                    prior_task = result.get(field)
                    prior_key = prior_task.get("task_key") if isinstance(prior_task, dict) else None
                    if prior_key in current_view["tasks"]:
                        result[field] = context_bundle(current_view["tasks"][prior_key], state["events"])
                return {**result, "replayed": True, "canonical_at": moment}
            if worker and worker_activity:
                descriptor = dict(payload.get("seat") or {})
                descriptor.update(seat=worker, heartbeat=moment)
                descriptor["feed_cursor"] = payload.get("feed_cursor") or (
                    state.get("workers", {}).get(worker, {}).get("feed_cursor") or "UNKNOWN")
                descriptor["dispatch_cursor"] = (
                    state.get("cursors", {}).get("commons", {}).get("feed_cursor") or "UNKNOWN")
                state.setdefault("workers", {}).setdefault(worker, {}).update(descriptor)
            view = _project(state, moment)
            selected_key = key
            if not selected_key and action == "heartbeat":
                active = [k for k, row in view["tasks"].items()
                          if row.get("state") == "ACTIVE" and row.get("worker") == worker]
                if len(active) != 1:
                    raise ValueError("heartbeat needs task_key unless worker owns exactly one ACTIVE task")
                selected_key = active[0]

            def emit(verb, target, suffix="", **extra):
                allowed = ("base_sha", "head_sha", "branch", "pr", "issue", "repo", "artifact",
                           "merge_sha", "blocker", "next_action", "required_capabilities",
                           "priority", "source_event_ids", "exact_error", "model", "harness")
                event = {field: payload[field] for field in allowed if field in payload}
                event.update(id="swarm:" + operation_id + suffix, action=verb, task_key=target,
                             worker=worker or "UNKNOWN", at=moment, source="swarmctl",
                             feed_cursor=payload.get("feed_cursor") or state.get("workers", {}).get(worker, {}).get("feed_cursor", "UNKNOWN"))
                event.update(extra)
                _append(state, [event])

            collision = None
            if action == "open":
                emit("OPEN", selected_key)
            elif action == "take":
                row = view["tasks"].get(selected_key)
                if not row:
                    emit("OPEN", selected_key, ":open")
                    view = _project(state, moment)
                    row = view["tasks"][selected_key]
                if row and row.get("state") in TERMINAL:
                    collision = {"task_key": selected_key, "reason": "terminal", "state": row["state"]}
                elif row and row.get("dispatchable") is False:
                    collision = {"task_key": selected_key, "reason": "provider_reconciliation_needed",
                                 "required": row.get("reconciliation_needed")}
                elif row and row.get("state") == "ACTIVE" and not row.get("recoverable") and row.get("worker") != worker:
                    collision = {"task_key": selected_key, "reason": "already_active", "worker": row.get("worker")}
                    emit("TAKE", selected_key, ":collision")
                else:
                    owns = row.get("state") == "ACTIVE" and row.get("worker") == worker
                    suitability = route({selected_key: row}, worker, _seats(state), moment)
                    if (not owns or not worker_activity) and suitability.get("task_key") != selected_key:
                        collision = {"task_key": selected_key, "reason": suitability.get("reason"),
                                     "routing": suitability}
                    else:
                        if row.get("recoverable"):
                            emit("RECOVER", selected_key, ":recover", expected_worker=row.get("worker"),
                                 expected_heartbeat=row.get("heartbeat"))
                        emit("TAKE", selected_key)
            elif action != "next":
                emit({"heartbeat": "HEARTBEAT", "ship": "SHIP", "block": "BLOCK",
                      "abandon": "ABANDON"}[action], selected_key)
            view = _project(state, moment)
            current = view["tasks"].get(selected_key) if selected_key else None
            next_job = None
            should_roll = action == "next" or collision is not None or (
                current and current.get("state") in TERMINAL and action != "open")
            if should_roll:
                choice = route(view["tasks"], worker, _seats(state), moment)
                next_key = choice.get("task_key")
                if next_key:
                    next_row = view["tasks"][next_key]
                    if next_row.get("recoverable"):
                        emit("RECOVER", next_key, ":next:recover", expected_worker=next_row.get("worker"),
                             expected_heartbeat=next_row.get("heartbeat"))
                    emit("TAKE", next_key, ":next")
                    view = _project(state, moment)
                    next_job = context_bundle(view["tasks"][next_key], state["events"])
                else:
                    next_job = choice
            result = {"action": action, "operation_id": operation_id,
                      "task": context_bundle(current, state["events"]) if current else None,
                      "collision": collision, "next": next_job,
                      "deferred": deferred,
                      "rejected": [row for row in view.get("rejected", [])
                                   if operation_id in str(row.get("id", row.get("event_id", "")))]}
            operations[operation_id] = {"request_hash": request_hash, "result": result}
            return result
        return self.store.update(mutation, push=push)
