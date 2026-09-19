#!/usr/bin/env python3
"""Cross-lane UNKNOWN-propagation screen (University of Iowa RFQ 18649).

Several delivery-kit lanes now carry the same recommendation, finding and
work-item identifiers. Each one handles "nobody estimated this" carefully on its
own, and each one says it differently: `null` plus a boolean plus `NOT_RANKED`
in one lane, the string `"UNKNOWN"` plus `PARTIAL` plus `complete: false` in
another. Nothing checks that a value recorded as UNKNOWN in the lane that owns
it is still UNKNOWN everywhere it appears downstream.

This screen reads the landed tree and answers exactly that question, for the
fields it can honestly align.

What it will not do
-------------------
* **It never says which lane is right.** When two lanes disagree about the same
  identifier and field, that is a question for a person. The screen reports both
  sides with exact file paths and stops. An UNKNOWN that became a number may be a
  legitimate later estimate or a fabrication; nothing in the bytes distinguishes
  them.
* **It never infers a field correspondence.** Fields are aligned by exact name,
  or by an entry in a declared crosswalk that records who asserted the
  equivalence and why. A name-similarity matcher would manufacture traceability,
  which is worse than finding none.
* **It never reports a clean result as correctness.** "No conflicts" means the
  screen found no disagreement in the fields it could align, and the report
  always states how many fields it could *not* align. That count is a finding in
  its own right, not a footnote.
* **It never scores, rates, grades or marks compliant.** No lane and no author is
  assessed. The strongest sentence this tool emits is "these two files
  disagree".
* **It never writes into the tree it reads.** Output goes only where the caller
  asks. `verify_readonly` hashes the scanned tree before and after and asserts
  byte-identical.

Offline, Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# --------------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------------

#: Identifier prefixes the delivery kit uses. Anything else is not treated as a
#: shared identifier, because guessing at ID shapes is how a screen invents
#: cross-lane links that were never there.
ID_PREFIXES: Tuple[str, ...] = (
    "REC-SYN-",
    "FND-SYN-",
    "EV-SYN-",
    "OBS-SYN-",
    "CR-SYN-",
    "WI-",
    "OPP-",
    "ECON-",
)

#: "Nobody supplied a value." Observed in the landed tree.
NO_ESTIMATE_TOKENS: Tuple[str, ...] = (
    "UNKNOWN",
    "NOT_RANKED",
    "NEEDS_ESTIMATE",
    "NO_RESOURCING_DATA",
    "NOT QUOTED",
    "NOT_ASSESSED",
    "UNASSESSED",
    "TBD",
    "N/A",
    "NA",
    "NONE",
    "POPULATION_UNKNOWN",
)

#: "Something was supplied, but it is not settled." Kept SEPARATE from the set
#: above on purpose. PARTIAL does not mean nobody looked -- it means somebody
#: looked and the answer is incomplete. Folding the two together would be the
#: same conflation this screen exists to detect, committed by the screen itself.
#: Both families are treated as *unsettled* when checking whether a value
#: hardened, because a PARTIAL silently becoming SUPPORTED is the same class of
#: concern; but every output states which family a given claim came from.
INCOMPLETE_TOKENS: Tuple[str, ...] = (
    "PARTIAL",
    "UNRESOLVED",
    "HOLD",
    "NOT_DEMONSTRATED",
    "INCONCLUSIVE",
)

KNOWN = "KNOWN"
UNKNOWN = "UNKNOWN"
INCOMPLETE = "INCOMPLETE"
ZERO = "ZERO"
EMPTY = "EMPTY"

#: Classes that mean "this is not a settled value".
UNSETTLED = (UNKNOWN, INCOMPLETE)

CONSISTENT = "CONSISTENT"
UNKNOWN_HARDENED = "UNKNOWN_HARDENED"
UNKNOWN_BECAME_ZERO = "UNKNOWN_BECAME_ZERO"

#: Severity order for reporting. UNKNOWN_BECAME_ZERO first because a zero is the
#: one substitution that silently survives every downstream sum.
FINDING_ORDER = (UNKNOWN_BECAME_ZERO, UNKNOWN_HARDENED, CONSISTENT)

#: The valued side sits in a lane that never records the unknown for this pair.
#: Something crossed a lane boundary and changed. This is the real signal.
CROSS_LANE = "CROSS_LANE"

#: The lane holding the value ALSO records the unknown for the same pair
#: somewhere else in its own files. That is one lane disagreeing with itself
#: across its own variants, which is what a checker's deliberately-broken
#: fixtures look like from outside -- a negative test copy differs from the
#: clean copy on purpose. It is NOT evidence that an unknown failed to survive a
#: handoff, and reporting it as one would manufacture a defect out of somebody
#: else's passing test suite.
INTRA_LANE_VARIANT = "INTRA_LANE_VARIANT"

#: Path segments a lane conventionally uses for its own negative fixtures. Used
#: only as reported CONTEXT alongside the structural rule above, never as the
#: rule itself -- a directory name is a convention, not a guarantee.
NEGATIVE_FIXTURE_HINTS = (
    "mismatched",
    "rejection",
    "hostile",
    "invalid",
    "broken",
    "negative",
    "malformed",
)

SCANNED_SUFFIXES = (".json", ".csv")

#: Directories that hold build droppings rather than delivered artifacts.
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", "node_modules"}


class ScanError(ValueError):
    """Input the screen refuses to interpret by guessing."""


# --------------------------------------------------------------------------------
# Value classification
# --------------------------------------------------------------------------------


def classify_value(value: Any) -> str:
    """KNOWN / UNKNOWN / ZERO / EMPTY.

    ZERO is deliberately separate from KNOWN. A real zero is a legitimate
    estimate, but when it sits opposite another lane's UNKNOWN it is the single
    most dangerous value in the kit: it is the substitution that survives every
    downstream sum without ever looking wrong.
    """
    if value is None:
        return UNKNOWN
    if isinstance(value, bool):
        return KNOWN
    if isinstance(value, (int, float)):
        return ZERO if value == 0 else KNOWN
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return EMPTY
        upper = token.upper()
        if upper in NO_ESTIMATE_TOKENS:
            return UNKNOWN
        if upper in INCOMPLETE_TOKENS:
            return INCOMPLETE
        # "$0.00", "0", "0.0"
        stripped = upper.replace("$", "").replace(",", "").rstrip("%")
        try:
            return ZERO if float(stripped) == 0 else KNOWN
        except ValueError:
            return KNOWN
    return KNOWN


def is_identifier(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(ID_PREFIXES)


# --------------------------------------------------------------------------------
# Claim extraction
# --------------------------------------------------------------------------------


class Claim:
    """One lane saying one thing about one identifier's one field."""

    __slots__ = ("identifier", "field", "value", "kind", "lane", "path", "locator")

    def __init__(
        self,
        identifier: str,
        field: str,
        value: Any,
        lane: str,
        path: str,
        locator: str,
    ) -> None:
        self.identifier = identifier
        self.field = field
        self.value = value
        self.kind = classify_value(value)
        self.lane = lane
        self.path = path
        self.locator = locator

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identifier": self.identifier,
            "field": self.field,
            "value": self.value,
            "value_class": self.kind,
            "lane": self.lane,
            "path": self.path,
            "locator": self.locator,
        }


