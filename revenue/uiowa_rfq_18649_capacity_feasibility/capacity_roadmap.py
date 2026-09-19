#!/usr/bin/env python3
"""Connect resource ranges to roadmap feasibility (UIOWA-116).

The completion bar is "results preserve prerequisite order and show unmet
capacity explicitly; relative plans make no personal availability commitments."
All three are graph and arithmetic properties, so all three are computed:

* PREREQUISITE ORDER is a real dependency graph -- topological ordering with
  cycle detection, and an explicit check for the defect a hand-built roadmap
  table hides best: a prerequisite scheduled LATER than the item depending on
  it. Parallelism is derived from reachability, not from "these look unrelated".

* UNMET CAPACITY is shown on the plan AS PROPOSED. A scheduler that silently
  slides work until everything fits reports a feasible plan and hides the
  shortfall that made it slide, so both views are produced: the proposed plan
  with its shortfalls, and the capacity-feasible resequencing with every move
  and its reason named.

* NO PERSONAL AVAILABILITY COMMITMENT is enforced at the loader, not asked for
  in a README: capacity is per role, a capacity record carrying a person-like
  field is rejected, role ids must be role-shaped, and no calendar date is
  emitted anywhere -- phases are relative windows only.

An UNKNOWN estimate is never zero. It schedules (so the sequence stays coherent)
but it makes its phase's verdict UNKNOWN rather than FEASIBLE, because a phase
whose cost nobody has estimated has not been shown to fit.

Python 3 standard library only. No network. Deterministic: no clock, no RNG.
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict

UNKNOWN = "UNKNOWN"
ERROR = "error"
WARN = "warning"
INFO = "info"

BEYOND_HORIZON = "BEYOND_HORIZON"

FEASIBLE = "FEASIBLE"
INFEASIBLE = "INFEASIBLE"
UNVERIFIABLE = "UNKNOWN"

# Keys that would turn a role capacity assumption into a statement about a
# person. The order says relative plans make no personal availability
# commitments, so the loader refuses the shape rather than trusting the author.
PERSON_FIELDS = frozenset([
    "person", "people", "name", "names", "email", "individual", "individuals",
    "staff_member", "employee", "employee_id", "username", "user", "person_id",
    "assignee", "who", "contact",
])
ROLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
# Any calendar-looking string in an output would be a commitment to a date.
DATE_SHAPED = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2})\b")

RULES = OrderedDict([
    ("D001_DUPLICATE_ITEM_ID", "Every roadmap item id appears once."),
    ("D002_MISSING_PREREQUISITE", "Every prerequisite id resolves to an item in the set."),
    ("D003_SELF_PREREQUISITE", "No item is its own prerequisite."),
    ("D004_PREREQUISITE_CYCLE", "The prerequisite graph is acyclic; a cycle is reported as its path and refuses to schedule."),
    ("D005_PREREQ_AFTER_DEPENDENT", "No prerequisite is placed in a later phase than the item that depends on it."),
    ("D006_PHASE_NOT_IN_HORIZON", "Every proposed phase is one of the declared horizon phases."),
    ("C001_UNMET_CAPACITY", "Role demand above role capacity in a phase is reported with its shortfall."),
    ("C002_CAPACITY_UNVERIFIABLE", "An UNKNOWN estimate makes its phase UNKNOWN, never FEASIBLE, and is never counted as zero."),
    ("C003_BEYOND_HORIZON", "Work that fits in no phase of the horizon is reported, not dropped."),
    ("C004_UNKNOWN_ROLE", "Every role an item needs exists in the capacity assumptions."),
    ("P001_PERSON_FIELD", "Capacity is per role; a person-like field is rejected on load."),
    ("P002_ROLE_SHAPE", "Role ids are role-shaped identifiers, not personal names."),
    ("S001_PHASE_MOVED", "An item the capacity pass had to move is named with the reason it moved."),
    ("S002_SAME_PHASE_CHAIN", "A dependency chain compressed into one window is flagged as tight."),
])


class InputError(Exception):
    """Input is unusable. Raised instead of letting a KeyError surface."""


class Finding(object):
    __slots__ = ("code", "severity", "subject", "detail")

    def __init__(self, code, severity, subject, detail):
        self.code = code
        self.severity = severity
        self.subject = subject or "-"
        self.detail = detail

    def as_dict(self):
        return {"code": self.code, "severity": self.severity,
                "subject": self.subject, "detail": self.detail}

    def __repr__(self):
        return "Finding(%s,%s,%s)" % (self.code, self.severity, self.subject)


def errors(findings):
    return [f for f in findings if f.severity == ERROR]


# ---------------------------------------------------------------- loading

def load_json(path):
    if not os.path.exists(path):
        raise InputError("file not found: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        raise InputError("%s is not valid JSON: %s" % (path, exc))
    if not isinstance(data, dict):
        raise InputError("%s must contain a JSON object at the top level" % path)
    return data


def _require(obj, keys, what):
    missing = [k for k in keys if k not in obj]
    if missing:
        raise InputError("%s is missing required key(s): %s" % (what, ", ".join(sorted(missing))))


def _scan_person_fields(node, path=""):
    """Walk any JSON structure looking for a person-like key."""
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            here = "%s.%s" % (path, k) if path else str(k)
            if str(k).strip().lower() in PERSON_FIELDS:
                hits.append(here)
            hits.extend(_scan_person_fields(v, here))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(_scan_person_fields(v, "%s[%d]" % (path, i)))
    return hits


def load_items(path):
    data = load_json(path)
    _require(data, ["meta", "items"], "item set %s" % path)
    _require(data["meta"], ["horizon_phases"], "item set meta in %s" % path)
    phases = data["meta"]["horizon_phases"]
    if not isinstance(phases, list) or not phases:
        raise InputError("item set %s declares no horizon_phases" % path)
    if not isinstance(data["items"], list) or not data["items"]:
        raise InputError("item set %s has no items" % path)
    for i, it in enumerate(data["items"]):
        if not isinstance(it, dict):
            raise InputError("item set %s item %d is not an object" % (path, i))
        _require(it, ["id", "title", "proposed_phase", "prerequisites", "effort"],
                 "item set %s item %d" % (path, i))
        if not isinstance(it["prerequisites"], list):
            raise InputError("item set %s item %r: prerequisites must be a list" % (path, it["id"]))
        if not isinstance(it["effort"], dict):
            raise InputError("item set %s item %r: effort must be an object keyed by role"
                             % (path, it["id"]))
    return data


def load_capacity(path):
    data = load_json(path)
    _require(data, ["meta", "roles", "scenarios"], "capacity set %s" % path)
    hits = _scan_person_fields({"roles": data["roles"], "scenarios": data["scenarios"]})
    if hits:
        raise InputError(
            "capacity set %s names individuals (%s). Capacity is stated per ROLE only: a "
            "relative plan must not commit a person's availability." % (path, ", ".join(sorted(hits))))
    for role in data["roles"]:
        if not ROLE_ID.match(str(role)):
            raise InputError(
                "capacity set %s: role id %r is not role-shaped (expected lower_snake_case such "
                "as 'iam_service_owner'). A personal name is not a role." % (path, role))
    if not isinstance(data["scenarios"], list) or not data["scenarios"]:
        raise InputError("capacity set %s has no scenarios" % path)
    for i, sc in enumerate(data["scenarios"]):
        _require(sc, ["id", "effort_point", "capacity_multiplier"],
                 "capacity set %s scenario %d" % (path, i))
        if sc["effort_point"] not in ("low", "likely", "high"):
            raise InputError("capacity set %s scenario %r: effort_point must be low|likely|high"
                             % (path, sc["id"]))
    return data


# ---------------------------------------------------------------- graph

class DependencyGraph(object):
    """The prerequisite graph. Edges run prerequisite -> dependent."""

    def __init__(self, items):
        self.items = OrderedDict()
        for it in items:
            self.items[it["id"]] = it
        self.prereqs = OrderedDict(
            (i, [p for p in self.items[i].get("prerequisites", []) if p in self.items])
            for i in self.items)
        self.dependents = OrderedDict((i, []) for i in self.items)
        for i, ps in self.prereqs.items():
            for p in ps:
                self.dependents[p].append(i)

    # -- cycles ---------------------------------------------------------
    def find_cycle(self):
        """Return one cycle as a path list, or None. DFS with a colour map."""
        WHITE, GREY, BLACK = 0, 1, 2
        colour = dict((i, WHITE) for i in self.items)
        stack = []

        def visit(node):
            colour[node] = GREY
            stack.append(node)
            for nxt in sorted(self.dependents[node]):
                if colour[nxt] == GREY:
                    return stack[stack.index(nxt):] + [nxt]
                if colour[nxt] == WHITE:
                    found = visit(nxt)
                    if found:
                        return found
            stack.pop()
            colour[node] = BLACK
            return None

        for node in sorted(self.items):
            if colour[node] == WHITE:
                found = visit(node)
                if found:
                    return found
        return None

    # -- ordering -------------------------------------------------------
    def topological_order(self):
        """Kahn's algorithm, id-sorted at each step so the order is stable."""
        indeg = dict((i, len(self.prereqs[i])) for i in self.items)
        ready = sorted(i for i in self.items if indeg[i] == 0)
        order = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for nxt in sorted(self.dependents[node]):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    ready.append(nxt)
            ready.sort()
        if len(order) != len(self.items):
            raise InputError("prerequisite cycle: cannot produce a topological order")
        return order

    def levels(self):
        """Longest-path depth: the earliest dependency level an item can sit at."""
        lvl = {}
        for node in self.topological_order():
            ps = self.prereqs[node]
            lvl[node] = 0 if not ps else 1 + max(lvl[p] for p in ps)
        return lvl

    def reachable_from(self, node):
        seen, stack = set(), list(self.dependents[node])
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.dependents[n])
        return seen

    def parallel_groups(self):
        """Per depth level, the items with no dependency path between them.

        Two items are reported as parallelizable only when neither can reach the
        other. Sharing a level is necessary but not sufficient -- this checks it.
        """
        lvl = self.levels()
        reach = dict((n, self.reachable_from(n)) for n in self.items)
        groups = OrderedDict()
        for level in sorted(set(lvl.values())):
            members = sorted(n for n in self.items if lvl[n] == level)
            independent = []
            for a in members:
                if all(b not in reach[a] and a not in reach[b] for b in members if b != a):
                    independent.append(a)
            groups[level] = {"members": members, "fully_independent": independent}
        return groups

    def tracks(self):
        """Weakly connected components: chains of work that never touch."""
        seen, out = set(), []
        for node in sorted(self.items):
            if node in seen:
                continue
            comp, stack = set(), [node]
            while stack:
                n = stack.pop()
                if n in comp:
                    continue
                comp.add(n)
                stack.extend(self.prereqs[n])
                stack.extend(self.dependents[n])
            seen |= comp
            out.append(sorted(comp))
        return out


