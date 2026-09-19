"""Whether a reported measure can carry the claim made from it.

The failure this addresses: an assessment samples 12 change records, finds 7
with a single approval, and the report says "58.3% of changes receive a single
approval". Every step of that is arithmetically correct and the sentence is
still wrong in three separate ways. It implies a resolution of one tenth of a
percentage point from data whose finest possible step is 8.3 points. It states
a rate where the honest statement is a count. And it describes the population
when it measured a sample.

None of that is caught by a citation checker, because the citation resolves, or
by an arithmetic checker, because the arithmetic is right.

Every rule here proposes the honest restatement rather than only objecting.
A checker that says "this is wrong" and stops has moved the work, not done it.

Python 3 standard library only. Deterministic: no clock, no RNG.
"""
from __future__ import annotations

import dataclasses
import json
import math
from typing import Any

ERROR = "error"
WARN = "warning"
INFO = "info"

# Below this many observations, a proportion should be stated as a count.
# Not a statistical threshold -- a readability one: "3 of 4" is honest and
# "75%" invites the reader to generalise.
MIN_DENOMINATOR_FOR_RATE = 8
MIN_N_FOR_MEDIAN = 5
MIN_N_FOR_MEDIAN_AT_ALL = 3

SAMPLING_KINDS = ("CENSUS", "RANDOM", "CONVENIENCE", "SELF_SELECTED", "UNKNOWN")
SCOPES = ("SAMPLE", "POPULATION")
PRESENTATIONS = ("PERCENT", "COUNT")
CLAIMS = ("DESCRIPTIVE", "POPULATION_ABSENCE")


class MeasureError(ValueError):
    """A measure that cannot be checked at all, as opposed to one that fails."""


@dataclasses.dataclass
class Finding:
    code: str
    severity: str
    measure_id: str
    message: str
    restatement: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def sort_key(self):
        order = {ERROR: 0, WARN: 1, INFO: 2}
        return (order.get(self.severity, 9), self.measure_id, self.code)


@dataclasses.dataclass
class Measure:
    id: str
    label: str
    kind: str                  # PROPORTION | MEDIAN | COUNT
    numerator: Any = None      # None means UNKNOWN, never zero
    denominator: Any = None
    reported_value: Any = None
    reported_decimals: int = 0
    observations: list[float] | None = None
    sampling: str = "UNKNOWN"
    scope: str = "SAMPLE"
    components: dict[str, int] | None = None
    stated_total: Any = None
    unit: str = ""
    presentation: str = "PERCENT"
    claim: str = "DESCRIPTIVE"
    population: str = ""
    inference: dict[str, Any] | None = None


def _req(raw: dict, key: str, mid: str):
    if key not in raw:
        raise MeasureError(f"measure {mid!r} is missing required field {key!r}")
    return raw[key]


def load_measures(path: str) -> list[Measure]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict) or raw.get("synthetic") is not True:
        raise MeasureError("the measure set must be explicitly marked synthetic:true")
    if not isinstance(raw.get("measures", []), list):
        raise MeasureError("measures must be a list")
    out = []
    for item in raw.get("measures", []):
        if not isinstance(item, dict):
            raise MeasureError("each measure must be an object")
        mid = item.get("id") or "<unnamed>"
        kind = _req(item, "kind", mid)
        if kind not in ("PROPORTION", "MEDIAN", "COUNT"):
            raise MeasureError(f"measure {mid!r} has unknown kind {kind!r}")
        sampling = item.get("sampling", "UNKNOWN")
        if sampling not in SAMPLING_KINDS:
            raise MeasureError(f"measure {mid!r} has unknown sampling {sampling!r}")
        scope = item.get("scope", "SAMPLE")
        if scope not in SCOPES:
            raise MeasureError(f"measure {mid!r} has unknown scope {scope!r}")
        denominator = item.get("denominator")
        numerator = item.get("numerator")
        measure = Measure(
            id=mid, label=_req(item, "label", mid), kind=kind,
            numerator=numerator, denominator=denominator,
            reported_value=item.get("reported_value"),
            reported_decimals=item.get("reported_decimals", 0),
            observations=item.get("observations"),
            sampling=sampling, scope=scope,
            components=item.get("components"),
            stated_total=item.get("stated_total"),
            unit=item.get("unit", ""),
            presentation=item.get("presentation", "PERCENT"),
            claim=item.get("claim", "DESCRIPTIVE"),
            population=item.get("population", ""),
            inference=item.get("inference"))
        if measure.kind == "PROPORTION":
            _validate_proportion(measure)
        elif measure.inference is not None or measure.claim != "DESCRIPTIVE":
            raise MeasureError("claim and inference fields require kind PROPORTION")
        out.append(measure)
    return sorted(out, key=lambda m: m.id)


