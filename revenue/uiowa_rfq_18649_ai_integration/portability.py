"""Portability, made countable.

"We can swap providers later" is the most confidently asserted and least evidenced
claim in an AI integration plan. This module refuses to accept it as an adjective.
It answers one question with a number and a named method:

    When the underlying capability is replaced, HOW MANY PLACES IN THE CODE CHANGE?

Two independent mechanisms, because one alone is gameable:

  1. scan_module_independence() -- a static scan of a real source file for provider
     symbols. Evidence that a specific module is or is not coupled, right now.
  2. swap_blast_radius() -- scoring of a declared code-surface inventory, for the
     parts of the estate nobody is going to paste into a scanner.

Honesty rule, enforced in code: an un-inventoried surface is UNKNOWN. It never
becomes zero. A total computed with UNKNOWNs present is reported as a FLOOR and the
band is INSUFFICIENT_EVIDENCE -- not "contained".
"""

import pathlib
import re

from unknowns import UNKNOWN, coerce, is_unknown, partition

# --------------------------------------------------------------- surface model
# weight = how many edit points one instance of this surface typically costs on a
# swap. Anything above 1 is there because the surface PROPAGATES: a vendor type or
# a unit convention leaks outward and drags its call sites with it.

SURFACES = {
    "direct_call_sites": {
        "weight": 1,
        "label": "Direct invocations of the capability outside an adapter",
        "why": "Each one is an edit even in the best case.",
    },
    "wire_shape_reads": {
        "weight": 1,
        "label": "Reads of provider response fields in workflow code",
        "why": "Response envelopes differ between capability providers more than "
               "request shapes do.",
    },
    "vendor_error_handlers": {
        "weight": 1,
        "label": "except clauses naming a provider-specific exception type",
        "why": "Error taxonomies are never portable and are usually forgotten until "
               "the first outage after the swap.",
    },
    "prompt_or_param_constructions": {
        "weight": 1,
        "label": "Prompt or parameter construction tied to one provider's dialect",
        "why": "Behavior, not just syntax: the same instruction text does not "
               "produce the same output across capability implementations.",
    },
    "auth_config_points": {
        "weight": 1,
        "label": "Credential / endpoint configuration points",
        "why": "Cheap per instance, but each is a deployment-time failure mode.",
    },
    "sdk_type_imports_outside_adapter": {
        "weight": 2,
        "label": "Provider SDK types imported into workflow modules",
        "why": "Types propagate through signatures; one import typically forces "
               "edits in the modules that call it.",
    },
    "unit_or_taxonomy_conversions_outside_adapter": {
        "weight": 2,
        "label": "Confidence-scale or category-name conversion done in workflow code",
        "why": "Silent correctness risk: percent vs fraction, upper vs lower case "
               "categories. Misses here are not compile errors.",
    },
    "observability_fields_bound_to_vendor_schema": {
        "weight": 1,
        "label": "Dashboards / alerts keyed to provider-specific field names",
        "why": "The swap succeeds and the monitoring silently goes blank.",
    },
}

BANDS = (
    (0, 2, "CONTAINED", "Swap is an adapter-sized change."),
    (3, 9, "PARTIAL", "Swap is a scoped project; workflow code is touched."),
    (10, None, "PERVASIVE", "Swap is a rewrite of the integration, not a substitution."),
)


def band_for(points: int):
    for low, high, name, note in BANDS:
        if points >= low and (high is None or points <= high):
            return name, note
    return "PERVASIVE", BANDS[-1][3]


# -------------------------------------------------------- 1. the static scanner

DEFAULT_FORBIDDEN = (
    # provider module / symbol names from the worked example
    "fake_alpha", "fake_beta", "AlphaTimeout", "AlphaRefused", "BetaUnavailable",
    "BetaSlowLane", "_AlphaWireClient", "_BetaWireClient",
    "AlphaClassificationAdapter", "BetaClassificationAdapter",
    # provider wire field names that must never appear in workflow code
    "confidence_pct", "category_name", "taxonomy_version",
)


