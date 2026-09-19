"""Bottom-up cost model for the proposed $24,000 base fee (UIOWA-003).

Five base work packages, costed from the bottom up: human production time,
human review time, compute and tooling, administration, correction effort, and
contingency. Each package is estimated at LOW / EXPECTED / HIGH effort, and the
model reports cost, contribution margin, and break-even hours.

Three rules this model will not bend on:

 1. **A missing estimate is never a zero cost.** A zero cost inflates margin,
    so the direction of that error is always "this bid looks profitable". An
    absent input stays UNKNOWN, propagates through every total that depends on
    it, and the affected package is excluded from the headline margin, which is
    then reported as not computable rather than printed as a number.

 2. **Every rate is an assumption, not a fact.** There is no agreed loaded rate
    for this engagement. Rates carry a `basis` string that must say ASSUMED;
    the model refuses a rate claiming to be an observed or contractual figure,
    because quoting a margin off an invented rate card is the specific way this
    artifact could mislead.

 3. **It reconciles to the commercial facts, it does not re-derive them.** The
    $24,000 base, the $4,000 option and the 40/40/20 milestone split are given
    inputs. A package total that does not reconcile to the quoted fee is an
    ERROR, not a rounding note.

Python 3 standard library only. Deterministic: no clock, no randomness.
"""

from __future__ import annotations

import json
from decimal import Decimal

import money
from money import UNKNOWN, is_unknown

CASES = ("low", "expected", "high")

# Cost lines every package carries. Kept explicit rather than inferred so a
# package that simply forgot one is visible as UNKNOWN instead of cheap.
EFFORT_LINES = ("production_hours", "review_hours", "correction_hours", "admin_hours")
CASH_LINES = ("compute_tooling",)


class ModelError(ValueError):
    """Bad input. Never silently repaired."""


def _require(mapping, key, where):
    if key not in mapping:
        raise ModelError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _opt_hours(raw, key, where):
    """Absent or null -> UNKNOWN. Present -> a real figure. Blank -> refused."""
    if key not in raw or raw[key] is None:
        return UNKNOWN
    value = raw[key]
    if isinstance(value, str) and not value.strip():
        raise ModelError(
            f"{where}: {key!r} is an empty string. Use null to mean 'not yet "
            f"estimated'; a blank is too easy to read as zero."
        )
    try:
        return money.hours(value)
    except (ValueError, ArithmeticError) as exc:
        raise ModelError(f"{where}: {key!r} is not a valid hours figure ({exc})") from exc


def _opt_money(raw, key, where):
    if key not in raw or raw[key] is None:
        return UNKNOWN
    try:
        return money.money(raw[key])
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise ModelError(f"{where}: {key!r} is not a valid amount ({exc})") from exc


class Rate:
    """A loaded hourly rate. An assumption, and it has to say so."""

    __slots__ = ("key", "label", "amount", "basis", "note")

    ALLOWED_BASIS = ("ASSUMED", "SYNTHETIC-FIXTURE")

    def __init__(self, key, label, amount, basis, note=""):
        self.key = key
        self.label = label
        self.amount = amount
        self.basis = basis
        self.note = note

    @classmethod
    def from_dict(cls, key, raw, where):
        basis = str(_require(raw, "basis", where)).upper()
        if basis not in cls.ALLOWED_BASIS:
            raise ModelError(
                f"{where}: rate basis {basis!r} is not allowed. This engagement has no "
                f"agreed rate card, so every rate must be declared {' or '.join(cls.ALLOWED_BASIS)}. "
                f"Quoting a margin off a rate presented as real would misstate the bid."
            )
        return cls(key, _require(raw, "label", where), money.money(_require(raw, "amount", where)),
                   basis, raw.get("note", ""))


class PackageCase:
    """One package at one effort case."""

    __slots__ = ("package", "case", "effort", "cash", "unknowns")

    def __init__(self, package, case, effort, cash, unknowns):
        self.package = package
        self.case = case
        self.effort = effort          # {line: hours}
        self.cash = cash              # {line: money}
        self.unknowns = tuple(unknowns)

    @property
    def has_unknown(self) -> bool:
        return bool(self.unknowns)

    def total_hours(self):
        return money.add(*[self.effort[k] for k in EFFORT_LINES])

    def labour_cost(self, rates, assignment):
        """Hours x the rate assigned to each line. UNKNOWN anywhere wins."""
        total = Decimal("0")
        for line in EFFORT_LINES:
            h = self.effort[line]
            if is_unknown(h):
                return UNKNOWN
            rate = rates[assignment[line]].amount
            total += h * rate
        return total

    def cash_cost(self):
        return money.add(*[self.cash[k] for k in CASH_LINES])

    def direct_cost(self, rates, assignment):
        return money.add(self.labour_cost(rates, assignment), self.cash_cost())


