"""Port of the LDA ExemplarBank to Kaggriculture turns.

Source: app/src/main/java/com/local/deviceagent/ExemplarBank.kt and its call sites in
AgentOrchestrator.kt at LDA 54081cd58d2c45b868b4265c3dcb8990aa1cc9b4. The mechanism
ported, not paraphrased:

  * entries are lean (state digest -> action) DEMONSTRATIONS, append-only JSONL,
    capped and rolling;
  * keyed by a SITUATION CLASS -- the structural abstraction of how a situation of
    this KIND behaves -- so an example generalises rather than memorising a path;
  * recorded ONLY from scored ADVANCING steps (the `pos && m > 0` gate);
  * retrieval returns the newest 1-2 for the class, same-context first then any
    context, DEDUPLICATED by action shape so two entries never teach the same move;
  * placed immediately BEFORE the live state, so continuing the pattern IS the
    action for the live state.

Provenance is explicit and never fabricated. A row is either `model` -- an action
this driver's model actually authored and the engine actually advanced -- or
`teacher:<name>`, a bootstrap demonstration from a named official agent, labelled as
such in the row and in the injected header. A teacher row is never presented as a
past model success.
"""

import json
import os

MAX_ROWS = 400
MAX_STATE = 320
MAX_ACTION = 200


def situation_class(obs, config, seat, adm):
    """The structural class of this turn. Engine-derived shape only, no preference."""
    import constraints as C
    farm = obs["farms"][seat]
    n_units = 1 + len(farm.get("hands", []))
    present = {o[0] for o in adm["units"][0]}
    # ORTHOGONAL situation facts, not the capability string. Keying on the exact set
    # of admissible op names made "DGL" and "DL" different classes even though both
    # are "carrying goods, standing on the shed", so the deposit turn matched nothing
    # while the bank held six rows of exactly that situation. Only the three ops that
    # change what a turn is ABOUT are kept; DROP/PICKUP/PLACE/DIG/CARE/BUILD are
    # implied by carry and access and are dropped from the key.
    caps = "".join(c for c, op in (("W", "WATER"), ("H", "HARVEST"),
                                   ("P", "PLANT")) if op in present) or "-"
    invs = obs["private"].get("inventories", [])
    carrying = any(sum(i.values()) for i in invs)
    K = C.engine()
    access = [tuple(t) for t in K._shed_access_tiles(len(farm["tiles"]))]
    on_access = tuple(int(v) for v in farm["farmer"]) in access
    hz = C.horizon(obs, config, seat)
    dying = any(p["dies_at_refresh_unless_watered"] for p in hz["plants"])
    ripe = any(p["yield_units"] > 0 and p["age_days"] >= p["first_yield_day"]
               for p in hz["plants"])
    shed = obs["private"].get("shed", {})
    cap = int(config.get("shedCapacity", 100) or 100)
    return "|".join([
        f"u{n_units}",
        "can:" + caps,
        "carry" if carrying else "nocarry",
        "access" if on_access else "field",
        "dying" if dying else "safe",
        "ripe" if ripe else "unripe",
        "shedfull" if sum(shed.values()) >= cap else "shedroom",
    ])


def context_of(obs):
    """The coarse bucket retrieval prefers, standing in for the source's `app`."""
    d = int(obs["day"])
    return "early" if d < 8 else "mid" if d < 18 else "late"


def lean_state(state_text):
    """The lean digest an entry stores: the first 8 non-blank lines, capped."""
    lines = [ln.strip() for ln in state_text.splitlines() if ln.strip()]
    return " . ".join(lines[:8])[:MAX_STATE]