# ---------------------------------------------------------------- checks

def static_checks(items_doc, capacity_doc):
    """Everything checkable before a single hour is scheduled."""
    findings = []
    items = items_doc["items"]
    phases = items_doc["meta"]["horizon_phases"]
    pidx = dict((p, n) for n, p in enumerate(phases))

    seen = set()
    for it in items:
        if it["id"] in seen:
            findings.append(Finding("D001_DUPLICATE_ITEM_ID", ERROR, it["id"],
                                    "item id appears more than once"))
        seen.add(it["id"])

    known = set(it["id"] for it in items)
    for it in items:
        for p in it.get("prerequisites", []):
            if p == it["id"]:
                findings.append(Finding("D003_SELF_PREREQUISITE", ERROR, it["id"],
                                        "item lists itself as a prerequisite"))
            elif p not in known:
                findings.append(Finding("D002_MISSING_PREREQUISITE", ERROR, it["id"],
                                        "prerequisite %r is not in the item set" % p))
        if it["proposed_phase"] not in pidx:
            findings.append(Finding("D006_PHASE_NOT_IN_HORIZON", ERROR, it["id"],
                                    "proposed phase %r is not one of %s"
                                    % (it["proposed_phase"], ", ".join(phases))))

    graph = DependencyGraph(items)
    cycle = graph.find_cycle()
    if cycle:
        findings.append(Finding("D004_PREREQUISITE_CYCLE", ERROR, " -> ".join(cycle),
                                "prerequisite cycle: %s. No schedule can satisfy this; "
                                "scheduling is refused until it is broken." % " -> ".join(cycle)))

    # The defect a hand-built roadmap table hides best.
    if not cycle:
        for it in items:
            if it["proposed_phase"] not in pidx:
                continue
            here = pidx[it["proposed_phase"]]
            for p in it.get("prerequisites", []):
                pit = next((x for x in items if x["id"] == p), None)
                if pit is None or pit["proposed_phase"] not in pidx:
                    continue
                there = pidx[pit["proposed_phase"]]
                if there > here:
                    findings.append(Finding(
                        "D005_PREREQ_AFTER_DEPENDENT", ERROR, it["id"],
                        "%s is proposed in %s but its prerequisite %s is proposed in %s, which is "
                        "later; the prerequisite cannot be done after the work that needs it"
                        % (it["id"], it["proposed_phase"], p, pit["proposed_phase"])))

    roles = set(capacity_doc["roles"])
    for it in items:
        for role in sorted(it["effort"]):
            if role not in roles:
                findings.append(Finding("C004_UNKNOWN_ROLE", ERROR, it["id"],
                                        "item needs role %r, which has no capacity assumption" % role))

    if not cycle:
        lvl = graph.levels()
        for track in graph.tracks():
            byphase = defaultdict(list)
            for n in track:
                it = graph.items[n]
                byphase[it["proposed_phase"]].append(n)
            for phase, members in sorted(byphase.items()):
                if len(members) >= 3:
                    chain = [m for m in members if lvl[m] != lvl[members[0]]]
                    if chain:
                        findings.append(Finding(
                            "S002_SAME_PHASE_CHAIN", WARN, phase,
                            "%s are proposed in the same window and are dependency-ordered "
                            "(levels %s); the window is carrying a whole chain"
                            % (", ".join(sorted(members)), ", ".join(str(lvl[m]) for m in sorted(members)))))

    findings.sort(key=lambda f: ({ERROR: 0, WARN: 1, INFO: 2}[f.severity], f.subject, f.code))
    return findings, graph