def resolvable_step_pp(denominator: int) -> float:
    """The smallest change in a proportion that the data can actually express."""
    return 100.0 / denominator


def _positive_trials(n: int) -> None:
    if type(n) is not int or n <= 0:
        raise MeasureError("trial count must be a positive integer")
    try:
        float(n)
    except OverflowError as exc:
        raise MeasureError("trial count exceeds the numeric calculation range") from exc


def rule_of_three_upper_bound(n: int) -> float:
    """Legacy approximate one-sided 95% binomial upper limit, in percent.

    Assumes independent trials with a common event probability. Arithmetic only:
    this helper does not validate a sampling design or license population claims.
    Clip the approximation to the probability domain; reports use the separately
    labeled exact calculation only when its assumptions are supplied.
    """
    _positive_trials(n)
    return min(100.0, 300.0 / n)


def zero_event_upper_bound(n: int, confidence: float) -> float:
    """Exact one-sided zero-event binomial upper limit, as a probability.

    Solve (1-p)**n = 1-confidence. Assumptions must be checked by the caller;
    this is not a two-sided Wilson interval or a posterior probability.
    """
    _positive_trials(n)
    if (type(confidence) not in (int, float)
            or not 0 < confidence < 1 or not math.isfinite(confidence)):
        raise MeasureError("confidence must be a finite number strictly between 0 and 1")
    return -math.expm1(math.log1p(-confidence) / n)


def _validate_proportion(m: Measure) -> None:
    for name, allowed in (("sampling", SAMPLING_KINDS), ("scope", SCOPES),
                          ("presentation", PRESENTATIONS), ("claim", CLAIMS)):
        if getattr(m, name) not in allowed:
            raise MeasureError(f"measure {m.id!r} has unknown {name}")
    for name in ("numerator", "denominator"):
        value = getattr(m, name)
        if value is not None:
            if type(value) is not int or value < 0:
                raise MeasureError(f"measure {m.id!r}: {name} must be a nonnegative integer or null")
            if value:
                _positive_trials(value)
    if (m.numerator is not None and m.denominator is not None
            and m.numerator > m.denominator):
        raise MeasureError(f"measure {m.id!r} has numerator greater than denominator")
    if type(m.reported_decimals) is not int or m.reported_decimals < 0:
        raise MeasureError("reported_decimals must be a nonnegative integer")
    if not isinstance(m.population, str):
        raise MeasureError("population must be a string describing the collection or target")
    if m.inference is not None and not isinstance(m.inference, dict):
        raise MeasureError("inference must be an object or null")