class Package:
    __slots__ = ("key", "name", "description", "cases", "milestone")

    def __init__(self, key, name, description, cases, milestone):
        self.key = key
        self.name = name
        self.description = description
        self.cases = cases            # {case: PackageCase}
        self.milestone = milestone

    @classmethod
    def from_dict(cls, raw, where):
        key = str(_require(raw, "key", where))
        name = str(_require(raw, "name", where))
        cases = {}
        raw_cases = _require(raw, "effort", where)
        for case in CASES:
            if case not in raw_cases:
                raise ModelError(
                    f"{where}: effort case {case!r} is missing. Low, expected and high are "
                    f"all required -- a single-point estimate hides the range this bid "
                    f"actually carries."
                )
            block = raw_cases[case]
            w = f"{where}.effort.{case}"
            effort, cash, unknowns = {}, {}, []
            for line in EFFORT_LINES:
                value = _opt_hours(block, line, w)
                effort[line] = value
                if is_unknown(value):
                    unknowns.append(f"{case}.{line}")
            for line in CASH_LINES:
                value = _opt_money(block, line, w)
                cash[line] = value
                if is_unknown(value):
                    unknowns.append(f"{case}.{line}")
            cases[case] = PackageCase(key, case, effort, cash, unknowns)

        # A model where high < low is arithmetically fine and obviously wrong.
        for line in EFFORT_LINES:
            lo, ex, hi = (cases[c].effort[line] for c in CASES)
            if not (is_unknown(lo) or is_unknown(ex) or is_unknown(hi)):
                if not (lo <= ex <= hi):
                    raise ModelError(
                        f"{where}: {line} is not ordered low <= expected <= high "
                        f"({lo} / {ex} / {hi}). One of the three is wrong."
                    )
        return cls(key, name, raw.get("description", ""), cases,
                   str(_require(raw, "milestone", where)))