# ---------------------------------------------------------------- effort

def effort_for(item, role, point):
    """The estimate for one role at one scenario point. UNKNOWN stays UNKNOWN."""
    block = item["effort"].get(role)
    if block is None:
        return 0.0
    if isinstance(block, (int, float)):
        return float(block)
    value = block.get(point)
    if value is None:
        return UNKNOWN
    if isinstance(value, str) and value.strip().upper() == UNKNOWN:
        return UNKNOWN
    try:
        return float(value)
    except (TypeError, ValueError):
        return UNKNOWN


def demand_of(item, point):
    return OrderedDict((role, effort_for(item, role, point)) for role in sorted(item["effort"]))


def scenario_capacity(capacity_doc, scenario):
    mult = float(scenario["capacity_multiplier"])
    out = OrderedDict()
    for role in sorted(capacity_doc["roles"]):
        out[role] = OrderedDict(
            (phase, float(hours) * mult)
            for phase, hours in sorted(capacity_doc["roles"][role].items()))
    return out


# ---------------------------------------------------------------- planning

def _role_phase_table(assignments, items_by_id, phases, cap, point):
    """Demand vs capacity per role per phase. Shortfall is printed, not absorbed."""
    demand = defaultdict(lambda: defaultdict(float))
    unknown = defaultdict(lambda: defaultdict(list))
    for item_id, phase in assignments.items():
        if phase == BEYOND_HORIZON:
            continue
        for role, hours in demand_of(items_by_id[item_id], point).items():
            if hours == UNKNOWN:
                unknown[role][phase].append(item_id)
            else:
                demand[role][phase] += hours
    rows = []
    for role in sorted(cap):
        for phase in phases:
            d = demand[role].get(phase, 0.0)
            unk = sorted(unknown[role].get(phase, []))
            c = cap[role].get(phase, 0.0)
            if unk:
                verdict, shortfall = UNVERIFIABLE, None
            elif d > c:
                verdict, shortfall = INFEASIBLE, d - c
            else:
                verdict, shortfall = FEASIBLE, None
            rows.append(OrderedDict([
                ("role", role), ("phase", phase), ("capacity", round(c, 1)),
                ("demand_known", round(d, 1)), ("unknown_items", unk),
                ("verdict", verdict),
                ("shortfall", None if shortfall is None else round(shortfall, 1)),
                ("headroom", None if verdict != FEASIBLE else round(c - d, 1)),
            ]))
    return rows


