# Does UNKNOWN survive the delivery chain?

A read-only screen over the landed RFQ-18649 lanes. It asks one question: when a lane records that nobody estimated something, does that stay recorded everywhere the same identifier appears?

Scanned: `/home/user/fleet/staging/OP5-CINDER/revenue/uiowa_rfq_18649_unknown_propagation/fixtures`

- Tree digest before: `sha256:8c1a2debc70e991bc745e033003b54210d7209a06491465b004e604eecece89e`
- Tree digest after:  `sha256:8c1a2debc70e991bc745e033003b54210d7209a06491465b004e604eecece89e`
- **Tree unchanged by this scan: True**

## What was found

| | |
|---|---:|
| Claims extracted | 28 |
| Distinct identifiers | 4 |
| Identifiers appearing in more than one lane | **4** |
| Distinct field names | 4 |
| Field names appearing in more than one lane | **3** |
| Identifier+field pairs actually comparable | 12 |

- `UNKNOWN_BECAME_ZERO`: **1**
- `UNKNOWN_HARDENED`: **3**
- `CONSISTENT` (all lanes agree it is unknown): 2

## The alignment gap

3 of 4 field names appear in more than one lane. The remaining 1 are used by exactly one lane, so no cross-lane check of those values is possible at all -- not because they agree, but because nothing can be compared to them.

**This is the headline result, not a caveat.** Lanes share identifiers but not a field vocabulary, so most values in the delivery kit cannot be cross-checked by any automated consumer. Where nothing can be compared, silence is not agreement.

Field names that do appear in more than one lane:

| field | lanes |
|---|---|
| `effort_hours` | lane_alpha, lane_beta |
| `owner` | lane_alpha, lane_beta |
| `priority` | lane_alpha, lane_beta |

## How the tree spells "nobody estimated this"

| spelling | family | lanes using it |
|---|---|---:|
| `NEEDS_ESTIMATE` | UNKNOWN | 1 |
| `NOT_ASSESSED` | UNKNOWN | 1 |
| `UNKNOWN` | UNKNOWN | 2 |
| `null` | UNKNOWN | 1 |

4 distinct spellings. Every one is a reasonable choice in its own lane. Together they are the reason a downstream consumer cannot tell that two lanes are saying the same thing.

`UNKNOWN` family = nobody supplied a value. `INCOMPLETE` family = somebody looked and the answer is not settled. This screen keeps them apart, because merging them would be the same conflation it exists to detect.

### Fields that spell it more than one way

- **`effort_hours`** — `UNKNOWN` (lane_alpha, lane_beta); `null` (lane_alpha)
- **`priority`** — `NEEDS_ESTIMATE` (lane_alpha); `NOT_ASSESSED` (lane_beta)

## Findings

### `UNKNOWN_BECAME_ZERO` — REC-SYN-FIX-001 · `effort_hours`

one lane records an unsettled value while another records a literal zero for the same identifier and field. A zero is the one substitution that survives every downstream sum without looking wrong.

| side | lane | value | files | example |
|---|---|---|---:|---|
| **has a value** | lane_beta | `0` | 1 | `lane_beta/rollup.csv` (row 2) |
| unsettled | lane_alpha | `null` | 1 | `lane_alpha/register.json` (.recommendations[0]) |

*Resolution:* This screen does not decide which lane is correct. A person with the engagement context has to say whether the value was settled after the unsettled one was recorded, or whether it is still unsettled.

### `UNKNOWN_HARDENED` — REC-SYN-FIX-001 · `priority`

one lane records an unsettled value while another records a settled one. This may be a legitimate later estimate or it may be a value that was never sourced; nothing in the bytes distinguishes them.

| side | lane | value | files | example |
|---|---|---|---:|---|
| **has a value** | lane_beta | `LOW` | 1 | `lane_beta/rollup.csv` (row 2) |
| unsettled | lane_alpha | `NEEDS_ESTIMATE` | 1 | `lane_alpha/register.json` (.recommendations[0]) |

*Resolution:* This screen does not decide which lane is correct. A person with the engagement context has to say whether the value was settled after the unsettled one was recorded, or whether it is still unsettled.

### `UNKNOWN_HARDENED` — REC-SYN-FIX-002 · `effort_hours`

one lane records an unsettled value while another records a settled one. This may be a legitimate later estimate or it may be a value that was never sourced; nothing in the bytes distinguishes them.

| side | lane | value | files | example |
|---|---|---|---:|---|
| **has a value** | lane_beta | `120` | 1 | `lane_beta/rollup.csv` (row 3) |
| unsettled | lane_alpha | `UNKNOWN` | 1 | `lane_alpha/register.json` (.recommendations[1]) |

*Resolution:* This screen does not decide which lane is correct. A person with the engagement context has to say whether the value was settled after the unsettled one was recorded, or whether it is still unsettled.

### `UNKNOWN_HARDENED` — REC-SYN-FIX-002 · `priority`

one lane records an unsettled value while another records a settled one. This may be a legitimate later estimate or it may be a value that was never sourced; nothing in the bytes distinguishes them.

| side | lane | value | files | example |
|---|---|---|---:|---|
| **has a value** | lane_beta | `HIGH` | 1 | `lane_beta/rollup.csv` (row 3) |
| unsettled | lane_alpha | `NEEDS_ESTIMATE` | 1 | `lane_alpha/register.json` (.recommendations[1]) |

*Resolution:* This screen does not decide which lane is correct. A person with the engagement context has to say whether the value was settled after the unsettled one was recorded, or whether it is still unsettled.

### `CONSISTENT` — REC-SYN-FIX-004 · `effort_hours`

every lane that speaks to this field records an unsettled value, in the same family: UNKNOWN.

| side | lane | value | files | example |
|---|---|---|---:|---|
| unsettled | lane_alpha | `UNKNOWN` | 1 | `lane_alpha/register.json` (.recommendations[3]) |
| unsettled | lane_beta | `UNKNOWN` | 1 | `lane_beta/rollup.csv` (row 5) |

*Resolution:* Nothing to resolve: no lane claims a settled value here. Listed so the comparison that was actually performed is visible, rather than only its failures.

### `CONSISTENT` — REC-SYN-FIX-004 · `priority`

every lane that speaks to this field records an unsettled value, in the same family: UNKNOWN.

| side | lane | value | files | example |
|---|---|---|---:|---|
| unsettled | lane_alpha | `NEEDS_ESTIMATE` | 1 | `lane_alpha/register.json` (.recommendations[3]) |
| unsettled | lane_beta | `NOT_ASSESSED` | 1 | `lane_beta/rollup.csv` (row 5) |

*Resolution:* Nothing to resolve: no lane claims a settled value here. Listed so the comparison that was actually performed is visible, rather than only its failures.

## Set aside: one lane's own variants

_None._

## What this screen cannot tell you

- A clean result means this screen found no disagreement in the fields it could align. It is NOT a statement that the artifacts agree.
- Fields are aligned by exact name or by a declared crosswalk entry. No similarity matching is performed, so genuinely equivalent fields with different names are invisible to this screen unless somebody declares the equivalence.
- Only JSON and CSV are read. Values stated in Markdown prose are not compared.
- The screen cannot tell a legitimate later estimate from a value that was never sourced, and does not try.
- No lane, artifact or author is scored, rated, graded or marked compliant by this output.

---

Produced offline by `scan_unknowns.py` (Python standard library only), read-only. This output is a screen result, not an assessment, not a finding about the University of Iowa, and not a judgement of any lane or any author.
