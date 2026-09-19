# Cross-lane UNKNOWN-propagation screen

Does a value recorded as UNKNOWN in one delivery lane stay UNKNOWN wherever the same
identifier appears in another?

Read-only, offline, Python 3 standard library only.

---

## Status

| Thing | Status |
|---|---|
| `scan_unknowns.py` | **Working code.** 46 tests, all passing. |
| `test_scan_unknowns.py` | **Working tests**, including planted positive conflicts. |
| `fixtures/lane_alpha`, `fixtures/lane_beta` | **SYNTHETIC.** Two invented lanes with deliberate conflicts, so the detector is proven on positives. |
| `crosswalk.json` | **Declared** field equivalences, each with who asserted it and why. |
| `examples/` | Output from a real run over the landed `revenue/uiowa_rfq_18649_*` tree. |

Not an assessment. Not a University of Iowa finding. No lane, artifact or author is scored,
rated, graded or marked compliant by any output here.

---

## Run

```bash
# Screen the landed tree
python3 scan_unknowns.py --root ..

# Prove the detector on the planted conflicts
python3 scan_unknowns.py --root fixtures --lane-prefix lane_ --crosswalk ""

python3 -m unittest -v test_scan_unknowns.py
python3 -O -m unittest test_scan_unknowns.py
```

---

## What it does

Walks every `.json` and `.csv` under the lane tree and extracts
`(identifier, field, value)` claims: any JSON object carrying an `*_id` key whose value
matches a known prefix (`REC-SYN-`, `FND-SYN-`, `EV-SYN-`, `OBS-SYN-`, `CR-SYN-`, `WI-`,
`OPP-`, `ECON-`), and any CSV row with an id column. Each value is classified, then claims
are grouped by identifier and aligned field.

### Value classes

| class | meaning |
|---|---|
| `UNKNOWN` | Nobody supplied a value — `null`, `"UNKNOWN"`, `NOT_RANKED`, `NEEDS_ESTIMATE`, `NO_RESOURCING_DATA`, `NOT QUOTED`, `TBD`, … |
| `INCOMPLETE` | Somebody looked and the answer is not settled — `PARTIAL`, `UNRESOLVED`, `HOLD`, … |
| `ZERO` | A literal `0`, `0.0`, `"0"`, `"$0.00"` |
| `KNOWN` | A settled value |
| `EMPTY` | An empty string — ambiguous, and **not** treated as a recorded unknown |

`UNKNOWN` and `INCOMPLETE` are kept apart deliberately. `PARTIAL` does not mean nobody
looked. Merging them would be the same conflation this screen exists to detect, committed
by the screen itself. Both count as *unsettled* for the hardening check, and every output
states which family a claim came from.

### Verdicts

| verdict | meaning |
|---|---|
| `UNKNOWN_BECAME_ZERO` | One lane unsettled, another a literal zero. Highest severity: a zero is the one substitution that survives every downstream sum without looking wrong. |
| `UNKNOWN_HARDENED` | One lane unsettled, another settled. May be a legitimate later estimate or a value that was never sourced. |
| `CONSISTENT` | Every lane that speaks to the field records an unsettled value. Reported, so the comparison that succeeded is visible and not only its failures. |

### Scope

A finding is `CROSS_LANE` only when the lane holding the value never records the unknown
for that same identifier and field anywhere in its own files.

When the same lane holds both sides, the finding is `INTRA_LANE_VARIANT` and is **set
aside**. That shape is what a checker's deliberately-broken fixtures look like from
outside — a negative-test copy differs from the clean copy on purpose. Counting those would
manufacture defects out of another seat's passing test suite. They are listed rather than
dropped, so the screen is not silently filtering its own results.

The rule is **structural**, not path-based. A directory called `fixtures/mismatched/` is a
convention, not a guarantee, so it cannot suppress a real cross-lane finding; the path is
reported only as corroborating context. A test asserts a value under a `mismatched/` path
in a *different* lane still raises `UNKNOWN_HARDENED`.

---

## What it refuses to do

**It never says which lane is right.** Nothing in the bytes distinguishes a legitimate later
estimate from a value that was never sourced. Every conflict is reported with both sides,
their exact file paths and locators, and the resolution *"a person with the engagement
context has to say."* A test asserts no finding contains the words `authoritative`,
`correct_lane`, `should be` or `is wrong`.