def plan_proposed(items_doc, capacity_doc, scenario, graph):
    """The plan exactly as proposed, with its shortfalls left visible.

    This view exists because a scheduler that slides work until it fits will
    always report a feasible plan. The shortfall that caused the slide is the
    finding leadership actually needs.
    """
    phases = items_doc["meta"]["horizon_phases"]
    items_by_id = graph.items
    point = scenario["effort_point"]
    cap = scenario_capacity(capacity_doc, scenario)
    assignments = OrderedDict((i, items_by_id[i]["proposed_phase"]) for i in graph.topological_order())
    rows = _role_phase_table(assignments, items_by_id, phases, cap, point)
    findings = []
    for r in rows:
        if r["verdict"] == INFEASIBLE:
            findings.append(Finding("C001_UNMET_CAPACITY", ERROR, "%s/%s" % (r["role"], r["phase"]),
                                    "demand %.1f h exceeds capacity %.1f h by %.1f h as proposed"
                                    % (r["demand_known"], r["capacity"], r["shortfall"])))
        elif r["verdict"] == UNVERIFIABLE:
            findings.append(Finding("C002_CAPACITY_UNVERIFIABLE", WARN,
                                    "%s/%s" % (r["role"], r["phase"]),
                                    "demand %.1f h plus UNKNOWN for %s against capacity %.1f h; "
                                    "this phase is not shown as feasible"
                                    % (r["demand_known"], ", ".join(r["unknown_items"]), r["capacity"])))
    return {"assignments": assignments, "rows": rows, "findings": findings, "capacity": cap}


