#!/usr/bin/env python3
"""Cost workbook, assumptions sheet and sensitivity table for the base fee.

    python3 analyze.py                                  # model as supplied
    python3 analyze.py --resolve WP5.correction_hours=14,22,40
    python3 analyze.py --check                          # reconcile only, exit 1 on error

Writes Markdown (the workbook), CSV (the per-package sheet) and JSON (machine
readable) to --out. Deterministic: no clock, no randomness, sorted traversal, so
a second operator gets byte-identical files.

Python 3 standard library only. No network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal

import cost_model
import money
import sensitivity
from money import UNKNOWN, is_unknown

CASE_LABEL = {"low": "Low", "expected": "Expected", "high": "High"}


def _j(value):
    """JSON-safe: Decimal to string, UNKNOWN to the literal word."""
    if is_unknown(value):
        return "UNKNOWN"
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _j(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_j(v) for v in value]
    return value


def assumptions_markdown(model: cost_model.Model) -> str:
    out = ["## Assumptions sheet", "",
           "Every figure in this section is an **assumption**, not an agreed or observed "
           "value. Nothing here has been confirmed with the University or with Clark's.", "",
           "### Rates", "",
           "| Rate | Assumed | Basis | Note |", "|---|---|---|---|"]
    for key in sorted(model.rates):
        r = model.rates[key]
        out.append(f"| **{r.label}** | {money.fmt_money(r.amount)}/h | `{r.basis}` | {r.note} |")
    out += ["", "### Overheads", "",
            "| Assumption | Value | What it covers |", "|---|---|---|",
            f"| Admin overhead | {model.admin_overhead_pct}% | Non-billed coordination load, "
            f"applied to direct cost. |",
            f"| Contingency | {model.contingency_pct}% | Re-work not already carried in each "
            f"package's correction hours. |", "",
            "### Commercial facts (given, not derived)", "",
            "| Item | Amount |", "|---|---|",
            f"| Base fee | {money.fmt_money(model.base_fee)} |",
            f"| Optional readout | {money.fmt_money(model.option_fee)} |"]
    for m in model.milestones:
        out.append(f"| {m['key']} - {m['label']} ({m['share_pct']}%) | "
                   f"{money.fmt_money(m['amount'])} |")
    out.append("")
    return "\n".join(out)


def workbook_markdown(model: cost_model.Model) -> str:
    out = [f"# {model.title}", "", f"> {model.disclaimer}", ""]
    if model.resolved_targets:
        out += ["> **Resolved inputs:** " + ", ".join(model.resolved_targets) +
                " were supplied at run time and are assumptions, not original estimates.", ""]
    if model.errors:
        out += ["## Reconciliation ERRORS", ""]
        out += [f"- {e}" for e in model.errors] + [""]
    else:
        out += ["Reconciles to the quoted commercial facts: milestones sum to the base fee and "
                "each matches its stated share.", ""]

    out += ["## Bottom-up cost by work package", ""]
    for case in cost_model.CASES:
        summary = model.case_summary(case)
        out += [f"### {CASE_LABEL[case]} effort case", "",
                "| Package | Hours | Labour | Compute/tooling | Admin overhead | Contingency | "
                "Total | Unknowns |", "|---|---|---|---|---|---|---|---|"]
        for r in summary["rows"]:
            unknown_note = ", ".join(r["unknowns"]) if r["unknowns"] else "-"
            out.append(
                f"| **{r['package']}** {r['name']} | {money.fmt_hours(r['hours'])} | "
                f"{money.fmt_money(r['labour'])} | {money.fmt_money(r['cash'])} | "
                f"{money.fmt_money(r['admin_overhead'])} | {money.fmt_money(r['contingency'])} | "
                f"**{money.fmt_money(r['total'])}** | {unknown_note} |")
        out.append(f"| | {money.fmt_hours(summary['total_hours'])} | | | | | "
                   f"**{money.fmt_money(summary['total_cost'])}** | |")
        out.append("")

        v = model.verdict(case)
        out += [f"**Verdict: `{v['verdict']}`**", "", v["explanation"], ""]
        if v["verdict"] == "MARGIN_COMPUTED":
            out += [f"Revenue {money.fmt_money(summary['revenue'])} - cost "
                    f"{money.fmt_money(summary['total_cost'])} = **contribution margin "
                    f"{money.fmt_money(summary['contribution_margin'])}** "
                    f"({money.fmt_pct(summary['contribution_margin_pct'])}).", ""]
        else:
            out += [f"Costed packages total {money.fmt_money(summary['known_subtotal'])}. "
                    f"**No margin is reported for this case.** A figure here would be a guess "
                    f"wearing the formatting of an answer.", ""]
    return "\n".join(out)


def breakeven_markdown(model: cost_model.Model) -> str:
    out = ["## Break-even", ""]
    for case in cost_model.CASES:
        be = model.break_even_hours(case)
        if is_unknown(be["break_even_hours"]):
            out += [f"- **{CASE_LABEL[case]}:** not computable - {be['reason']}."]
            continue
        out += [f"- **{CASE_LABEL[case]}:** the fee covers "
                f"**{money.fmt_hours(be['break_even_hours'])}** at the blended rate of "
                f"{money.fmt_money(be['blended_rate'])}/h after "
                f"{money.fmt_money(be['non_labour_cost'])} of non-labour cost. "
                f"Planned: {money.fmt_hours(be['planned_hours'])}. "
                f"Headroom: **{money.fmt_hours(be['headroom_hours'])}**."]
    out.append("")
    out.append("Break-even hours are what the fee buys at the blended rate once non-labour cost "
               "is carried. A negative headroom means the plan spends hours the fee does not "
               "cover.")
    out.append("")
    return "\n".join(out)


def sensitivity_markdown(model: cost_model.Model) -> str:
    sw = sensitivity.sweep(model)
    out = ["## Sensitivity", "",
           f"Every effort case against rate assumptions at "
           f"{', '.join(f'x{f}' for f in sw['rate_steps'])} of the assumed card "
           f"({sw['counts']['total']} scenarios).", "",
           "| Rate factor | Case | Total cost | Margin | Verdict |", "|---|---|---|---|---|"]
    for s in sw["scenarios"]:
        out.append(f"| x{s['rate_factor']} | {CASE_LABEL[s['case']]} | "
                   f"{money.fmt_money(s['total_cost'])} | {money.fmt_money(s['margin'])} | "
                   f"`{s['verdict']}` |")
    out += ["", f"**{sw['conclusion']}**", ""]
    if sw["profitable_only_at_optimistic_corner"]:
        out += ["> Reported as a corner result rather than a margin on purpose. "
                "\"Profitable under some assumptions\" would be true and misleading.", ""]

    for rate_key in sorted(model.rates):
        flip = sensitivity.rate_breakeven(model, "expected", rate_key)
        if is_unknown(flip.get("flips_at", None)) or "flips_at_amount" not in flip:
            out.append(f"- **{model.rates[rate_key].label}:** {flip['reason']}")
        else:
            out.append(
                f"- **{model.rates[rate_key].label}:** the expected case turns profitable only "
                f"{flip['direction']} {money.fmt_money(flip['flips_at_amount'])}/h "
                f"(currently assumed {money.fmt_money(flip['current_amount'])}/h, "
                f"a factor of {flip['flips_at_factor']}).")
    out.append("")
    return "\n".join(out)


def package_csv(model: cost_model.Model) -> str:
    rows = ["package,name,milestone,case,hours,labour,compute_tooling,admin_overhead,"
            "contingency,total,unknowns"]
    for p in model.packages:
        for case in cost_model.CASES:
            r = model.package_cost(p, case)
            def cell(v):
                return "UNKNOWN" if is_unknown(v) else str(v)
            rows.append(",".join([
                r["package"], '"' + r["name"].replace('"', '""') + '"', p.milestone, case,
                cell(r["hours"]), cell(r["labour"]), cell(r["cash"]),
                cell(r["admin_overhead"]), cell(r["contingency"]), cell(r["total"]),
                '"' + ";".join(r["unknowns"]) + '"']))
    return "\n".join(rows) + "\n"


def model_json(model: cost_model.Model) -> str:
    sw = sensitivity.sweep(model)
    payload = {
        "title": model.title,
        "disclaimer": model.disclaimer,
        "resolved_targets": list(model.resolved_targets),
        "reconciliation_errors": model.errors,
        "commercial": {
            "base_fee": str(model.base_fee),
            "option_fee": str(model.option_fee),
            "milestones": [{k: str(v) for k, v in m.items()} for m in model.milestones],
        },
        "assumptions": {
            "rates": {k: {"label": r.label, "amount": str(r.amount), "basis": r.basis,
                          "note": r.note} for k, r in sorted(model.rates.items())},
            "admin_overhead_pct": str(model.admin_overhead_pct),
            "contingency_pct": str(model.contingency_pct),
        },
        "cases": {case: _j({
            "total_cost": model.case_summary(case)["total_cost"],
            "known_subtotal": model.case_summary(case)["known_subtotal"],
            "total_hours": model.case_summary(case)["total_hours"],
            "contribution_margin": model.case_summary(case)["contribution_margin"],
            "contribution_margin_pct": model.case_summary(case)["contribution_margin_pct"],
            "incomplete_packages": model.case_summary(case)["incomplete_packages"],
            "verdict": model.verdict(case)["verdict"],
            "explanation": model.verdict(case)["explanation"],
            "break_even": model.break_even_hours(case),
        }) for case in cost_model.CASES},
        "sensitivity": _j({"counts": sw["counts"], "conclusion": sw["conclusion"],
                           "profitable_only_at_optimistic_corner":
                               sw["profitable_only_at_optimistic_corner"],
                           "scenarios": sw["scenarios"]}),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def full_markdown(model: cost_model.Model) -> str:
    return "\n".join([workbook_markdown(model), assumptions_markdown(model),
                      breakeven_markdown(model), sensitivity_markdown(model),
                      "## What this model does not know", "",
                      "- The actual loaded rates. Every rate here is `ASSUMED`; no rate card has "
                      "been agreed, so every margin figure moves with them.",
                      "- The real correction workload, which depends on the volume of "
                      "consolidated University comments and is not knowable before the draft "
                      "is reviewed.",
                      "- Whether onsite attendance is required for the base packages. Travel is "
                      "excluded here and is carried separately in the readout option.",
                      "- The actual split of work between Clark's and TJLabs, which changes who "
                      "carries which hours.", ""])


def _parse_resolution(text: str) -> tuple[str, dict]:
    if "=" not in text:
        raise argparse.ArgumentTypeError(
            f"--resolve expects TARGET=low,expected,high (got {text!r})")
    target, values = text.split("=", 1)
    parts = [v.strip() for v in values.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"--resolve {target}: supply exactly three values (low,expected,high); "
            f"resolving one case only would leave the others UNKNOWN")
    return target.strip(), dict(zip(cost_model.CASES, parts))


def main(argv=None) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=os.path.join(here, "fixtures", "base_fee_model.json"))
    ap.add_argument("--out", default=os.path.join(here, "sample_output"))
    ap.add_argument("--resolve", action="append", default=[],
                    help="TARGET=low,expected,high  e.g. WP5.correction_hours=14,22,40")
    ap.add_argument("--check", action="store_true",
                    help="reconcile against the commercial facts and exit")
    args = ap.parse_args(argv)

    try:
        model = cost_model.Model.from_json_file(args.data)
    except cost_model.ModelError as exc:
        print(f"input rejected: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"no such data file: {args.data}", file=sys.stderr)
        return 2

    if args.resolve:
        resolutions = {}
        for item in args.resolve:
            target, values = _parse_resolution(item)
            resolutions[target] = values
        try:
            model = model.resolve(resolutions)
        except cost_model.ModelError as exc:
            print(f"resolution rejected: {exc}", file=sys.stderr)
            return 2

    if args.check:
        if model.errors:
            print("reconciliation FAILED:")
            for e in model.errors:
                print(f"  - {e}")
            return 1
        print(f"reconciles: milestones sum to {money.fmt_money(model.base_fee)} and each "
              f"matches its stated share.")
        return 0

    os.makedirs(args.out, exist_ok=True)
    artifacts = {
        "cost-workbook.md": full_markdown(model),
        "package-costs.csv": package_csv(model),
        "base-fee-economics.json": model_json(model),
    }
    written = []
    for name in sorted(artifacts):
        body = artifacts[name]
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as fh:
            fh.write(body)
        written.append((name, hashlib.sha256(body.encode("utf-8")).hexdigest()))

    print(model.disclaimer)
    print()
    for name, digest in written:
        print(f"  {digest[:12]}  {name}")
    print()
    for case in cost_model.CASES:
        s = model.case_summary(case)
        v = model.verdict(case)
        print(f"  {CASE_LABEL[case]:9} cost={money.fmt_money(s['total_cost']):>12}  "
              f"margin={money.fmt_money(s['contribution_margin']):>12}  {v['verdict']}")
    sw = sensitivity.sweep(model)
    print()
    print(f"  {sw['conclusion']}")
    return 1 if model.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