**It never infers a field correspondence.** Fields align by exact name, or by an entry in
`crosswalk.json` recording who asserted the equivalence and on what basis. An equivalence
with no basis is **refused** — an unexplained mapping is indistinguishable from a guess. A
test asserts `effort_hours` and `effort_hrs` are *not* aligned automatically.

**It never reports a clean result as correctness.** "No conflicts" means no disagreement was
found *in the fields it could align*. The report always states how many fields it could not
align, and calls that the headline result rather than a caveat.

**It never scores, rates or grades.** A test walks the output for `score`, `grade`,
`compliant`, `pass_rate`, `quality_rating` and fails if any appear outside the disclaimer.

**It never writes into the tree it reads.** `verify_readonly` hashes every scanned file
before and after and asserts byte-identical. A separate test proves the digest actually
detects a one-character edit, because a read-only proof whose digest cannot notice a change
proves nothing.

**It reports what it could not read.** A file that fails to parse is listed with its reason,
never skipped silently — a screen that quietly ignores unreadable files is reporting on a
smaller tree than it claims to.

---

## Result over the landed tree

From `examples/landed-tree-scan.md`, one run over `revenue/`. A snapshot: the tree keeps
growing, so the run is pinned by its digest `sha256:1fa495b0c532d3dc348…`.

```
claims extracted                            6,221
identifiers                                   136
identifiers appearing in >1 lane               29
field names                                   222
field names appearing in >1 lane               36
field names used by exactly one lane          186
comparable identifier+field pairs             120
unreadable files                                0

UNKNOWN_BECAME_ZERO   0   (cross-lane)
UNKNOWN_HARDENED      0   (cross-lane)
CONSISTENT            4
set aside             3   (intra-lane variants)
tree unchanged     True
```

**The alignment gap is the finding.** 36 of 222 field names appear in more than one lane;
186 are used by exactly one lane, so no cross-lane check of those values is possible at
all — not because they agree, but because nothing can be compared to them. Only 120
identifier+field pairs could be compared at all.

**Twelve distinct spellings of "unsettled"** are in use: `UNKNOWN`, `NOT_RANKED`,
`NEEDS_ESTIMATE`, `NO_RESOURCING_DATA`, `NOT QUOTED`, `POPULATION_UNKNOWN`, `NONE`, `None`,
`none`, `null`, plus `PARTIAL` and `UNRESOLVED` in the `INCOMPLETE` family. Each is
reasonable in its own lane. Together they are why no automated consumer can tell that two
lanes are saying the same thing. **Twelve fields spell it more than one way**, including
`rank` (`NOT_RANKED` / `UNKNOWN` / `null`, two lanes) and `status`
(`NEEDS_ESTIMATE` / `PARTIAL` / `UNKNOWN`, three lanes).

Zero cross-lane hardening was found. That is a statement about 120 comparable pairs, not
about the delivery kit.

The three set-aside items are all in one lane's `fixtures/mismatched/` tree — deliberately
broken copies belonging to that lane's own checker, correctly not counted as defects.

### One defect this screen found in its author's own earlier work

The census surfaced the spelling `None` — the Python `str(None)` result, not JSON `null` —
in `uiowa_rfq_18649_prioritization`. Tracing it: a recommendation with `"notes": null`
shipped with `"notes": "None"`, because the loader used
`str(payload.get("notes", "")).strip()`. Four characters that look like content in every
downstream CSV, report and comparison.

Fixed in the same change that adds this lane: `prioritize.py` gains a `_text()` helper that
maps `None` to `""`, applied to `title`, `group`, `area` and `notes`, with two regression
tests and regenerated examples.

---

## Limits

- Only JSON and CSV are read. Values stated in Markdown prose are not compared.
- Identifier detection is prefix-based. A lane using an unlisted ID shape is invisible.
- A field used by one lane only is uncheckable, and that is most of them.
- The screen cannot tell a legitimate later estimate from an unsourced value, and does not
  try.
- A clean result is a statement about the comparisons performed, not about the delivery kit.

## UNKNOWN University inputs

Everything about the actual engagement. This screen reads synthetic preparation artifacts
only. It says nothing about the University of Iowa, its systems, or any real assessment.

---

Built by seat OP5-CINDER (Claude Opus 5).