def scan_module_independence(path, forbidden_symbols=DEFAULT_FORBIDDEN):
    """Scan one source file for provider coupling. Returns a findings dict.

    Comment and docstring text is scanned too, on purpose: a rule that only checks
    executable lines is trivially defeated and, more usefully, a file that has to
    TALK about the provider usually also has to import it eventually.
    """
    path = pathlib.Path(path)
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    violations = []
    for symbol in forbidden_symbols:
        pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
        for number, line in enumerate(lines, start=1):
            if pattern.search(line):
                violations.append({"symbol": symbol, "line": number,
                                   "text": line.strip()[:120]})
    violations.sort(key=lambda v: (v["line"], v["symbol"]))
    return {
        "module": path.name,
        "independent": not violations,
        "violation_count": len(violations),
        "distinct_symbols": sorted({v["symbol"] for v in violations}),
        "violations": violations,
    }


# --------------------------------------------------- 2. declared-inventory score

def swap_blast_radius(inventory, system_id="(unnamed)"):
    """Score a declared code-surface inventory.

    inventory: {surface_key: count | "unknown"}. Unlisted surfaces are UNKNOWN --
    omission is not evidence of absence, and this function will not pretend it is.
    """
    full = {key: coerce(inventory.get(key, UNKNOWN)) for key in SURFACES}
    known, unknown_keys = partition(full)

    bad = [k for k, v in known.items() if not isinstance(v, int) or v < 0]
    if bad:
        raise ValueError(f"surface counts must be non-negative integers or UNKNOWN: {bad}")

    unexpected = sorted(set(inventory) - set(SURFACES))
    contributions = {k: known[k] * SURFACES[k]["weight"] for k in known}
    points = sum(contributions.values())

    if unknown_keys:
        band, note = "INSUFFICIENT_EVIDENCE", (
            "Some code surfaces were not inventoried. The point total below is a "
            "FLOOR over the surfaces that were counted; the real figure can only be "
            "higher. No band is assigned."
        )
        total_is_floor = True
    else:
        band, note = band_for(points)
        total_is_floor = False

    return {
        "system_id": system_id,
        "edit_points": points,
        "total_is_floor": total_is_floor,
        "band": band,
        "band_note": note,
        "counted_surfaces": {k: {"count": known[k],
                                 "weight": SURFACES[k]["weight"],
                                 "edit_points": contributions[k]}
                             for k in sorted(known)},
        "uncounted_surfaces_unknown": unknown_keys,
        "unexpected_keys_ignored": unexpected,
        "method": "edit_points = sum(count * weight) over INVENTORIED surfaces only",
    }


def render_portability_markdown(scores):
    out = ["# Provider-swap blast radius (portability)", "",
           "**Method.** `edit_points = sum(count x weight)` over the code surfaces that "
           "were actually inventoried. Weight > 1 marks a surface that propagates "
           "(a vendor type or unit convention drags its call sites with it).", "",
           "Bands: `CONTAINED` 0-2 edit points - `PARTIAL` 3-9 - `PERVASIVE` 10+ - "
           "`INSUFFICIENT_EVIDENCE` when any surface was not inventoried.", "",
           "| System | Edit points | Total is | Band | Uncounted (UNKNOWN) |",
           "|---|---|---|---|---|"]
    for score in scores:
        floor = "a FLOOR" if score["total_is_floor"] else "complete"
        unknown = ", ".join(score["uncounted_surfaces_unknown"]) or "none"
        out.append(f"| {score['system_id']} | {score['edit_points']} | {floor} | "
                   f"`{score['band']}` | {unknown} |")
    out += ["", "## Per-system detail", ""]
    for score in scores:
        out.append(f"### {score['system_id']}")
        out.append("")
        out.append(f"{score['band_note']}")
        out.append("")
        out.append("| Surface | Count | Weight | Edit points |")
        out.append("|---|---|---|---|")
        for key, detail in score["counted_surfaces"].items():
            out.append(f"| {SURFACES[key]['label']} | {detail['count']} | "
                       f"{detail['weight']} | {detail['edit_points']} |")
        if score["uncounted_surfaces_unknown"]:
            out.append("")
            out.append("**Not inventoried -- treated as UNKNOWN, not as zero:**")
            for key in score["uncounted_surfaces_unknown"]:
                out.append(f"- `{key}` - {SURFACES[key]['label']}. {SURFACES[key]['why']}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