class Bank:
    def __init__(self, path):
        self.path = path
        self.rows = []
        if os.path.exists(path):
            with open(path) as fh:
                for ln in fh:
                    ln = ln.strip()
                    if ln:
                        try:
                            self.rows.append(json.loads(ln))
                        except Exception:
                            pass

    def record(self, cls, context, state_text, action, provenance, plan=None):
        """Bank one ADVANCING demonstration. Callers must apply the advancing gate.

        A row carries a `plan` because the emitted turn shape requires one first. A
        teacher row's plan is a factual restatement of what its action did, and the
        row stays labelled `teacher:` so it is never read as a model success.
        """
        if not cls or not state_text or not action:
            return
        if plan and "plan" not in action:
            action = {"plan": plan, **action}
        row = {"cls": cls, "ctx": context, "state": lean_state(state_text),
               "action": json.dumps(action, separators=(",", ":"))[:MAX_ACTION],
               "provenance": provenance, "n": len(self.rows)}
        self.rows.append(row)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        if len(self.rows) > MAX_ROWS:
            self.rows = self.rows[len(self.rows) // 4:]
            with open(self.path, "w") as fh:
                for r in self.rows:
                    fh.write(json.dumps(r) + "\n")

    @staticmethod
    def _drop_units(cls):
        """The class without its unit-count field."""
        return "|".join(cls.split("|")[1:])

    @staticmethod
    def _hands_of(action_json):
        """How many hand entries a stored action has, for shape compatibility."""
        import json as _j
        try:
            return len(_j.loads(action_json).get("hands") or [])
        except Exception:
            return -1

    def for_class(self, cls, context, n=2, exclude_state=None, n_hands=None):
        """Newest n for this class, deduplicated by action shape.

        Retrieval relaxes in the source's two-pass shape, one step further: exact
        class and same context, then exact class any context, then the class without
        its unit count. The last pass exists because a demonstration is ONE unit's op
        and generalises across how many units the turn has; without it a single-farmer
        turn could match nothing while the bank held the right situation under u5.
        The relaxation level is returned on each row so it stays visible.

        `exclude_state` drops any row whose lean digest matches the live one, so an
        evaluation card is never handed its own answer.
        """
        relaxed = self._drop_units(cls)
        passes = [
            ("exact+ctx", lambda r: r.get("cls") == cls and r.get("ctx") == context),
            ("exact", lambda r: r.get("cls") == cls),
            ("any-unit-count", lambda r: self._drop_units(r.get("cls", "")) == relaxed),
        ]
        out, seen = [], set()
        for level, pred in passes:
            for r in reversed(self.rows):
                if len(out) >= n:
                    break
                if not pred(r):
                    continue
                # Shape compatibility: a demonstration with a different number of hand
                # entries cannot be continued for this turn -- an 8-hand action shown
                # to a single farmer is noise the output grammar forbids anyway.
                if n_hands is not None and self._hands_of(r["action"]) != n_hands:
                    continue
                if exclude_state and r["state"] == exclude_state:
                    continue
                shape = r["action"].split('"farmer":')[-1][:26]
                if shape in seen:
                    continue
                seen.add(shape)
                row = dict(r)
                row["match"] = level
                out.append(row)
            if len(out) >= n:
                break
        return out


def block(rows):
    """The injected block. Provenance is stated in the header, never implied."""
    if not rows:
        return ""
    prov = {r.get("provenance", "?").split(":")[0] for r in rows}
    if prov == {"model"}:
        head = ("YOUR OWN PAST WINS on this kind of turn "
                "(state -> the action that advanced it):")
    elif prov == {"teacher"}:
        names = sorted({r["provenance"] for r in rows})
        head = (f"DEMONSTRATIONS on this kind of turn from {', '.join(names)} "
                f"(state -> the action that advanced it). These are a teacher's "
                f"turns, not your own past wins:")
    else:
        head = ("PAST ADVANCING TURNS of this kind (state -> the action that "
                "advanced it); each line is labelled with whose turn it was:")
    lines = []
    for r in rows:
        tag = "" if prov == {"model"} or prov == {"teacher"} else f"[{r['provenance']}] "
        lines.append(f"{tag}{r['state']} -> {r['action']}")
    return head + "\n" + "\n".join(lines)
