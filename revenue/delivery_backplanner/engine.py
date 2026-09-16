from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Mapping, Sequence

VERSION = "delivery-backplanner/v1"
MAX_TASKS = 24
MAX_RESOURCES = 16
MAX_CALENDARS = 8
MAX_HORIZON_DAYS = 366
MAX_COMMITMENTS = 256
MAX_SEARCH_LIMIT = 2_000_000
MAX_ID_LEN = 80


class BackplannerError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _as_object(value: Any, where: str, allowed: set[str], required: set[str] = frozenset()) -> dict[str, Any]:
    if type(value) is not dict:
        raise BackplannerError(f"{where}: expected object")
    extra = set(value) - allowed
    missing = required - set(value)
    if extra:
        raise BackplannerError(f"{where}: unknown fields: {sorted(extra)}")
    if missing:
        raise BackplannerError(f"{where}: missing fields: {sorted(missing)}")
    return value


def _as_id(value: Any, where: str) -> str:
    if type(value) is not str or not value or len(value) > MAX_ID_LEN:
        raise BackplannerError(f"{where}: invalid identifier")
    if value.strip() != value or any(ord(ch) < 32 for ch in value):
        raise BackplannerError(f"{where}: invalid identifier")
    return value


def _as_int(value: Any, where: str, lo: int, hi: int) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise BackplannerError(f"{where}: expected integer in [{lo}, {hi}]")
    return value