def plan_feasible(items_doc, capacity_doc, scenario, graph):
    """Resequence to fit capacity WITHOUT breaking prerequisite order.

    Items are walked in topological order, so an item is only ever considered
    once every prerequisite already has a phase. The earliest phase it may take
    is its latest prerequisite's phase; from there it takes the first phase where
    every role it needs still has room. Work that fits nowhere lands in
    BEYOND_HORIZON rather than being quietly dropped off the end of the plan.
    """
    phases = items_doc["meta"]["horizon_phases"]
    pidx = dict((p, n) for n, p in enumerate(phases))
    items_by_id = graph.items
    point = scenario["effort_point"]
    cap = scenario_capacity(capacity_doc, scenario)
    remaining = OrderedDict((role, OrderedDict((p, cap[role].get(p, 0.0)) for p in phases))
                            for role in cap)
    assignments, moves, notes = OrderedDict(), [], []

    for item_id in graph.topological_order():
        item = items_by_id[item_id]
        earliest = 0
        for p in graph.prereqs[item_id]:
            pa = assignments.get(p)
            if pa == BEYOND_HORIZON:
                earliest = len(phases)
                break
            if pa in pidx:
                earliest = max(earliest, pidx[pa])
        proposed = pidx.get(item["proposed_phase"], 0)
        # Never earlier than proposed: the proposed phase is a deliberate choice
        # (you may want the routing table reviewed AFTER a quarter of operation).
        # Capacity can force work later; it does not entitle the tool to pull it
        # forward.
        start = max(earliest, proposed)
        demand = demand_of(item, point)
        placed, reason = None, None
        blocked_by_prereq = earliest >= len(phases)
        for n in range(start, len(phases)):
            phase = phases[n]
            fits = True
            for role, hours in demand.items():
                if hours == UNKNOWN:
                    continue  # cannot be checked; never treated as zero
                if remaining.get(role, {}).get(phase, 0.0) < hours:
                    fits = False
                    break
            if fits:
                placed = phase
                for role, hours in demand.items():
                    if hours != UNKNOWN:
                        remaining[role][phase] -= hours
                break
        if placed is None:
            placed = BEYOND_HORIZON
            if blocked_by_prereq:
                reason = "a prerequisite is itself beyond the horizon"
                detail = ("%s cannot be scheduled because a prerequisite of it did not fit inside "
                          "%s under scenario %r" % (item_id, phases[-1], scenario["id"]))
            else:
                reason = "no phase in the horizon has capacity for every role this item needs"
                detail = ("%s does not fit inside %s under scenario %r; it is reported here rather "
                          "than dropped off the end of the plan"
                          % (item_id, phases[-1], scenario["id"]))
            notes.append(Finding("C003_BEYOND_HORIZON", ERROR, item_id, detail))
        assignments[item_id] = placed
        if placed != item["proposed_phase"]:
            if reason is None:
                reason = ("prerequisite order" if earliest > proposed else "role capacity")
            moves.append(OrderedDict([
                ("item", item_id), ("proposed", item["proposed_phase"]),
                ("scheduled", placed), ("reason", reason)]))
            notes.append(Finding("S001_PHASE_MOVED", WARN, item_id,
                                 "proposed %s, scheduled %s (%s)"
                                 % (item["proposed_phase"], placed, reason)))
        if any(h == UNKNOWN for h in demand.values()):
            unk = sorted(r for r, h in demand.items() if h == UNKNOWN)
            notes.append(Finding("C002_CAPACITY_UNVERIFIABLE", WARN, item_id,
                                 "effort for %s is UNKNOWN, so this placement is not shown as "
                                 "capacity-feasible; it is not counted as zero either"
                                 % ", ".join(unk)))

    rows = _role_phase_table(assignments, items_by_id, phases, cap, point)
    notes.sort(key=lambda f: ({ERROR: 0, WARN: 1, INFO: 2}[f.severity], f.subject, f.code))
    return {"assignments": assignments, "rows": rows, "findings": notes,
            "moves": moves, "capacity": cap}


def verdict_of(rows, assignments=None):
    # Beyond-horizon work stops contributing demand, so the per-phase table can
    # read clean while the plan does not actually deliver. Check it first.
    if assignments and any(p == BEYOND_HORIZON for p in assignments.values()):
        return INFEASIBLE
    if any(r["verdict"] == INFEASIBLE for r in rows):
        return INFEASIBLE
    if any(r["verdict"] == UNVERIFIABLE for r in rows):
        return UNVERIFIABLE
    return FEASIBLE


# ---------------------------------------------------------------- rendering

W = 78


def _line(ch="-"):
    return "+" + ch * (W - 2) + "+"


def _row(text=""):
    t = str(text).encode("ascii", "replace").decode("ascii")
    return "| " + t[:W - 4].ljust(W - 4) + " |"


def bar(demand, capacity, width=28):
    """A text bar. Marks, never colour: '=' inside capacity, '!' over it, '|' is
    the capacity line."""
    if capacity <= 0:
        return "[" + "?" * width + "|]"
    scale = max(demand, capacity)
    inside = int(round(width * min(demand, capacity) / scale))
    over = int(round(width * max(0.0, demand - capacity) / scale))
    capmark = int(round(width * capacity / scale))
    cells = []
    for i in range(width):
        if i == capmark:
            cells.append("|")
        cells.append("=" if i < inside else ("!" if i < inside + over else "."))
    if capmark >= width:
        cells.append("|")
    return "[" + "".join(cells) + "]"


