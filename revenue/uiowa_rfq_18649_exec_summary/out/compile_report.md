# Compile report

Source register: Cedar Hollow Regional Authority (FICTIONAL) - assessment findings register, draft

| Metric | Value |
|---|---|
| statements submitted | 12 |
| statements accepted | 4 |
| statements rejected | 8 |
| findings total | 6 |
| findings cited | 4 |
| findings uncited | 2 |

## Findings rejected at load

Malformed records are named and excluded. They are NOT repaired with defaults, because a repaired finding becomes citable by a leadership statement.

- `F-007-MALFORMED` - finding 'F-007-MALFORMED': severity 'URGENT' not in ['INFORMATIONAL', 'MINOR', 'SIGNIFICANT', 'CRITICAL']

## Statements rejected

Each rejection names the check, the reason, and the remedy. The author fixes the sentence; the compiler does not soften it for them.

### `S-002`

> Data ownership is documented for the systems that feed the reporting pipeline.

Cites: `F-002`

- **OVERCLAIM** - phrasing asserts SETTLED, but the weakest citation (F-002) supports only SINGLE_SOURCE: Must be attributed to its source: 'one team reported'. Never generalized.
  - *Remedy:* rephrase with attribution, e.g. 'one unit reported ...', and do not generalize beyond that source

### `S-003`

> Evidence indicates that all units triage requests within the same working day.

Cites: `F-004`

- **SCOPE_OVERREACH** - phrasing generalizes to all units (all units) but the citation(s) cover only part of scope: F-004 (2 of 5 units)
  - *Remedy:* state the actual scope, e.g. 'in the N of M units reviewed', or cite a finding established across full scope

### `S-004`

> Governance of AI-assisted output is handled through an established review path.

Cites: `F-999`

- **UNKNOWN_FINDING** - cites finding ID(s) not present in the findings store: F-999
  - *Remedy:* correct the finding ID, or record the finding before citing it

### `S-005`

> Overall the organization is well positioned to expand its use of AI.

Cites: *nothing*

- **NO_CITATION** - the statement cites no finding
  - *Remedy:* bind the statement to the finding ID that establishes it, or delete the statement

### `S-006`

> A review path exists for AI-assisted outputs before they take effect.

Cites: `F-003`

- **ASSERTS_NOT_ESTABLISHED** - cited finding(s) F-003 are not established (basis or confidence is UNKNOWN / no evidence attached), so nothing may be asserted from them
  - *Remedy:* remove the assertion; move the subject to the open-questions section as an UNKNOWN

### `S-007`

> Reference data is refreshed on a documented schedule, covering 42% of catalogued datasets.

Cites: `F-006`

- **UNSUPPORTED_NUMBER** - figure(s) 42 appear in the statement but in none of its citations
  - *Remedy:* use the figure exactly as the finding records it, or remove it

### `S-010`

> Delays in incident closure trace to individual performance in the intake role.

Cites: `F-001`

- **INDIVIDUAL_ATTRIBUTION** - language evaluates a person rather than a workflow or system: individual performance
  - *Remedy:* restate as an observation about the process, the system or the unit; individual performance is out of scope for this engagement

### `S-011`

> Incident records are retained with a named owner and data ownership is documented for the reporting pipeline.

Cites: `F-001`, `F-002`

- **OVERCLAIM** - phrasing asserts SETTLED, but the weakest citation (F-002) supports only SINGLE_SOURCE: Must be attributed to its source: 'one team reported'. Never generalized.
  - *Remedy:* rephrase with attribution, e.g. 'one unit reported ...', and do not generalize beyond that source

## Coverage: findings not represented in the summary

**Assertable but uncited.** These findings COULD have been stated and were not. Each one is either a deliberate editorial choice or a finding that fell out of the summary unnoticed.

| Finding | Severity | Strength | Scope | Title |
|---|---|---|---|---|
| `F-005` | **CRITICAL** | SETTLED | 4 of 5 units | Corrective actions recorded but not tracked to completion |

**Not assertable, correctly absent.** These are uncited because nothing may be asserted from them. They belong in the open-questions section of the summary, and they are there.

- `F-003` (CRITICAL) - Review path for AI-assisted outputs. May NOT be asserted at all. May only be named as an open question in the unresolved section.