def _as_date(value: Any, where: str) -> date:
    if type(value) is not str or len(value) != 10:
        raise BackplannerError(f"{where}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise BackplannerError(f"{where}: invalid date") from exc
    if parsed.isoformat() != value:
        raise BackplannerError(f"{where}: non-canonical date")
    return parsed


def _strict_json_loads(text: str) -> Any:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise BackplannerError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def reject_constant(value: str) -> None:
        raise BackplannerError(f"non-finite JSON number: {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs_hook, parse_constant=reject_constant)
    except BackplannerError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BackplannerError("invalid JSON") from exc


def load_spec_text(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 1_000_000:
        raise BackplannerError("spec exceeds 1,000,000 UTF-8 bytes")
    value = _strict_json_loads(text)
    if type(value) is not dict:
        raise BackplannerError("root: expected object")
    normalize_spec(value)
    return value


@dataclass(frozen=True)
class Calendar:
    name: str
    weekdays: tuple[int, ...]
    holidays: frozenset[date]

    def eligible(self, day: date) -> bool:
        return day.weekday() in self.weekdays and day not in self.holidays


@dataclass(frozen=True)
class Task:
    task_id: str
    duration: int
    calendar: str
    release: date
    latest_finish: date
    resources: tuple[tuple[str, int], ...]
    dependencies: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Commitment:
    commitment_id: str
    start: date
    end: date
    resources: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Model:
    horizon_start: date
    deadline: date
    search_limit: int
    calendars: Mapping[str, Calendar]
    resource_capacity: Mapping[str, int]
    tasks: Mapping[str, Task]
    commitments: tuple[Commitment, ...]
    topological_order: tuple[str, ...]
    spec: dict[str, Any]


def normalize_spec(spec: Mapping[str, Any]) -> Model:
    root = _as_object(
        dict(spec),
        "root",
        {"version", "horizon_start", "deadline", "search_limit", "calendars", "resources", "commitments", "tasks"},
        {"version", "horizon_start", "deadline", "calendars", "resources", "tasks"},
    )
    if root["version"] != VERSION:
        raise BackplannerError(f"root.version: expected {VERSION}")
    start = _as_date(root["horizon_start"], "root.horizon_start")
    deadline = _as_date(root["deadline"], "root.deadline")
    if deadline < start or (deadline - start).days > MAX_HORIZON_DAYS:
        raise BackplannerError("root: horizon must be 0..366 days")
    search_limit = _as_int(root.get("search_limit", 250_000), "root.search_limit", 1, MAX_SEARCH_LIMIT)

    calendars_raw = root["calendars"]
    if type(calendars_raw) is not list or not 1 <= len(calendars_raw) <= MAX_CALENDARS:
        raise BackplannerError("root.calendars: invalid size")
    calendars: dict[str, Calendar] = {}
    norm_calendars: list[dict[str, Any]] = []
    for i, raw in enumerate(calendars_raw):
        obj = _as_object(raw, f"calendars[{i}]", {"id", "weekdays", "holidays"}, {"id", "weekdays"})
        cid = _as_id(obj["id"], f"calendars[{i}].id")
        if cid in calendars:
            raise BackplannerError(f"duplicate calendar: {cid}")
        weekdays_raw = obj["weekdays"]
        if type(weekdays_raw) is not list or not weekdays_raw:
            raise BackplannerError(f"calendars[{i}].weekdays: expected non-empty array")
        weekdays: list[int] = []
        for j, raw_day in enumerate(weekdays_raw):
            day = _as_int(raw_day, f"calendars[{i}].weekdays[{j}]", 0, 6)
            if day in weekdays:
                raise BackplannerError(f"calendars[{i}].weekdays: duplicate {day}")
            weekdays.append(day)
        weekdays.sort()
        holidays_raw = obj.get("holidays", [])
        if type(holidays_raw) is not list or len(holidays_raw) > MAX_HORIZON_DAYS:
            raise BackplannerError(f"calendars[{i}].holidays: invalid array")
        holidays = sorted({_as_date(v, f"calendars[{i}].holidays") for v in holidays_raw})
        if len(holidays) != len(holidays_raw):
            raise BackplannerError(f"calendars[{i}].holidays: duplicates")
        calendar = Calendar(cid, tuple(weekdays), frozenset(holidays))
        calendars[cid] = calendar
        norm_calendars.append({"id": cid, "weekdays": weekdays, "holidays": [d.isoformat() for d in holidays]})

    resources_raw = root["resources"]
    if type(resources_raw) is not list or not 1 <= len(resources_raw) <= MAX_RESOURCES:
        raise BackplannerError("root.resources: invalid size")
    capacities: dict[str, int] = {}
    norm_resources: list[dict[str, Any]] = []
    for i, raw in enumerate(resources_raw):
        obj = _as_object(raw, f"resources[{i}]", {"id", "daily_capacity"}, {"id", "daily_capacity"})
        rid = _as_id(obj["id"], f"resources[{i}].id")
        if rid in capacities:
            raise BackplannerError(f"duplicate resource: {rid}")
        cap = _as_int(obj["daily_capacity"], f"resources[{i}].daily_capacity", 1, 10_000)
        capacities[rid] = cap
        norm_resources.append({"id": rid, "daily_capacity": cap})

    commitments_raw = root.get("commitments", [])
    if type(commitments_raw) is not list or len(commitments_raw) > MAX_COMMITMENTS:
        raise BackplannerError("root.commitments: invalid size")
    commitments: list[Commitment] = []
    norm_commitments: list[dict[str, Any]] = []
    commitment_ids: set[str] = set()
    for i, raw in enumerate(commitments_raw):
        obj = _as_object(raw, f"commitments[{i}]", {"id", "start", "end", "resources"}, {"id", "start", "end", "resources"})
        cid = _as_id(obj["id"], f"commitments[{i}].id")
        if cid in commitment_ids:
            raise BackplannerError(f"duplicate commitment: {cid}")
        commitment_ids.add(cid)
        cstart = _as_date(obj["start"], f"commitments[{i}].start")
        cend = _as_date(obj["end"], f"commitments[{i}].end")
        if cend < cstart or cstart < start or cend > deadline:
            raise BackplannerError(f"commitments[{i}]: outside horizon")
        cres = _normalize_resource_demands(obj["resources"], capacities, f"commitments[{i}].resources", allow_zero=False)
        commitments.append(Commitment(cid, cstart, cend, tuple(cres.items())))
        norm_commitments.append({"id": cid, "start": cstart.isoformat(), "end": cend.isoformat(), "resources": dict(sorted(cres.items()))})

    tasks_raw = root["tasks"]
    if type(tasks_raw) is not list or not 1 <= len(tasks_raw) <= MAX_TASKS:
        raise BackplannerError("root.tasks: invalid size")
    tasks: dict[str, Task] = {}
    norm_tasks: list[dict[str, Any]] = []
    raw_dependencies: dict[str, list[tuple[str, int]]] = {}
    for i, raw in enumerate(tasks_raw):
        obj = _as_object(
            raw,
            f"tasks[{i}]",
            {"id", "duration_workdays", "calendar", "release_date", "latest_finish", "resources", "dependencies"},
            {"id", "duration_workdays", "calendar", "release_date", "resources"},
        )
        tid = _as_id(obj["id"], f"tasks[{i}].id")
        if tid in tasks:
            raise BackplannerError(f"duplicate task: {tid}")
        duration = _as_int(obj["duration_workdays"], f"tasks[{i}].duration_workdays", 1, MAX_HORIZON_DAYS + 1)
        calendar_id = _as_id(obj["calendar"], f"tasks[{i}].calendar")
        if calendar_id not in calendars:
            raise BackplannerError(f"tasks[{i}].calendar: unknown calendar {calendar_id}")
        release = _as_date(obj["release_date"], f"tasks[{i}].release_date")
        latest = _as_date(obj.get("latest_finish", deadline.isoformat()), f"tasks[{i}].latest_finish")
        if release < start or release > deadline or latest < release or latest > deadline:
            raise BackplannerError(f"tasks[{i}]: invalid release/latest window")
        demands = _normalize_resource_demands(obj["resources"], capacities, f"tasks[{i}].resources", allow_zero=False)
        deps_raw = obj.get("dependencies", [])
        if type(deps_raw) is not list or len(deps_raw) > MAX_TASKS:
            raise BackplannerError(f"tasks[{i}].dependencies: invalid array")
        deps: list[tuple[str, int]] = []
        dep_ids: set[str] = set()
        norm_deps: list[dict[str, Any]] = []
        for j, raw_dep in enumerate(deps_raw):
            dobj = _as_object(raw_dep, f"tasks[{i}].dependencies[{j}]", {"task_id", "lag_workdays"}, {"task_id"})
            dep_id = _as_id(dobj["task_id"], f"tasks[{i}].dependencies[{j}].task_id")
            if dep_id in dep_ids:
                raise BackplannerError(f"tasks[{i}].dependencies: duplicate {dep_id}")
            dep_ids.add(dep_id)
            lag = _as_int(dobj.get("lag_workdays", 0), f"tasks[{i}].dependencies[{j}].lag_workdays", 0, MAX_HORIZON_DAYS)
            deps.append((dep_id, lag))
            norm_deps.append({"task_id": dep_id, "lag_workdays": lag})
        task_obj = Task(tid, duration, calendar_id, release, latest, tuple(sorted(demands.items())), tuple(deps))
        tasks[tid] = task_obj
        raw_dependencies[tid] = deps
        norm_tasks.append({"id": tid, "duration_workdays": duration, "calendar": calendar_id, "release_date": release.isoformat(), "latest_finish": latest.isoformat(), "resources": dict(sorted(demands.items())), "dependencies": sorted(norm_deps, key=lambda x: x["task_id"])})

    for tid, deps in raw_dependencies.items():
        for dep_id, _ in deps:
            if dep_id not in tasks:
                raise BackplannerError(f"task {tid}: orphan dependency {dep_id}")
            if dep_id == tid:
                raise BackplannerError(f"task {tid}: self dependency")

    topo = _topological_order(tasks)
    norm_spec = {"version": VERSION, "horizon_start": start.isoformat(), "deadline": deadline.isoformat(), "search_limit": search_limit, "calendars": sorted(norm_calendars, key=lambda x: x["id"]), "resources": sorted(norm_resources, key=lambda x: x["id"]), "commitments": sorted(norm_commitments, key=lambda x: x["id"]), "tasks": sorted(norm_tasks, key=lambda x: x["id"])}
    return Model(start, deadline, search_limit, calendars, capacities, tasks, tuple(commitments), topo, norm_spec)


def _normalize_resource_demands(raw: Any, capacities: Mapping[str, int], where: str, allow_zero: bool) -> dict[str, int]:
    if type(raw) is not dict or not raw:
        raise BackplannerError(f"{where}: expected non-empty object")
    out: dict[str, int] = {}
    for key, value in raw.items():
        rid = _as_id(key, f"{where} key")
        if rid not in capacities:
            raise BackplannerError(f"{where}: unknown resource {rid}")
        amount = _as_int(value, f"{where}.{rid}", 0 if allow_zero else 1, 10_000)
        if amount > capacities[rid]:
            raise BackplannerError(f"{where}.{rid}: demand exceeds daily capacity")
        out[rid] = amount
    return out


def _topological_order(tasks: Mapping[str, Task]) -> tuple[str, ...]:
    indegree = {tid: 0 for tid in tasks}
    children: dict[str, list[str]] = {tid: [] for tid in tasks}
    for tid, task in tasks.items():
        for dep_id, _ in task.dependencies:
            indegree[tid] += 1
            children[dep_id].append(tid)
    ready = sorted(tid for tid, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        tid = ready.pop(0)
        order.append(tid)
        for child in sorted(children[tid]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(tasks):
        raise BackplannerError("tasks: dependency cycle")
    return tuple(order)


def _day_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _working_days(calendar: Calendar, start: date, end: date) -> list[date]:
    return [d for d in _day_range(start, end) if calendar.eligible(d)]


def _candidate_blocks(model: Model, task: Task, schedule: Mapping[str, tuple[date, ...]]) -> list[tuple[date, ...]]:
    calendar = model.calendars[task.calendar]
    days = _working_days(calendar, model.horizon_start, task.latest_finish)
    index = {d: i for i, d in enumerate(days)}
    earliest = task.release
    for dep_id, lag in task.dependencies:
        dep_days = schedule[dep_id]
        dep_last = dep_days[-1]
        dep_idx = index.get(dep_last)
        if dep_idx is None:
            after = [d for d in days if d > dep_last]
            if len(after) <= lag:
                return []
            dep_ready = after[lag]
        else:
            target_idx = dep_idx + lag + 1
            if target_idx >= len(days):
                return []
            dep_ready = days[target_idx]
        if dep_ready > earliest:
            earliest = dep_ready
    candidates: list[tuple[date, ...]] = []
    for i, day in enumerate(days):
        if day < earliest:
            continue
        block = tuple(days[i : i + task.duration])
        if len(block) != task.duration:
            break
        if block[-1] > task.latest_finish:
            break
        candidates.append(block)
    return candidates


def _base_load(model: Model) -> dict[date, dict[str, int]]:
    load: dict[date, dict[str, int]] = {d: {rid: 0 for rid in model.resource_capacity} for d in _day_range(model.horizon_start, model.deadline)}
    for commitment in model.commitments:
        for day in _day_range(commitment.start, commitment.end):
            for rid, amount in commitment.resources:
                load[day][rid] += amount
                if load[day][rid] > model.resource_capacity[rid]:
                    raise BackplannerError(f"commitments overbook {rid} on {day.isoformat()}")
    return load


def _fits(load: Mapping[date, Mapping[str, int]], model: Model, task: Task, block: Sequence[date]) -> bool:
    return all(load[day][rid] + amount <= model.resource_capacity[rid] for day in block for rid, amount in task.resources)


def _apply(load: dict[date, dict[str, int]], task: Task, block: Sequence[date], sign: int) -> None:
    for day in block:
        for rid, amount in task.resources:
            load[day][rid] += sign * amount


def solve(spec: Mapping[str, Any]) -> dict[str, Any]:
    model = normalize_spec(spec)
    load = _base_load(model)
    schedule: dict[str, tuple[date, ...]] = {}
    nodes = 0
    limit_hit = False

    def dfs(position: int) -> bool:
        nonlocal nodes, limit_hit
        if position == len(model.topological_order):
            return True
        tid = model.topological_order[position]
        task = model.tasks[tid]
        for block in _candidate_blocks(model, task, schedule):
            if nodes >= model.search_limit:
                limit_hit = True
                return False
            nodes += 1
            if not _fits(load, model, task, block):
                continue
            schedule[tid] = block
            _apply(load, task, block, +1)
            if dfs(position + 1):
                return True
            _apply(load, task, block, -1)
            del schedule[tid]
        return False

    found = dfs(0)
    base: dict[str, Any] = {"version": VERSION, "input_sha256": _digest(model.spec), "search_limit": model.search_limit, "search_nodes": nodes}
    if found:
        normalized_schedule = _normalized_schedule(model, schedule)
        verdict = validate_schedule(model.spec, normalized_schedule)
        if not verdict["valid"]:
            raise AssertionError(f"internal solver emitted invalid schedule: {verdict}")
        result = {**base, "status": "PLAN_FOUND", "schedule": normalized_schedule, "resource_load": _resource_load_rows(model, schedule), "blockers": []}
    elif limit_hit:
        result = {**base, "status": "SEARCH_LIMIT", "schedule": [], "resource_load": [], "blockers": ["Search limit reached before exhaustive proof; result is inconclusive."]}
    else:
        result = {**base, "status": "NO_FEASIBLE_PLAN", "schedule": [], "resource_load": [], "blockers": ["Exhaustive bounded search found no schedule satisfying the supplied constraints."]}
    result["result_sha256"] = _digest({k: v for k, v in result.items() if k != "result_sha256"})
    return result


def _normalized_schedule(model: Model, schedule: Mapping[str, Sequence[date]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tid in sorted(schedule):
        task = model.tasks[tid]
        days = schedule[tid]
        rows.append({"task_id": tid, "calendar": task.calendar, "start": days[0].isoformat(), "finish": days[-1].isoformat(), "workdays": [d.isoformat() for d in days], "resources": dict(task.resources)})
    return rows


def validate_schedule(spec: Mapping[str, Any], schedule_rows: Any) -> dict[str, Any]:
    try:
        model = normalize_spec(spec)
        if type(schedule_rows) is not list or len(schedule_rows) != len(model.tasks):
            raise BackplannerError("schedule: must contain every task exactly once")
        seen: set[str] = set()
        schedule: dict[str, tuple[date, ...]] = {}
        for i, raw in enumerate(schedule_rows):
            obj = _as_object(raw, f"schedule[{i}]", {"task_id", "calendar", "start", "finish", "workdays", "resources"}, {"task_id", "calendar", "start", "finish", "workdays", "resources"})
            tid = _as_id(obj["task_id"], f"schedule[{i}].task_id")
            if tid not in model.tasks or tid in seen:
                raise BackplannerError(f"schedule[{i}]: unknown/duplicate task")
            seen.add(tid)
            task = model.tasks[tid]
            if obj["calendar"] != task.calendar or obj["resources"] != dict(task.resources):
                raise BackplannerError(f"schedule[{i}]: task metadata mismatch")
            workdays_raw = obj["workdays"]
            if type(workdays_raw) is not list or len(workdays_raw) != task.duration:
                raise BackplannerError(f"schedule[{i}].workdays: wrong duration")
            days = tuple(_as_date(v, f"schedule[{i}].workdays") for v in workdays_raw)
            if list(days) != sorted(days) or len(set(days)) != len(days):
                raise BackplannerError(f"schedule[{i}].workdays: invalid order/duplicates")
            calendar = model.calendars[task.calendar]
            eligible = _working_days(calendar, model.horizon_start, task.latest_finish)
            positions = [eligible.index(d) if d in eligible else -999 for d in days]
            if positions != list(range(positions[0], positions[0] + task.duration)):
                raise BackplannerError(f"schedule[{i}]: workdays are not consecutive eligible workdays")
            if days[0] < task.release or days[-1] > task.latest_finish:
                raise BackplannerError(f"schedule[{i}]: task window violation")
            if obj["start"] != days[0].isoformat() or obj["finish"] != days[-1].isoformat():
                raise BackplannerError(f"schedule[{i}]: start/finish mismatch")
            schedule[tid] = days
        for tid, task in model.tasks.items():
            if task.dependencies:
                candidate_blocks = _candidate_blocks(model, task, {dep: schedule[dep] for dep, _ in task.dependencies})
                if schedule[tid] not in candidate_blocks:
                    raise BackplannerError(f"task {tid}: dependency/lag violation")
        load = _base_load(model)
        for tid in model.topological_order:
            task = model.tasks[tid]
            block = schedule[tid]
            if not _fits(load, model, task, block):
                raise BackplannerError(f"task {tid}: resource capacity violation")
            _apply(load, task, block, +1)
        return {"valid": True, "error": None, "input_sha256": _digest(model.spec)}
    except (BackplannerError, ValueError) as exc:
        return {"valid": False, "error": str(exc)}


def _resource_load_rows(model: Model, schedule: Mapping[str, Sequence[date]]) -> list[dict[str, Any]]:
    load = _base_load(model)
    for tid, block in schedule.items():
        _apply(load, model.tasks[tid], block, +1)
    rows: list[dict[str, Any]] = []
    for day in _day_range(model.horizon_start, model.deadline):
        if any(load[day].values()):
            rows.append({"date": day.isoformat(), "usage": {rid: load[day][rid] for rid in sorted(load[day])}, "capacity": {rid: model.resource_capacity[rid] for rid in sorted(model.resource_capacity)}})
    return rows


def verify_result(spec: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    try:
        model = normalize_spec(spec)
        obj = _as_object(dict(result), "result", {"version", "input_sha256", "search_limit", "search_nodes", "status", "schedule", "resource_load", "blockers", "result_sha256"}, {"version", "input_sha256", "search_limit", "search_nodes", "status", "schedule", "resource_load", "blockers", "result_sha256"})
        if obj["version"] != VERSION:
            raise BackplannerError("result.version mismatch")
        if obj["input_sha256"] != _digest(model.spec):
            raise BackplannerError("result.input_sha256 mismatch")
        expected_digest = _digest({k: v for k, v in obj.items() if k != "result_sha256"})
        if obj["result_sha256"] != expected_digest:
            raise BackplannerError("result_sha256 mismatch")
        if obj["status"] not in {"PLAN_FOUND", "NO_FEASIBLE_PLAN", "SEARCH_LIMIT"}:
            raise BackplannerError("result.status invalid")
        if obj["status"] == "PLAN_FOUND":
            validation = validate_schedule(model.spec, obj["schedule"])
            if not validation["valid"]:
                raise BackplannerError(f"schedule invalid: {validation['error']}")
        recomputed = solve(model.spec)
        if _canonical_json(recomputed) != _canonical_json(obj):
            raise BackplannerError("semantic recomputation mismatch")
        return {"valid": True, "status": obj["status"], "result_sha256": expected_digest}
    except (BackplannerError, ValueError) as exc:
        return {"valid": False, "error": str(exc)}


def render_markdown(spec: Mapping[str, Any], result: Mapping[str, Any]) -> str:
    model = normalize_spec(spec)
    lines = ["# Delivery Backplanner Result", "", f"- Status: `{result['status']}`", f"- Horizon: `{model.horizon_start.isoformat()}` → `{model.deadline.isoformat()}`", f"- Search nodes: `{result['search_nodes']}` / `{result['search_limit']}`", f"- Input SHA-256: `{result['input_sha256']}`", f"- Result SHA-256: `{result['result_sha256']}`", ""]
    if result["status"] == "PLAN_FOUND":
        lines.extend(["## Timeline", "", "| Task | Start | Finish | Workdays |", "|---|---:|---:|---:|"])
        for row in sorted(result["schedule"], key=lambda r: (r["start"], r["task_id"])):
            lines.append(f"| {row['task_id']} | {row['start']} | {row['finish']} | {len(row['workdays'])} |")
    else:
        lines.extend(["## Blockers", ""])
        for blocker in result.get("blockers", []):
            lines.append(f"- {blocker}")
    lines.extend(["", "Authority: planning evidence on supplied assumptions only; no buyer/staffing/calendar/provider/payment authority.", ""])
    return "\n".join(lines)


def render_resource_csv(result: Mapping[str, Any]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["date", "resource", "usage", "capacity", "available"])
    for row in result.get("resource_load", []):
        for rid in sorted(row["capacity"]):
            usage = row["usage"][rid]
            capacity = row["capacity"][rid]
            writer.writerow([row["date"], rid, usage, capacity, capacity - usage])
    return buffer.getvalue()