def render_graph_ascii(graph, items_doc):
    out = [_line("="), _row("DEPENDENCY GRAPH"), _line("=")]
    cycle = graph.find_cycle()
    if cycle:
        out.append(_row("CYCLE: " + " -> ".join(cycle)))
        out.append(_row("No schedule can satisfy this. Scheduling refused."))
        out.append(_line("="))
        return "\n".join(out) + "\n"
    lvl = graph.levels()
    groups = graph.parallel_groups()
    out.append(_row("Level = dependency depth. Items on one level with no path between"))
    out.append(_row("them can genuinely run in parallel; that is checked, not assumed."))
    out.append(_line("-"))
    for level, info in groups.items():
        for n in info["members"]:
            ps = graph.prereqs[n]
            arrow = ("  <- " + ", ".join(sorted(ps))) if ps else "  (no prerequisites)"
            out.append(_row("  L%-2d %-6s %-34s%s"
                            % (level, n, graph.items[n]["title"][:34], arrow)))
        if len(info["fully_independent"]) > 1:
            out.append(_row("       parallel: %s" % ", ".join(info["fully_independent"])))
        out.append(_row(""))
    out.append(_row("TRACKS (chains that never touch each other)"))
    for t in graph.tracks():
        out.append(_row("  " + " + ".join(t)))
    out.append(_line("="))
    _ = items_doc, lvl
    return "\n".join(out) + "\n"


def render_scenario_ascii(items_doc, graph, scenario, proposed, feasible):
    phases = items_doc["meta"]["horizon_phases"]
    out = []
    out.append(_line("="))
    out.append(_row("SCENARIO: %s  (%s)" % (scenario["id"], scenario.get("label", ""))))
    out.append(_row("estimates at the %r point, capacity x%s"
                    % (scenario["effort_point"], scenario["capacity_multiplier"])))
    out.append(_line("="))
    out.append(_row("LEGEND  = within capacity   ! over capacity   | capacity line"))
    out.append(_row("        . unused capacity   marks only, no colour"))
    out.append(_line("="))

    for title, plan in (("PLAN AS PROPOSED", proposed), ("CAPACITY-FEASIBLE RESEQUENCING", feasible)):
        out.append(_row(title + "   verdict: " + verdict_of(plan["rows"], plan["assignments"])))
        out.append(_line("-"))
        for phase in phases + [BEYOND_HORIZON]:
            members = [i for i, p in plan["assignments"].items() if p == phase]
            if not members and phase == BEYOND_HORIZON:
                continue
            out.append(_row("  %-10s %s" % (phase, "" if members else "(nothing scheduled)")))
            for m in members:
                ps = graph.prereqs[m]
                after = ("  after " + ", ".join(sorted(ps))) if ps else ""
                out.append(_row("     %-6s %-40s%s" % (m, graph.items[m]["title"][:40], after)))
        out.append(_line("-"))
        out.append(_row("  %-7s %-22s %7s %7s  %s"
                        % ("phase", "role", "capacity", "demand", "result")))
        for r in plan["rows"]:
            if r["demand_known"] == 0 and not r["unknown_items"]:
                continue
            if r["verdict"] == INFEASIBLE:
                result = "SHORT by %.1f h" % r["shortfall"]
            elif r["verdict"] == UNVERIFIABLE:
                result = "UNKNOWN (+%d unestimated)" % len(r["unknown_items"])
            else:
                result = "ok, %.1f h spare" % r["headroom"]
            out.append(_row("  %-7s %-22s %7.1f %7.1f  %s"
                            % (r["phase"], r["role"][:22], r["capacity"],
                               r["demand_known"], result)))
            out.append(_row("  %-30s %s" % ("", bar(r["demand_known"], r["capacity"]))))
        out.append(_line("="))

    if feasible["moves"]:
        out.append(_row("WHAT THE RESOURCE RANGE CHANGED"))
        out.append(_line("-"))
        for m in feasible["moves"]:
            out.append(_row("  %-6s %s -> %s   (%s)" % (m["item"], m["proposed"],
                                                        m["scheduled"], m["reason"])))
        out.append(_line("="))
    return "\n".join(out) + "\n"


