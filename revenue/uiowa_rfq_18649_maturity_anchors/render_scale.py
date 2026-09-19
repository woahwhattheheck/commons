#!/usr/bin/env python3
"""Render the maturity scale, the worked examples, and the UIOWA-022 handoff.

    python3 render_scale.py              # writes 21-maturity-scale.md and sample_output/
    python3 render_scale.py --check      # evaluate the examples, exit 1 on a data error

Deterministic: no clock, no randomness, sorted traversal.
Python 3 standard library only. No network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import anchors

FRAMEWORK_NOTE = (
    "**These anchors are our proposed framework, drafted for RFQ 18649 preparation.** They are "
    "not a University of Iowa finding, not an industry standard, and not a certification scale. "
    "They are offered for discussion and expected to be renamed and adjusted."
)

PATTERNS = {
    "repeatable_practice": "Repeatable practice - the work is recorded happening more than once.",
    "isolated_success": "Isolated success - one real instance, nothing showing it repeats.",
    "policy_only_claim": "Claim without a practice record - the practice is asserted, in a "
                         "document or an interview, but nothing records the work itself.",
    "missing_evidence": "Missing evidence - nothing was supplied. Not a low level.",
    "not_applicable": "Not applicable - the criterion has no subject in this group.",
    "unassessed": "Not assessed - outside the agreed scope this round.",
}


def scale_markdown() -> str:
    out = ["# 21 - Common maturity anchors", "", FRAMEWORK_NOTE, "",
           "One ordinal scale, used unchanged across development, security, deployment and "
           "AI readiness.", "",
           "## Why the scale is bounded by evidence kind", "",
           "A maturity scale scored by counting evidence rewards whoever has the most "
           "documents. A group with ten written policies and no practice outscores a group "
           "that does the work and writes little down, which is the opposite of the truth.",
           "",
           "So the **kind** of evidence sets a ceiling, and volume never buys it:", "",
           "| Evidence kind | Ceiling | Why |", "|---|---|---|"]
    for key in sorted(anchors.EVIDENCE_KINDS, key=lambda k: anchors.EVIDENCE_KINDS[k]["caps_at"]):
        kind = anchors.EVIDENCE_KINDS[key]
        out.append(f"| `{key}` - {kind['label']} | **{kind['caps_at']}** | {kind['why']} |")
    out += ["",
            "**Interview statements need corroboration.** A document states an intended "
            "practice by existing. An interview statement counts toward level 2 only when it "
            "is corroborated (`states_intended_practice`): one person's account is a claim, "
            "and two accounts that disagree are evidence that no practice is defined, which is "
            "level 1.", "",
            "A ceiling is not an award. Holding a policy document does not place a group at "
            "level 2; it means they cannot be **above** it. The level reached is the highest "
            "one whose anchors are actually evidenced, and then the ceiling is applied. The "
            "lower of the two wins.", "",
            "## The levels", ""]
    for level in anchors.LEVELS:
        out += [f"### Level {level['rank']} - {level['label']}", "",
                f"**What this level measures:** {level['measures']}", "",
                "**Observable anchors** - all must be evidenced:", ""]
        out += [f"- {a}" for a in level["observable_anchors"]]
        out += ["", f"**To reach level {level['rank'] + 1}:** {level['to_reach_next']}"
                if level["rank"] < anchors.MAX_RANK else
                f"**Note:** {level['to_reach_next']}", ""]

    out += ["## States that are not levels", "",
            "These answer different questions from \"how mature is this?\". Each carries "
            "`maturity_rank = null`, so nothing can sort it onto the bottom of the scale, and "
            "none is counted as a low level.", "",
            "| Status | Meaning |", "|---|---|"]
    for key, meaning in anchors.NON_RANK_STATUSES.items():
        out.append(f"| `{key}` | {meaning} |")
    out += ["",
            "`not_applicable` requires a stated `applicability_reason`. Without one it is "
            "indistinguishable from an area nobody looked at, which is the failure this "
            "distinction exists to prevent.", "",
            "An assessed criterion with no evidence returns `insufficient_evidence`, **not "
            "level 1**. Level 1 is a finding that the practice is absent; no evidence is a "
            "statement about our own collection.", "",
            "## The four patterns the examples keep apart", "", "| Pattern | Meaning |",
            "|---|---|"]
    for key in ("repeatable_practice", "isolated_success", "policy_only_claim",
                "missing_evidence"):
        out.append(f"| `{key}` | {PATTERNS[key]} |")
    out += ["", "## Handoff to UIOWA-022", "",
            "The rating model in `revenue/uiowa_rfq_18649_rating_model/` states that it does "
            "not invent the maturity scale and takes the rank and label as inputs. This method "
            "emits exactly the fields that model declares: `criterion_id`, `area`, `service`, "
            "`assessment_status`, `maturity_rank`, `maturity_label`, `evidence_ids`. "
            "Composition of those observations, coverage and confidence remain that model's "
            "job, not this one's.", ""]
    return "\n".join(out)


def examples_markdown(doc: dict, assessments: list) -> str:
    out = [f"# 21 - Worked examples: {doc['title']}", "", f"> {doc['disclaimer']}", "",
           FRAMEWORK_NOTE, "",
           "The same scale applied in all four areas, including every state that is not a "
           "level.", "",
           "| Criterion | Area | Service | Level | Pattern | Why not higher |",
           "|---|---|---|---|---|---|"]
    for a in assessments:
        rank = a.rank if a.rank is not None else "-"
        label = a.label if a.rank is not None else f"`{a.status}`"
        out.append(f"| **{a.criterion_id}** | {a.area} | {a.service} | {rank} {label} | "
                   f"`{a.pattern}` | {a.cap_reason} |")
    out += ["", "## Each example in full", ""]
    for a in assessments:
        rank = a.rank if a.rank is not None else "not on the scale"
        out += [f"### {a.criterion_id} - {a.area} / {a.service}", "",
                f"- **Result:** {rank}" + (f" ({a.label})" if a.rank is not None else
                                           f" - `{a.status}`"),
                f"- **Pattern:** {PATTERNS.get(a.pattern, a.pattern)}",
                f"- **Why not higher:** {a.cap_reason}"]
        if a.next_level_requires:
            out.append(f"- **What would raise it:** {a.next_level_requires}")
        if a.notes:
            out.append(f"- **Note:** {a.notes}")
        if a.evidence:
            out += ["- **Evidence supplied:**"]
            for e in a.evidence:
                bits = [f"`{e.kind}` (ceiling {e.caps_at})", e.locator]
                if e.instances > 1:
                    bits.append(f"{e.instances} instances")
                if e.covers_multiple_actors:
                    bits.append("covers more than one person or service")
                if e.exceptions_recorded:
                    bits.append("exceptions recorded")
                if e.measure_defined:
                    bits.append("measure defined")
                if e.change_evidenced:
                    bits.append("change evidenced")
                out.append(f"  - " + " - ".join(bits))
        else:
            out.append("- **Evidence supplied:** none")
        out.append("")
    return "\n".join(out)


def examples_csv(assessments: list) -> str:
    rows = ["criterion_id,area,service,assessment_status,maturity_rank,maturity_label,"
            "evidence_pattern,cap_reason"]
    for a in assessments:
        rank = "" if a.rank is None else str(a.rank)
        rows.append(",".join([
            a.criterion_id, a.area, a.service, a.status,
            rank if rank else "NULL",
            '"' + a.label.replace('"', '""') + '"',
            a.pattern,
            '"' + a.cap_reason.replace('"', '""') + '"']))
    return "\n".join(rows) + "\n"


def rating_model_input(doc: dict, assessments: list) -> str:
    return json.dumps({
        "_note": "Input records for the UIOWA-022 rating model, using that model's declared "
                 "field names. maturity_rank is null for every status that is not a level.",
        "_framework": "Maturity ranks come from OUR PROPOSED anchor framework (UIOWA-021), not "
                      "from a standard and not from University findings.",
        "disclaimer": doc["disclaimer"],
        "criteria": [a.as_rating_model_input() for a in assessments],
    }, indent=2, sort_keys=True) + "\n"


def main(argv=None) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=os.path.join(here, "fixtures", "worked_examples.json"))
    ap.add_argument("--out", default=os.path.join(here, "sample_output"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    try:
        doc = anchors.load(args.data)
        assessments = anchors.evaluate_all(doc["criteria"])
    except anchors.AnchorError as exc:
        print(f"input rejected: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"no such data file: {args.data}", file=sys.stderr)
        return 2

    if args.check:
        for a in assessments:
            rank = a.rank if a.rank is not None else "-"
            print(f"  {a.criterion_id:8} {a.area:13} {str(rank):>2}  {a.pattern}")
        print(f"{len(assessments)} criteria evaluated, no data errors.")
        return 0

    os.makedirs(args.out, exist_ok=True)
    scale_path = os.path.join(here, "21-maturity-scale.md")
    with open(scale_path, "w", encoding="utf-8") as fh:
        fh.write(scale_markdown())

    artifacts = {
        "21-worked-examples.md": examples_markdown(doc, assessments),
        "21-worked-examples.csv": examples_csv(assessments),
        "rating-model-input.json": rating_model_input(doc, assessments),
    }
    written = [("21-maturity-scale.md",
                hashlib.sha256(scale_markdown().encode("utf-8")).hexdigest())]
    for name in sorted(artifacts):
        body = artifacts[name]
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as fh:
            fh.write(body)
        written.append((name, hashlib.sha256(body.encode("utf-8")).hexdigest()))

    print(doc["disclaimer"])
    print()
    for name, digest in written:
        print(f"  {digest[:12]}  {name}")
    print()
    ranked = [a for a in assessments if a.rank is not None]
    print(f"  {len(assessments)} criteria across {len(anchors.AREAS)} areas: "
          f"{len(ranked)} carry a level, {len(assessments) - len(ranked)} are not on the scale.")
    for pattern in sorted({a.pattern for a in assessments}):
        n = sum(1 for a in assessments if a.pattern == pattern)
        print(f"    {pattern:22} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