class Model:
    """The whole bid: packages, rates, overheads, and the quoted price."""

    resolved_targets: tuple = ()

    def __init__(self, raw: dict):
        self._raw = json.loads(json.dumps(raw))
        self.title = str(_require(raw, "title", "document"))
        self.disclaimer = str(_require(raw, "disclaimer", "document"))

        comm = _require(raw, "commercial", "document")
        self.base_fee = money.money(_require(comm, "base_fee", "commercial"))
        self.option_fee = money.money(_require(comm, "option_fee", "commercial"))
        self.milestones = [
            {"key": str(_require(m, "key", "milestone")),
             "label": str(_require(m, "label", "milestone")),
             "share_pct": Decimal(str(_require(m, "share_pct", "milestone"))),
             "amount": money.money(_require(m, "amount", "milestone"))}
            for m in _require(comm, "milestones", "commercial")
        ]

        self.rates = {k: Rate.from_dict(k, v, f"rates.{k}")
                      for k, v in _require(raw, "rates", "document").items()}
        self.assignment = _require(raw, "rate_assignment", "document")
        for line in EFFORT_LINES:
            if line not in self.assignment:
                raise ModelError(f"rate_assignment: no rate assigned to {line!r}")
            if self.assignment[line] not in self.rates:
                raise ModelError(
                    f"rate_assignment: {line!r} points at unknown rate "
                    f"{self.assignment[line]!r}")

        over = _require(raw, "overheads", "document")
        self.contingency_pct = Decimal(str(_require(over, "contingency_pct", "overheads")))
        self.admin_overhead_pct = Decimal(str(_require(over, "admin_overhead_pct", "overheads")))
        if self.contingency_pct < 0 or self.admin_overhead_pct < 0:
            raise ModelError("overheads: percentages cannot be negative")

        self.packages = [Package.from_dict(p, f"packages[{i}]")
                         for i, p in enumerate(_require(raw, "packages", "document"))]
        if not self.packages:
            raise ModelError("document: no work packages supplied")
        keys = [p.key for p in self.packages]
        if len(set(keys)) != len(keys):
            raise ModelError("packages: duplicate package key")

        self.errors = self._reconcile()

    # -- reconciliation to the commercial facts -------------------------
    def _reconcile(self) -> list[str]:
        """The quoted facts are inputs. Disagreeing with them is an error."""
        problems = []
        total = money.add(*[m["amount"] for m in self.milestones])
        if total != self.base_fee:
            problems.append(
                f"milestones total {money.fmt_money(total)} but the base fee is "
                f"{money.fmt_money(self.base_fee)}")
        share = sum(m["share_pct"] for m in self.milestones)
        if share != Decimal("100"):
            problems.append(f"milestone shares total {share}%, not 100%")
        for m in self.milestones:
            expected = (self.base_fee * m["share_pct"] / Decimal("100")).quantize(money.CENT)
            if m["amount"] != expected:
                problems.append(
                    f"milestone {m['key']}: {money.fmt_money(m['amount'])} is not "
                    f"{m['share_pct']}% of the base fee ({money.fmt_money(expected)})")
        milestone_keys = {m["key"] for m in self.milestones}
        for p in self.packages:
            if p.milestone not in milestone_keys:
                problems.append(f"package {p.key} bills to unknown milestone {p.milestone!r}")
        return problems

    # -- costing ---------------------------------------------------------
    def package_cost(self, package: Package, case: str) -> dict:
        pc = package.cases[case]
        direct = pc.direct_cost(self.rates, self.assignment)
        admin = money.mul(direct, self.admin_overhead_pct / Decimal("100"))
        subtotal = money.add(direct, admin)
        contingency = money.mul(subtotal, self.contingency_pct / Decimal("100"))
        total = money.add(subtotal, contingency)
        return {
            "package": package.key,
            "name": package.name,
            "case": case,
            "hours": pc.total_hours(),
            "labour": pc.labour_cost(self.rates, self.assignment),
            "cash": pc.cash_cost(),
            "direct": direct,
            "admin_overhead": admin,
            "contingency": contingency,
            "total": total,
            "unknowns": list(pc.unknowns),
        }

    def case_summary(self, case: str) -> dict:
        """Totals for one effort case, with the unknowns quarantined.

        `total_cost` is UNKNOWN when any package is incomplete. `known_subtotal`
        is the cost of the packages we CAN cost -- useful, and explicitly a
        floor rather than a total, because the missing packages can only add.
        """
        rows = [self.package_cost(p, case) for p in self.packages]
        incomplete = [r["package"] for r in rows if is_unknown(r["total"])]
        total = money.add(*[r["total"] for r in rows])
        known_subtotal = money.add(*[r["total"] for r in rows if not is_unknown(r["total"])])
        total_hours = money.add(*[r["hours"] for r in rows])

        if is_unknown(total):
            margin = UNKNOWN
            margin_pct = UNKNOWN
        else:
            margin = self.base_fee - total
            margin_pct = ((margin / self.base_fee) * Decimal("100")
                          ).quantize(Decimal("0.01")) if self.base_fee else UNKNOWN
        return {
            "case": case,
            "rows": rows,
            "total_cost": total,
            "known_subtotal": known_subtotal,
            "incomplete_packages": incomplete,
            "total_hours": total_hours,
            "revenue": self.base_fee,
            "contribution_margin": margin,
            "contribution_margin_pct": margin_pct,
            "computable": not incomplete,
        }

    # -- reasoning under partial information ----------------------------
    #
    # "An estimate is missing, therefore we know nothing" is as wrong as
    # treating the gap as zero. Cost lines cannot be negative, so the cost of
    # the packages we CAN price is a floor on the whole bid. If that floor
    # already exceeds the fee, the missing estimate cannot rescue it, and the
    # bid loses money whatever the unknown turns out to be. That is a sound
    # conclusion from incomplete data, and it is the one a bidder most needs.
    VERDICTS = ("MARGIN_COMPUTED", "LOSS_CERTAIN_DESPITE_UNKNOWNS", "NOT_COMPUTABLE")

    def verdict(self, case: str) -> dict:
        summary = self.case_summary(case)
        if summary["computable"]:
            return {
                "case": case,
                "verdict": "MARGIN_COMPUTED",
                "margin": summary["contribution_margin"],
                "margin_pct": summary["contribution_margin_pct"],
                "explanation": "Every package is costed; the margin is a computed figure.",
            }
        floor = summary["known_subtotal"]
        missing = summary["incomplete_packages"]
        if not is_unknown(floor) and floor >= self.base_fee:
            shortfall = floor - self.base_fee
            return {
                "case": case,
                "verdict": "LOSS_CERTAIN_DESPITE_UNKNOWNS",
                "margin": UNKNOWN,
                "margin_pct": UNKNOWN,
                "floor_cost": floor,
                "minimum_loss": shortfall,
                "explanation": (
                    f"The packages that can be costed already total "
                    f"{money.fmt_money(floor)} against a {money.fmt_money(self.base_fee)} fee. "
                    f"The missing estimates in {', '.join(missing)} can only add cost, never "
                    f"subtract it, so this case loses at least {money.fmt_money(shortfall)} "
                    f"whatever those estimates turn out to be. The exact margin is still "
                    f"unknown; the sign of it is not."),
            }
        headroom = self.base_fee - floor
        return {
            "case": case,
            "verdict": "NOT_COMPUTABLE",
            "margin": UNKNOWN,
            "margin_pct": UNKNOWN,
            "floor_cost": floor,
            "remaining_headroom": headroom,
            "explanation": (
                f"Costed packages total {money.fmt_money(floor)}, leaving "
                f"{money.fmt_money(headroom)} of the fee before this case turns to a loss. "
                f"Whether it does depends entirely on {', '.join(missing)}, which is not "
                f"estimated. No margin is reported, because any number here would be a guess "
                f"presented as an answer."),
        }

    def resolve(self, resolutions: dict) -> "Model":
        """Return a copy with missing estimates supplied.

        The point of this is to price the unknown rather than argue about it:
        an operator supplies the figure they believe, and the model says what
        it does to the bid. The resolved values are marked so a reader can
        never mistake a supplied assumption for an original estimate.
        """
        raw = json.loads(json.dumps(self._raw))
        applied = []
        for target, values in resolutions.items():
            try:
                pkg_key, line = target.split(".", 1)
            except ValueError:
                raise ModelError(
                    f"resolution target {target!r} must look like WP5.correction_hours") from None
            if line not in EFFORT_LINES and line not in CASH_LINES:
                raise ModelError(f"resolution {target!r}: unknown cost line {line!r}")
            pkg = next((p for p in raw["packages"] if p["key"] == pkg_key), None)
            if pkg is None:
                raise ModelError(f"resolution {target!r}: no package {pkg_key!r}")
            for case in CASES:
                if case not in values:
                    raise ModelError(
                        f"resolution {target!r}: supply all three cases; a resolution for "
                        f"one case only would silently keep the others UNKNOWN")
                if pkg["effort"][case].get(line) is not None:
                    raise ModelError(
                        f"resolution {target!r}: {case}.{line} already has an estimate "
                        f"({pkg['effort'][case][line]}). Resolving it would overwrite real "
                        f"input with an assumption.")
                pkg["effort"][case][line] = values[case]
            applied.append(target)
        resolved = Model(raw)
        resolved.resolved_targets = tuple(sorted(applied))
        return resolved

    def blended_rate(self) -> Decimal:
        """Hours-weighted blended rate at the expected case.

        Weighted by where the hours actually are, not a plain average of the
        rate card -- an unweighted mean would quietly assume every line uses
        the same number of hours.
        """
        weighted = Decimal("0")
        total = Decimal("0")
        for p in self.packages:
            pc = p.cases["expected"]
            for line in EFFORT_LINES:
                h = pc.effort[line]
                if is_unknown(h):
                    return UNKNOWN
                weighted += h * self.rates[self.assignment[line]].amount
                total += h
        if total == 0:
            return UNKNOWN
        return (weighted / total).quantize(money.CENT)

    def break_even_hours(self, case: str = "expected"):
        """How many hours the fee covers before it stops covering them.

        Returned as a pair: the hours the fee buys at the blended rate after
        non-labour cost, and the hours actually planned. The gap is the margin
        expressed in the unit the team actually spends.
        """
        summary = self.case_summary(case)
        blended = self.blended_rate()
        if is_unknown(blended) or is_unknown(summary["total_cost"]):
            return {"case": case, "break_even_hours": UNKNOWN, "planned_hours":
                    summary["total_hours"], "headroom_hours": UNKNOWN,
                    "reason": "an effort estimate is missing, so the blended rate and the "
                              "break-even point cannot be computed"}
        # Non-labour cost is carried before a single hour is paid for.
        non_labour = money.add(*[money.add(r["cash"], r["admin_overhead"], r["contingency"])
                                 for r in summary["rows"]])
        if is_unknown(non_labour):
            return {"case": case, "break_even_hours": UNKNOWN,
                    "planned_hours": summary["total_hours"], "headroom_hours": UNKNOWN,
                    "reason": "a non-labour cost line is missing"}
        coverable = self.base_fee - non_labour
        be = (coverable / blended).quantize(Decimal("0.01")) if blended else UNKNOWN
        headroom = be - summary["total_hours"] if not is_unknown(be) else UNKNOWN
        return {"case": case, "break_even_hours": be,
                "planned_hours": summary["total_hours"], "headroom_hours": headroom,
                "blended_rate": blended, "non_labour_cost": non_labour, "reason": ""}

    @classmethod
    def from_json_file(cls, path: str) -> "Model":
        with open(path, "r", encoding="utf-8") as fh:
            try:
                raw = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ModelError(f"{path}: not valid JSON ({exc})") from exc
        return cls(raw)