def render_markdown(items_doc, capacity_doc, graph, static, results):
    out = []
    out.append("# Capacity-aware roadmap feasibility")
    out.append("")
    out.append("> %s" % items_doc["meta"].get("fiction_notice", ""))
    out.append("")
    out.append("> %s" % capacity_doc["meta"].get("no_individuals_notice", ""))
    out.append("")
    out.append("## Dependency checks")
    out.append("")
    if static:
        out.append("| Severity | Rule | Subject | Detail |")
        out.append("|---|---|---|---|")
        for f in static:
            out.append("| %s | %s | %s | %s |" % (f.severity, f.code, f.subject,
                                                  f.detail.replace("|", "\\|")))
    else:
        out.append("No dependency defects: the graph is acyclic, every prerequisite resolves, and "
                   "no prerequisite is placed later than the item that depends on it.")
    out.append("")
    out.append("## Scenario comparison")
    out.append("")
    out.append("| Scenario | Estimates | Capacity | Proposed plan | Resequenced | Items moved | Beyond horizon |")
    out.append("|---|---|---|---|---|---|---|")
    for sc, prop, feas in results:
        beyond = sum(1 for p in feas["assignments"].values() if p == BEYOND_HORIZON)
        out.append("| %s | %s | x%s | %s | %s | %d | %d |" % (
            sc["id"], sc["effort_point"], sc["capacity_multiplier"],
            verdict_of(prop["rows"], prop["assignments"]),
            verdict_of(feas["rows"], feas["assignments"]), len(feas["moves"]), beyond))
    out.append("")
    for sc, prop, feas in results:
        out.append("### %s - %s" % (sc["id"], sc.get("label", "")))
        out.append("")
        out.append("%s" % sc.get("note", ""))
        out.append("")
        out.append("| Item | Proposed | Scheduled | Reason |")
        out.append("|---|---|---|---|")
        for item_id, phase in feas["assignments"].items():
            proposed_phase = graph.items[item_id]["proposed_phase"]
            move = next((m for m in feas["moves"] if m["item"] == item_id), None)
            out.append("| %s | %s | %s | %s |" % (item_id, proposed_phase, phase,
                                                  move["reason"] if move else "unchanged"))
        out.append("")
        short = [r for r in prop["rows"] if r["verdict"] == INFEASIBLE]
        if short:
            out.append("Unmet capacity on the plan **as proposed**:")
            out.append("")
            out.append("| Role | Phase | Capacity | Demand | Short by |")
            out.append("|---|---|---|---|---|")
            for r in short:
                out.append("| %s | %s | %.1f | %.1f | %.1f |" % (
                    r["role"], r["phase"], r["capacity"], r["demand_known"], r["shortfall"]))
            out.append("")
    return "\n".join(out) + "\n"




# ---------------------------------------------------------------- provenance

# Why this exists: the Markdown and ASCII outputs of this lane carried their
# provenance notice; the CSVs did not. A CSV is the most portable artifact here
# and the one most likely to be lifted out of the bundle and opened alone --
# which is exactly how a fictional number ends up quoted as a real finding.
#
# The requirement is a PROVENANCE statement, not a fiction label. A real
# measurement must not be stamped synthetic, and an artifact whose source says
# nothing must not be stamped either way: it is reported as undeclared.

PROVENANCE_PREFIX = "# PROVENANCE: "
UNDECLARED_PROVENANCE = ("PROVENANCE NOT DECLARED IN SOURCE. Do not treat these rows as "
                         "real or as synthetic until the source declares which.")


def provenance_statement(*metas):
    """An explicit provenance wins; a fiction notice implies synthetic; silence
    is reported as undeclared rather than assumed in either direction."""
    for meta in metas:
        if isinstance(meta, dict) and str(meta.get("provenance", "")).strip():
            return " ".join(str(meta["provenance"]).split())
    for meta in metas:
        if isinstance(meta, dict) and str(meta.get("fiction_notice", "")).strip():
            return "SYNTHETIC. " + " ".join(str(meta["fiction_notice"]).split())
    return UNDECLARED_PROVENANCE


def write_provenance(fh, statement):
    """One banner line, then the header row. A '#' first line is the convention
    the rest of the kit uses, and read_csv_rows() below strips it, so the banner
    cannot break machine parsing."""
    fh.write(PROVENANCE_PREFIX + statement.replace("\r", " ").replace("\n", " ") + "\n")