def _record_identifier(record: Dict[str, Any]) -> Optional[str]:
    """The identifier a JSON object is *about*, or None.

    Only a key ending in `_id` counts, and its value must match a known prefix.
    A nested object that merely mentions an identifier in prose is not a claim
    about it.
    """
    for key, value in record.items():
        if key.endswith("_id") and is_identifier(value):
            return value
    return None


def claims_from_json(
    payload: Any, lane: str, path: str
) -> List[Claim]:
    """Walk JSON and emit one claim per scalar field of each identified object."""
    found: List[Claim] = []

    def walk(node: Any, pointer: str) -> None:
        if isinstance(node, dict):
            identifier = _record_identifier(node)
            if identifier is not None:
                for key, value in node.items():
                    if key.endswith("_id"):
                        continue
                    if isinstance(value, (dict, list)):
                        continue
                    found.append(
                        Claim(identifier, key, value, lane, path, pointer or "$")
                    )
            for key, value in node.items():
                walk(value, f"{pointer}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{pointer}[{index}]")

    walk(payload, "")
    return found


def claims_from_csv(text: str, lane: str, path: str) -> List[Claim]:
    """Rows whose id column holds a known identifier become claims."""
    found: List[Claim] = []
    reader = csv.reader(text.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return found
    id_columns = [
        index
        for index, name in enumerate(header)
        if name.strip().endswith("_id") or name.strip() == "id"
    ]
    if not id_columns:
        return found
    for row_index, row in enumerate(reader, start=2):
        identifier = None
        for index in id_columns:
            if index < len(row) and is_identifier(row[index].strip()):
                identifier = row[index].strip()
                break
        if identifier is None:
            continue
        for index, name in enumerate(header):
            if index in id_columns or index >= len(row):
                continue
            found.append(
                Claim(
                    identifier,
                    name.strip(),
                    row[index],
                    lane,
                    path,
                    f"row {row_index}",
                )
            )
    return found


# --------------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------------


def iter_files(root: str, lane_prefix: str) -> Iterable[Tuple[str, str]]:
    """Yield (lane, path) for every scannable file under root."""
    if not os.path.isdir(root):
        raise ScanError(f"{root} is not a directory")
    for lane in sorted(os.listdir(root)):
        if lane_prefix and not lane.startswith(lane_prefix):
            continue
        lane_dir = os.path.join(root, lane)
        if not os.path.isdir(lane_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(lane_dir):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                if name.endswith(SCANNED_SUFFIXES):
                    yield lane, os.path.join(dirpath, name)


def collect_claims(
    root: str, lane_prefix: str = "uiowa_rfq_18649_"
) -> Tuple[List[Claim], List[Dict[str, str]]]:
    """Read every scannable file. Returns (claims, unreadable files).

    A file that cannot be parsed is reported, never skipped silently: a screen
    that quietly ignores what it could not read is reporting on a smaller tree
    than it claims to.
    """
    claims: List[Claim] = []
    unreadable: List[Dict[str, str]] = []
    for lane, path in iter_files(root, lane_prefix):
        relative = os.path.relpath(path, root)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append({"path": relative, "reason": str(exc)})
            continue
        try:
            if path.endswith(".json"):
                claims.extend(claims_from_json(json.loads(text), lane, relative))
            else:
                claims.extend(claims_from_csv(text, lane, relative))
        except (json.JSONDecodeError, csv.Error) as exc:
            unreadable.append({"path": relative, "reason": str(exc)})
    return claims, unreadable


# --------------------------------------------------------------------------------
# Alignment
# --------------------------------------------------------------------------------


class Crosswalk:
    """Declared field equivalences. Nothing is inferred.

    Each entry names a canonical field and the lane-specific field names that
    were *asserted* to mean the same thing, with who asserted it and on what
    basis. An equivalence with no basis is refused, because an unexplained
    mapping is indistinguishable from a guess.
    """

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.entries: Dict[Tuple[str, str], str] = {}
        self.declarations: List[Dict[str, Any]] = []
        if not payload:
            return
        for entry in payload.get("equivalences", []):
            canonical = entry.get("canonical_field")
            basis = entry.get("basis", "")
            asserted_by = entry.get("asserted_by", "")
            if not canonical:
                raise ScanError("each equivalence needs a 'canonical_field'")
            if not basis or not asserted_by:
                raise ScanError(
                    f"equivalence '{canonical}' has no basis/asserted_by. An "
                    f"unexplained field mapping is a guess, and this screen does "
                    f"not carry guesses."
                )
            for member in entry.get("members", []):
                lane = member.get("lane")
                field = member.get("field")
                if not lane or not field:
                    raise ScanError(
                        f"equivalence '{canonical}' has a member without a "
                        f"lane/field"
                    )
                self.entries[(lane, field)] = canonical
            self.declarations.append(
                {
                    "canonical_field": canonical,
                    "asserted_by": asserted_by,
                    "basis": basis,
                    "members": entry.get("members", []),
                }
            )

    def canonical(self, lane: str, field: str) -> str:
        """The aligned field name for this lane's field. Identity by default."""
        return self.entries.get((lane, field), field)


# --------------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------------


def _summarize_sides(
    unknowns: Sequence[Claim], valued: Sequence[Claim]
) -> List[Dict[str, Any]]:
    """Collapse a finding's evidence to distinct (side, lane, value) rows.

    One lane repeating the same value across twenty fixture copies is one claim
    stated twenty times, not twenty claims. Printing all twenty buries the thing
    that actually differs. The full claim list stays in the JSON.
    """
    buckets: Dict[Tuple[str, str, str], List[Claim]] = {}
    for side, group in (("unsettled", unknowns), ("has a value", valued)):
        for claim in group:
            key = (
                side,
                claim.lane,
                "null" if claim.value is None else str(claim.value),
            )
            buckets.setdefault(key, []).append(claim)
    rows: List[Dict[str, Any]] = []
    for (side, lane, value), members in sorted(buckets.items()):
        paths = sorted({c.path for c in members})
        rows.append(
            {
                "side": side,
                "lane": lane,
                "value": value,
                "file_count": len(paths),
                "example_path": paths[0],
                "example_locator": members[0].locator,
            }
        )
    return rows


def analyze(
    claims: Sequence[Claim], crosswalk: Optional[Crosswalk] = None
) -> Dict[str, Any]:
    """Group claims by (identifier, aligned field) and classify disagreements."""
    crosswalk = crosswalk or Crosswalk()

    lanes_by_identifier: Dict[str, Set[str]] = {}
    lanes_by_field: Dict[str, Set[str]] = {}
    groups: Dict[Tuple[str, str], List[Claim]] = {}

    for claim in claims:
        lanes_by_identifier.setdefault(claim.identifier, set()).add(claim.lane)
        field = crosswalk.canonical(claim.lane, claim.field)
        lanes_by_field.setdefault(field, set()).add(claim.lane)
        groups.setdefault((claim.identifier, field), []).append(claim)

    shared_identifiers = {
        k: sorted(v) for k, v in lanes_by_identifier.items() if len(v) > 1
    }
    shared_fields = {k: sorted(v) for k, v in lanes_by_field.items() if len(v) > 1}

    findings: List[Dict[str, Any]] = []
    comparable = 0

    for (identifier, field), members in sorted(groups.items()):
        lanes = {c.lane for c in members}
        if len(lanes) < 2:
            # Only one lane says anything about this field. There is nothing to
            # agree or disagree with, so it is not a finding either way.
            continue
        comparable += 1
        unknowns = [c for c in members if c.kind in UNSETTLED]
        zeros = [c for c in members if c.kind == ZERO]
        knowns = [c for c in members if c.kind == KNOWN]
        if not unknowns:
            continue
        families = sorted({c.kind for c in unknowns})
        if zeros:
            verdict = UNKNOWN_BECAME_ZERO
            detail = (
                "one lane records an unsettled value while another records a "
                "literal zero for the same identifier and field. A zero is the "
                "one substitution that survives every downstream sum without "
                "looking wrong."
            )
        elif knowns:
            verdict = UNKNOWN_HARDENED
            detail = (
                "one lane records an unsettled value while another records a "
                "settled one. This may be a legitimate later estimate or it may "
                "be a value that was never sourced; nothing in the bytes "
                "distinguishes them."
            )
        else:
            verdict = CONSISTENT
            detail = (
                "every lane that speaks to this field records an unsettled "
                "value, in the "
                + ("same" if len(families) == 1 else "following")
                + " family: "
                + ", ".join(families)
                + "."
            )
        valued = zeros + knowns
        unknown_lanes = {c.lane for c in unknowns}
        valued_lanes = {c.lane for c in valued}
        # If every lane holding a value also records the unknown for this same
        # pair, no unknown crossed a boundary and changed -- one lane's own
        # variants differ from each other, which is what a negative test fixture
        # is for.
        scope = (
            INTRA_LANE_VARIANT
            if valued and valued_lanes.issubset(unknown_lanes)
            else CROSS_LANE
        )
        hint_paths = sorted(
            {
                c.path
                for c in valued
                if any(h in c.path.lower() for h in NEGATIVE_FIXTURE_HINTS)
            }
        )
        findings.append(
            {
                "verdict": verdict,
                "scope": scope,
                "identifier": identifier,
                "aligned_field": field,
                "lanes": sorted(lanes),
                "unknown_lanes": sorted(unknown_lanes),
                "valued_lanes": sorted(valued_lanes),
                "detail": detail,
                "scope_detail": (
                    "No valued side: no lane records a settled value for this "
                    "pair, so nothing crossed a boundary and changed."
                    if not valued
                    else "Cross-lane: a lane records a value for this pair "
                    "without recording the unknown anywhere in its own files. "
                    "Something changed across a handoff."
                    if scope == CROSS_LANE
                    else "Intra-lane variant: every lane holding a value also "
                    "records the unknown for this same pair elsewhere in its own "
                    "files. That is one lane's copies differing from each other, "
                    "which is what a checker's deliberately-broken fixtures look "
                    "like from outside. Not evidence that an unknown failed to "
                    "survive a handoff."
                ),
                "negative_fixture_path_hint": hint_paths,
                "unsettled_families": families,
                "unknown_side": [c.to_dict() for c in unknowns],
                "valued_side": [c.to_dict() for c in valued],
                "evidence_summary": _summarize_sides(unknowns, valued),
                "resolution": (
                    "Nothing to resolve: no lane claims a settled value here. "
                    "Listed so the comparison that was actually performed is "
                    "visible, rather than only its failures."
                    if verdict == CONSISTENT
                    else "This screen does not decide which lane is correct. A "
                    "person with the engagement context has to say whether the "
                    "value was settled after the unsettled one was recorded, or "
                    "whether it is still unsettled."
                    if scope == CROSS_LANE
                    else "No action implied. Reported for completeness so the "
                    "screen is not silently filtering its own results."
                ),
            }
        )

    cross_lane = [f for f in findings if f["scope"] == CROSS_LANE]
    by_verdict = {
        v: [f for f in cross_lane if f["verdict"] == v] for v in FINDING_ORDER
    }

    # The alignment gap is a first-class result. A screen that could compare
    # almost nothing and reported "no conflicts" would be worse than useless.
    single_lane_fields = {
        k: sorted(v) for k, v in lanes_by_field.items() if len(v) == 1
    }

    return {
        "content_class": "READ_ONLY_SCREEN_RESULT_NOT_AN_ASSESSMENT",
        "totals": {
            "claims": len(claims),
            "identifiers": len(lanes_by_identifier),
            "identifiers_in_multiple_lanes": len(shared_identifiers),
            "field_names": len(lanes_by_field),
            "field_names_in_multiple_lanes": len(shared_fields),
            "field_names_in_one_lane_only": len(single_lane_fields),
            "comparable_identifier_field_pairs": comparable,
        },
        "coverage": {
            "shared_identifiers": shared_identifiers,
            "shared_fields": shared_fields,
            "single_lane_fields_sample": sorted(single_lane_fields)[:40],
            "alignment_note": (
                f"{len(shared_fields)} of {len(lanes_by_field)} field names appear "
                f"in more than one lane. The remaining "
                f"{len(single_lane_fields)} are used by exactly one lane, so no "
                f"cross-lane check of those values is possible at all -- not "
                f"because they agree, but because nothing can be compared to "
                f"them."
            ),
        },
        "findings": [
            f for verdict in FINDING_ORDER for f in by_verdict[verdict]
        ],
        "intra_lane_variants": [
            f for f in findings if f["scope"] == INTRA_LANE_VARIANT
        ],
        "counts_by_verdict": {v: len(by_verdict[v]) for v in FINDING_ORDER},
        "counts_by_scope": {
            CROSS_LANE: len(cross_lane),
            INTRA_LANE_VARIANT: len(findings) - len(cross_lane),
        },
        "crosswalk_declarations": crosswalk.declarations,
        "limits": [
            "A clean result means this screen found no disagreement in the fields "
            "it could align. It is NOT a statement that the artifacts agree.",
            "Fields are aligned by exact name or by a declared crosswalk entry. "
            "No similarity matching is performed, so genuinely equivalent fields "
            "with different names are invisible to this screen unless somebody "
            "declares the equivalence.",
            "Only JSON and CSV are read. Values stated in Markdown prose are not "
            "compared.",
            "The screen cannot tell a legitimate later estimate from a value that "
            "was never sourced, and does not try.",
            "No lane, artifact or author is scored, rated, graded or marked "
            "compliant by this output.",
        ],
    }


def vocabulary_divergence(claims: Sequence[Claim]) -> List[Dict[str, Any]]:
    """Fields where lanes disagree about how to spell 'no value'.

    This is the mechanism behind most of the findings above: two lanes both
    handle the absence correctly, in words the other would not recognize, so no
    automated consumer can see that they agree.
    """
    spellings: Dict[str, Dict[str, Set[str]]] = {}
    for claim in claims:
        if claim.kind not in UNSETTLED:
            continue
        token = "null" if claim.value is None else str(claim.value).strip()
        spellings.setdefault(claim.field, {}).setdefault(token, set()).add(claim.lane)
    out: List[Dict[str, Any]] = []
    for field, tokens in sorted(spellings.items()):
        if len(tokens) < 2:
            continue
        out.append(
            {
                "field": field,
                "spellings": {
                    token: sorted(lanes) for token, lanes in sorted(tokens.items())
                },
                "detail": (
                    f"field '{field}' expresses an unsettled value in "
                    f"{len(tokens)} different ways across the tree"
                ),
            }
        )
    return out


def unknown_vocabulary_census(claims: Sequence[Claim]) -> Dict[str, Any]:
    """Every distinct spelling of an unsettled value, and which lanes use it.

    The `family` column keeps the distinction the screen refuses to blur: a token
    meaning "nobody supplied this" is not the same as one meaning "somebody
    looked and it is incomplete".
    """
    census: Dict[str, Tuple[str, Set[str]]] = {}
    for claim in claims:
        if claim.kind not in UNSETTLED:
            continue
        token = "null" if claim.value is None else str(claim.value).strip()
        family, lanes = census.setdefault(token, (claim.kind, set()))
        lanes.add(claim.lane)
    return {
        token: {
            "family": family,
            "lanes": sorted(lanes),
            "lane_count": len(lanes),
        }
        for token, (family, lanes) in sorted(census.items())
    }


# --------------------------------------------------------------------------------
# Read-only verification
# --------------------------------------------------------------------------------


def tree_digest(root: str, lane_prefix: str = "uiowa_rfq_18649_") -> str:
    """A digest over every scanned file's bytes, for before/after comparison."""
    hasher = hashlib.sha256()
    for lane, path in iter_files(root, lane_prefix):
        hasher.update(os.path.relpath(path, root).encode("utf-8"))
        try:
            with open(path, "rb") as handle:
                hasher.update(hashlib.sha256(handle.read()).digest())
        except OSError:
            hasher.update(b"<unreadable>")
    return "sha256:" + hasher.hexdigest()


def verify_readonly(root: str, lane_prefix: str = "uiowa_rfq_18649_"):
    """Run a scan between two digests and prove nothing in the tree moved."""
    before = tree_digest(root, lane_prefix)
    claims, unreadable = collect_claims(root, lane_prefix)
    after = tree_digest(root, lane_prefix)
    return {
        "digest_before": before,
        "digest_after": after,
        "tree_unchanged": before == after,
    }, claims, unreadable


# --------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------


def render_markdown(
    result: Dict[str, Any],
    divergence: Sequence[Dict[str, Any]],
    census: Dict[str, Any],
    readonly: Dict[str, Any],
    root_label: str,
) -> str:
    totals = result["totals"]
    out: List[str] = []
    out.append("# Does UNKNOWN survive the delivery chain?")
    out.append("")
    out.append(
        "A read-only screen over the landed RFQ-18649 lanes. It asks one "
        "question: when a lane records that nobody estimated something, does that "
        "stay recorded everywhere the same identifier appears?"
    )
    out.append("")
    out.append(f"Scanned: `{root_label}`")
    out.append("")
    out.append(
        f"- Tree digest before: `{readonly['digest_before']}`\n"
        f"- Tree digest after:  `{readonly['digest_after']}`\n"
        f"- **Tree unchanged by this scan: {readonly['tree_unchanged']}**"
    )
    out.append("")

    out.append("## What was found")
    out.append("")
    out.append("| | |")
    out.append("|---|---:|")
    out.append(f"| Claims extracted | {totals['claims']:,} |")
    out.append(f"| Distinct identifiers | {totals['identifiers']:,} |")
    out.append(
        f"| Identifiers appearing in more than one lane | "
        f"**{totals['identifiers_in_multiple_lanes']}** |"
    )
    out.append(f"| Distinct field names | {totals['field_names']:,} |")
    out.append(
        f"| Field names appearing in more than one lane | "
        f"**{totals['field_names_in_multiple_lanes']}** |"
    )
    out.append(
        f"| Identifier+field pairs actually comparable | "
        f"{totals['comparable_identifier_field_pairs']} |"
    )
    out.append("")
    counts = result["counts_by_verdict"]
    out.append(
        f"- `UNKNOWN_BECAME_ZERO`: **{counts[UNKNOWN_BECAME_ZERO]}**\n"
        f"- `UNKNOWN_HARDENED`: **{counts[UNKNOWN_HARDENED]}**\n"
        f"- `CONSISTENT` (all lanes agree it is unknown): {counts[CONSISTENT]}"
    )
    out.append("")

    out.append("## The alignment gap")
    out.append("")
    out.append(result["coverage"]["alignment_note"])
    out.append("")
    out.append(
        "**This is the headline result, not a caveat.** Lanes share identifiers "
        "but not a field vocabulary, so most values in the delivery kit cannot be "
        "cross-checked by any automated consumer. Where nothing can be compared, "
        "silence is not agreement."
    )
    out.append("")
    if result["coverage"]["shared_fields"]:
        out.append("Field names that do appear in more than one lane:")
        out.append("")
        out.append("| field | lanes |")
        out.append("|---|---|")
        for field, lanes in sorted(result["coverage"]["shared_fields"].items()):
            out.append(f"| `{field}` | {', '.join(lanes)} |")
        out.append("")

    out.append("## How the tree spells \"nobody estimated this\"")
    out.append("")
    if not census:
        out.append("_No unknown markers found._")
    else:
        out.append("| spelling | family | lanes using it |")
        out.append("|---|---|---:|")
        for token, info in census.items():
            out.append(
                f"| `{token}` | {info['family']} | {info['lane_count']} |"
            )
        out.append("")
        out.append(
            f"{len(census)} distinct spellings. Every one is a reasonable choice "
            "in its own lane. Together they are the reason a downstream consumer "
            "cannot tell that two lanes are saying the same thing.\n\n"
            "`UNKNOWN` family = nobody supplied a value. `INCOMPLETE` family = "
            "somebody looked and the answer is not settled. This screen keeps "
            "them apart, because merging them would be the same conflation it "
            "exists to detect."
        )
    out.append("")

    if divergence:
        out.append("### Fields that spell it more than one way")
        out.append("")
        for entry in divergence:
            out.append(f"- **`{entry['field']}`** — " + "; ".join(
                f"`{token}` ({', '.join(lanes)})"
                for token, lanes in entry["spellings"].items()
            ))
        out.append("")

    out.append("## Findings")
    out.append("")
    if not result["findings"]:
        out.append(
            "**No cross-lane disagreement was found in the fields this screen "
            "could align.** Read that precisely: it is a statement about "
            f"{totals['comparable_identifier_field_pairs']} comparable "
            "identifier+field pairs, not about the delivery kit. The alignment "
            "gap above is what limits it."
        )
    else:
        for finding in result["findings"]:
            out.append(
                f"### `{finding['verdict']}` — {finding['identifier']} · "
                f"`{finding['aligned_field']}`"
            )
            out.append("")
            out.append(finding["detail"])
            out.append("")
            out.append("| side | lane | value | files | example |")
            out.append("|---|---|---|---:|---|")
            for row in finding["evidence_summary"]:
                side = (
                    f"**{row['side']}**"
                    if row["side"] == "has a value"
                    else row["side"]
                )
                out.append(
                    f"| {side} | {row['lane']} | `{row['value']}` | "
                    f"{row['file_count']} | `{row['example_path']}` "
                    f"({row['example_locator']}) |"
                )
            out.append("")
            out.append(f"*Resolution:* {finding['resolution']}")
            out.append("")

    intra = result.get("intra_lane_variants", [])
    out.append("## Set aside: one lane's own variants")
    out.append("")
    if not intra:
        out.append("_None._")
    else:
        out.append(
            f"{len(intra)} pair(s) where a lane records a value for an identifier "
            f"and field that the **same lane** records as unknown elsewhere in its "
            f"own files. That is a lane's copies differing from each other, which "
            f"is exactly what a checker's deliberately-broken fixtures look like "
            f"from outside. These are **not** counted as propagation failures — "
            f"treating another seat's passing negative tests as defects in the "
            f"delivery kit would be manufacturing findings. They are listed so the "
            f"screen is not silently filtering its own results."
        )
        out.append("")
        out.append("| identifier | field | lane(s) | negative-fixture paths |")
        out.append("|---|---|---|---:|")
        for finding in intra:
            out.append(
                f"| {finding['identifier']} | `{finding['aligned_field']}` | "
                f"{', '.join(finding['valued_lanes'])} | "
                f"{len(finding['negative_fixture_path_hint'])} |"
            )
        out.append("")
        out.append(
            "The rule that sets these aside is **structural** — the same lane "
            "holds both sides — not a directory-name guess. The path column is "
            "reported only as corroborating context; a convention like "
            "`fixtures/mismatched/` is a habit, not a guarantee."
        )
    out.append("")

    if result["crosswalk_declarations"]:
        out.append("## Declared field equivalences")
        out.append("")
        out.append(
            "Alignments below were **asserted by a person**, not inferred. "
            "Nothing else was aligned by anything but an exact name match."
        )
        out.append("")
        for entry in result["crosswalk_declarations"]:
            members = ", ".join(
                f"`{m['lane']}.{m['field']}`" for m in entry["members"]
            )
            out.append(
                f"- **{entry['canonical_field']}** — {members}\n"
                f"  - asserted by: {entry['asserted_by']}\n"
                f"  - basis: {entry['basis']}"
            )
        out.append("")

    out.append("## What this screen cannot tell you")
    out.append("")
    for limit in result["limits"]:
        out.append(f"- {limit}")
    out.append("")
    out.append("---")
    out.append("")
    out.append(
        "Produced offline by `scan_unknowns.py` (Python standard library only), "
        "read-only. This output is a screen result, not an assessment, not a "
        "finding about the University of Iowa, and not a judgement of any lane or "
        "any author."
    )
    out.append("")
    return "\n".join(out)


CSV_COLUMNS = [
    "verdict",
    "identifier",
    "aligned_field",
    "unknown_lane",
    "unknown_value",
    "unknown_path",
    "valued_lane",
    "valued_value",
    "valued_path",
    "resolution",
]


def to_csv_rows(result: Dict[str, Any]) -> List[List[str]]:
    rows: List[List[str]] = [list(CSV_COLUMNS)]
    for finding in result["findings"]:
        for unknown in finding["unknown_side"]:
            for valued in finding["valued_side"] or [{}]:
                rows.append(
                    [
                        finding["verdict"],
                        finding["identifier"],
                        finding["aligned_field"],
                        unknown["lane"],
                        # Written as a word. A blank cell here would be the very
                        # substitution this screen exists to detect.
                        "null" if unknown["value"] is None else str(unknown["value"]),
                        unknown["path"],
                        valued.get("lane", ""),
                        "" if not valued else str(valued.get("value", "")),
                        valued.get("path", ""),
                        finding["resolution"],
                    ]
                )
    return rows


def write_csv(result: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(to_csv_rows(result))


# --------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        prog="scan_unknowns.py",
        description=(
            "Read-only screen: does a value recorded as UNKNOWN in one delivery "
            "lane stay UNKNOWN wherever the same identifier appears?"
        ),
    )
    parser.add_argument(
        "--root",
        default=os.path.abspath(os.path.join(here, "..")),
        help="directory holding the lanes (default: the parent revenue/ dir)",
    )
    parser.add_argument("--lane-prefix", default="uiowa_rfq_18649_")
    parser.add_argument(
        "--crosswalk",
        default=os.path.join(here, "crosswalk.json"),
        help="declared field equivalences; pass an empty path to align by name only",
    )
    parser.add_argument("--json-out")
    parser.add_argument("--csv-out")
    parser.add_argument("--markdown-out")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        crosswalk_payload = None
        if args.crosswalk and os.path.exists(args.crosswalk):
            with open(args.crosswalk, "r", encoding="utf-8") as handle:
                crosswalk_payload = json.load(handle)
        crosswalk = Crosswalk(crosswalk_payload)
        readonly, claims, unreadable = verify_readonly(args.root, args.lane_prefix)
        result = analyze(claims, crosswalk)
        result["unreadable_files"] = unreadable
        result["readonly_verification"] = readonly
        divergence = vocabulary_divergence(claims)
        result["vocabulary_divergence"] = divergence
        census = unknown_vocabulary_census(claims)
        result["unknown_vocabulary_census"] = census
    except (ScanError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(
        result, divergence, census, readonly, os.path.abspath(args.root)
    )
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    if args.csv_out:
        write_csv(result, args.csv_out)
    if args.markdown_out:
        with open(args.markdown_out, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    if not (args.json_out or args.csv_out or args.markdown_out):
        print(markdown)

    totals = result["totals"]
    counts = result["counts_by_verdict"]
    print(
        f"[unknowns] {totals['claims']} claims, "
        f"{totals['identifiers_in_multiple_lanes']} identifiers in >1 lane, "
        f"{totals['field_names_in_multiple_lanes']}/{totals['field_names']} field "
        f"names in >1 lane; {counts[UNKNOWN_BECAME_ZERO]} became-zero, "
        f"{counts[UNKNOWN_HARDENED]} hardened, {counts[CONSISTENT]} consistent. "
        f"Tree unchanged: {readonly['tree_unchanged']}.",
        file=sys.stderr,
    )
    if not readonly["tree_unchanged"]:
        print("[unknowns] READ-ONLY VIOLATION", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