def _check_zero_claim(m: Measure) -> list[Finding]:
    """Keep the observed count, claimed absence, and model inference separate."""
    out: list[Finding] = []
    observed = f"{m.numerator} of {m.denominator} {m.label} observed"
    if m.claim == "POPULATION_ABSENCE":
        if m.numerator != 0:
            out.append(Finding("ABSENCE_CONTRADICTED", ERROR, m.id,
                "the absence claim contradicts the recorded nonzero count", observed))
        elif not (m.sampling == "CENSUS" and m.scope == "POPULATION"
                  and m.population.strip()):
            out.append(Finding("ZERO_OBSERVED_AS_ABSENCE", ERROR, m.id,
                "a recorded zero does not establish the asserted absence in a population; "
                "a complete census can establish absence only in its explicitly named collection",
                observed + "; do not extend this count beyond the examined collection"))
    if m.inference is None:
        return out

    model = m.inference
    confidence = model.get("confidence")
    # RANDOM is a supplied design label, not a proof of independent Bernoulli trials.
    supported = (m.numerator == 0 and m.sampling == "RANDOM"
                 and bool(m.population.strip())
                 and model.get("method") == "BINOMIAL_ZERO_UPPER"
                 and model.get("independent_trials") is True
                 and model.get("constant_probability") is True
                 and isinstance(model.get("rationale"), str)
                 and bool(model["rationale"].strip())
                 and type(confidence) in (int, float)
                 and 0 < confidence < 1 and math.isfinite(confidence))
    if not supported:
        out.append(Finding("ZERO_EVENT_MODEL_UNSUPPORTED", ERROR, m.id,
            "no population limit computed: this method requires zero events, a RANDOM "
            "design, a named target, finite confidence in (0,1), and explicit justified "
            "independent-trial and common-probability assumptions; a census needs no "
            "sampling interval for its complete collection",
            observed + "; model-based uncertainty remains UNKNOWN"))
        return out
    bound = zero_event_upper_bound(m.denominator, confidence)
    text = (f"under the stated independent, constant-probability trial assumptions, "
            f"the exact one-sided {100*confidence:g}% BINOMIAL_ZERO_UPPER limit for "
            f"{m.population} is {100*bound:.6g}%; this is model-based, not proof of absence")
    out.append(Finding("ZERO_EVENT_MODEL_LIMIT", INFO, m.id,
        text + "; supplied rationale: " + model["rationale"], observed + "; " + text))
    return out


def check(measures: list[Measure]) -> list[Finding]:
    out: list[Finding] = []
    for m in measures:
        if m.kind not in ("PROPORTION", "MEDIAN", "COUNT"):
            raise MeasureError("unknown measure kind")
        if m.kind != "PROPORTION" and (m.inference is not None or m.claim != "DESCRIPTIVE"):
            raise MeasureError("claim and inference fields require kind PROPORTION")
        if m.kind == "PROPORTION":
            out.extend(_check_proportion(m))
        elif m.kind == "MEDIAN":
            out.extend(_check_median(m))
        if m.components is not None or m.stated_total is not None:
            out.extend(_check_components(m))
    return sorted(out, key=lambda f: f.sort_key())


def _check_proportion(m: Measure) -> list[Finding]:
    _validate_proportion(m)
    out: list[Finding] = []

    if m.denominator is None:
        out.append(Finding(
            "PERCENTAGE_WITHOUT_DENOMINATOR", ERROR, m.id,
            "a proportion is reported with no denominator; the reader cannot tell "
            "whether it came from 4 records or 4,000, and an absent denominator is "
            "not the same as a large one",
            restatement="state the denominator, or report the numerator as a count"))
        return out

    if m.denominator == 0:
        out.append(Finding(
            "EMPTY_DENOMINATOR", ERROR, m.id,
            "the denominator is zero: nothing was observed, so no proportion exists",
            restatement="report UNKNOWN; zero observations is not zero percent"))
        return out

    if m.numerator is None:
        out.append(Finding(
            "NUMERATOR_UNKNOWN", ERROR, m.id,
            f"the denominator is {m.denominator} but the numerator was never "
            "recorded; this measure stays UNKNOWN rather than defaulting to zero"))
        return out

    if m.presentation == "PERCENT":
        step = resolvable_step_pp(m.denominator)

        if m.denominator < MIN_DENOMINATOR_FOR_RATE:
            out.append(Finding(
                "DENOMINATOR_TOO_SMALL", ERROR, m.id,
                f"a percentage from {m.denominator} observations invites the reader to "
                f"generalise from {m.denominator} observations; one record changing "
                f"moves this figure by {step:.1f} percentage points",
                restatement=f"{m.numerator} of {m.denominator} {m.label}"))

        else:
            # Only checked when the measure is large enough to be stated as a rate at
            # all. Below that, DENOMINATOR_TOO_SMALL already covers it, and two
            # findings for one defect makes the counts untrustworthy.
            implied_resolution = 10.0 ** (-m.reported_decimals)
            if implied_resolution < step / 2.0:
                rounded = round(100.0 * m.numerator / m.denominator)
                # A decimal place on a small sample is a stronger claim than a whole
                # percent, so it is the error and the whole percent is the warning.
                severity = ERROR if m.reported_decimals > 0 else WARN
                out.append(Finding(
                    "FALSE_PRECISION", severity, m.id,
                    f"reported to {m.reported_decimals} decimal place(s), implying a "
                    f"resolution of {implied_resolution:g} percentage points, but "
                    f"{m.denominator} observations can only resolve steps of "
                    f"{step:.2f} points",
                    restatement=(f"{m.numerator} of {m.denominator}"
                                 f" (about {rounded}%)")))

    out.extend(_check_zero_claim(m))

    if m.scope == "POPULATION" and m.sampling in ("CONVENIENCE", "SELF_SELECTED",
                                                  "UNKNOWN"):
        out.append(Finding(
            "SAMPLE_STATED_AS_POPULATION", ERROR, m.id,
            f"this is phrased about the population but the sample is "
            f"{m.sampling}; a {m.sampling.lower().replace('_', '-')} sample does "
            "not license a statement about everything",
            restatement=f"of the {m.denominator} {m.label} examined, "
                        f"{m.numerator} ..."))
    return out