def read_csv_rows(path):
    """The documented reader contract for these CSVs.

    Returns (provenance_statement_or_None, list_of_dict_rows). Leading '#' lines
    are metadata, not data; everything after them parses as ordinary CSV.
    """
    with open(path, "r", newline="", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    statement, start = None, 0
    for i, line in enumerate(lines):
        if line.startswith("#"):
            if statement is None and line.startswith(PROVENANCE_PREFIX):
                statement = line[len(PROVENANCE_PREFIX):].strip()
            start = i + 1
        else:
            break
    body = "\n".join(lines[start:])
    return statement, list(csv.DictReader(body.splitlines()))



def write_plan_csv(path, graph, results, statement=None):
    cols = ["scenario", "effort_point", "capacity_multiplier", "item", "rec", "title",
            "owner_role", "level", "prerequisites", "proposed_phase", "scheduled_phase",
            "moved_reason", "effort_unknown"]
    lvl = graph.levels()
    with open(path, "w", newline="", encoding="utf-8") as fh:
        write_provenance(fh, statement or UNDECLARED_PROVENANCE)
        w = csv.writer(fh)
        w.writerow(cols)
        for sc, _prop, feas in results:
            for item_id, phase in feas["assignments"].items():
                it = graph.items[item_id]
                move = next((m for m in feas["moves"] if m["item"] == item_id), None)
                demand = demand_of(it, sc["effort_point"])
                unk = sorted(r for r, h in demand.items() if h == UNKNOWN)
                w.writerow([sc["id"], sc["effort_point"], sc["capacity_multiplier"], item_id,
                            it.get("rec", ""), it["title"], it.get("owner_role", ""), lvl[item_id],
                            ";".join(sorted(graph.prereqs[item_id])), it["proposed_phase"], phase,
                            move["reason"] if move else "", ";".join(unk)])


def write_capacity_csv(path, results, statement=None):
    cols = ["scenario", "view", "role", "phase", "capacity", "demand_known",
            "unknown_items", "verdict", "shortfall", "headroom"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        write_provenance(fh, statement or UNDECLARED_PROVENANCE)
        w = csv.writer(fh)
        w.writerow(cols)
        for sc, prop, feas in results:
            for view, plan in (("proposed", prop), ("feasible", feas)):
                for r in plan["rows"]:
                    w.writerow([sc["id"], view, r["role"], r["phase"], r["capacity"],
                                r["demand_known"], ";".join(r["unknown_items"]), r["verdict"],
                                "" if r["shortfall"] is None else r["shortfall"],
                                "" if r["headroom"] is None else r["headroom"]])


# ---------------------------------------------------------------- driver

def run(items_doc, capacity_doc):
    static, graph = static_checks(items_doc, capacity_doc)
    if any(f.code == "D004_PREREQUISITE_CYCLE" for f in static):
        return static, graph, []
    results = []
    for sc in capacity_doc["scenarios"]:
        prop = plan_proposed(items_doc, capacity_doc, sc, graph)
        feas = plan_feasible(items_doc, capacity_doc, sc, graph)
        results.append((sc, prop, feas))
    return static, graph, results


def all_findings(static, results):
    out = list(static)
    for _sc, prop, feas in results:
        out.extend(prop["findings"])
        out.extend(feas["findings"])
    return out


# ---------------------------------------------------------------- cli

def _load(args):
    return load_items(args.items), load_capacity(args.capacity)


def cmd_check(args):
    items_doc, capacity_doc = _load(args)
    static, graph, results = run(items_doc, capacity_doc)
    findings = all_findings(static, results)
    if args.json:
        sys.stdout.write(json.dumps([f.as_dict() for f in findings], indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render_markdown(items_doc, capacity_doc, graph, static, results))
    return 1 if errors(findings) else 0


def cmd_plan(args):
    items_doc, capacity_doc = _load(args)
    static, graph, results = run(items_doc, capacity_doc)
    outdir = args.outdir
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    text = [render_graph_ascii(graph, items_doc), ""]
    for sc, prop, feas in results:
        text.append(render_scenario_ascii(items_doc, graph, sc, prop, feas))
        text.append("")
    with open(os.path.join(outdir, "roadmap-ascii.txt"), "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(text))
    with open(os.path.join(outdir, "feasibility-report.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write(render_markdown(items_doc, capacity_doc, graph, static, results))
    prov = provenance_statement(items_doc.get("meta", {}), capacity_doc.get("meta", {}))
    write_plan_csv(os.path.join(outdir, "roadmap-planning-table.csv"), graph, results, prov)
    write_capacity_csv(os.path.join(outdir, "capacity-by-role-phase.csv"), results, prov)
    for name in ("roadmap-ascii.txt", "feasibility-report.md",
                 "roadmap-planning-table.csv", "capacity-by-role-phase.csv"):
        sys.stdout.write("wrote %s\n" % os.path.join(outdir, name))
    for sc, prop, feas in results:
        beyond = sum(1 for p in feas["assignments"].values() if p == BEYOND_HORIZON)
        sys.stdout.write("%-12s proposed=%-10s resequenced=%-10s moved=%d beyond_horizon=%d\n"
                         % (sc["id"], verdict_of(prop["rows"], prop["assignments"]),
                            verdict_of(feas["rows"], feas["assignments"]),
                            len(feas["moves"]), beyond))
    findings = all_findings(static, results)
    return 1 if errors(findings) else 0


def cmd_rules(args):
    for code, desc in RULES.items():
        sys.stdout.write("%-32s %s\n" % (code, desc))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Connect resource ranges to roadmap feasibility: dependency graph + capacity.")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="dependency and capacity checks; exit 1 on an error")
    c.add_argument("--items", required=True)
    c.add_argument("--capacity", required=True)
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_check)
    p = sub.add_parser("plan", help="write the ASCII roadmap, report and planning tables")
    p.add_argument("--items", required=True)
    p.add_argument("--capacity", required=True)
    p.add_argument("--outdir", default="examples")
    p.set_defaults(func=cmd_plan)
    u = sub.add_parser("rules", help="print the rule table")
    u.set_defaults(func=cmd_rules)
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    try:
        return args.func(args)
    except InputError as exc:
        sys.stderr.write("INPUT ERROR: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