def _check_median(m: Measure) -> list[Finding]:
    out: list[Finding] = []
    observations = m.observations
    if not observations:
        out.append(Finding(
            "MEDIAN_WITHOUT_OBSERVATIONS", ERROR, m.id,
            "a median is reported with no underlying observations recorded",
            restatement="supply the observations or report UNKNOWN"))
        return out
    n = len(observations)
    if n < MIN_N_FOR_MEDIAN_AT_ALL:
        out.append(Finding(
            "MEDIAN_OF_TOO_FEW", ERROR, m.id,
            f"a median of {n} observation(s) is the observation(s) themselves "
            "dressed as a statistic",
            restatement="list the "
                        + ", ".join(f"{v:g}" for v in sorted(observations))
                        + (f" {m.unit}" if m.unit else "") + " observed"))
    elif n < MIN_N_FOR_MEDIAN:
        low, high = min(observations), max(observations)
        out.append(Finding(
            "MEDIAN_OF_FEW", WARN, m.id,
            f"a median of {n} observations carries a wide spread "
            f"({low:g} to {high:g} {m.unit})".rstrip(),
            restatement=f"median over n={n}, range {low:g}-{high:g} {m.unit}".rstrip()))
    return out


def _check_components(m: Measure) -> list[Finding]:
    out: list[Finding] = []
    if m.components is None:
        return out
    if any(v is None for v in m.components.values()):
        missing = sorted(k for k, v in m.components.items() if v is None)
        out.append(Finding(
            "COMPONENT_UNKNOWN", ERROR, m.id,
            f"component(s) {', '.join(missing)} were never recorded, so the total "
            "cannot be checked; they are not treated as zero",
            restatement="record the missing component(s) or report the total as UNKNOWN"))
        return out
    summed = sum(m.components.values())
    if m.stated_total is not None and summed != m.stated_total:
        out.append(Finding(
            "COMPONENT_SUM_MISMATCH", ERROR, m.id,
            f"components total {summed} but the stated total is {m.stated_total}",
            restatement=f"reconcile to {summed} or correct the components"))
    return out


def render_text(measures: list[Measure], findings: list[Finding]) -> str:
    errors = [f for f in findings if f.severity == ERROR]
    warns = [f for f in findings if f.severity == WARN]
    lines = [
        "sample soundness",
        "=" * 72,
        f"measures checked : {len(measures)}",
        f"result           : {'FAIL' if errors else 'PASS'}"
        f"  ({len(errors)} error, {len(warns)} warning)",
        "",
    ]
    for f in findings:
        lines.append(f"  [{f.severity}] {f.code}  {f.measure_id}")
        lines.append(f"      {f.message}")
        if f.restatement:
            lines.append(f"      say instead: {f.restatement}")
    if not findings:
        lines.append("  No configured rule reported a finding. Sampling, scope and claim")
        lines.append("  labels are supplied inputs, not independently verified evidence.")
    lines.append("")
    return "\n".join(lines)
