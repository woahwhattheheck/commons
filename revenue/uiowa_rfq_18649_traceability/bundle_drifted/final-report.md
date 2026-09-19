# Miniature assessment report (synthetic rehearsal)

{narrative} Rehearsal purpose only. All records referenced here are fabricated.
Section numbering matches the trace map; `trace-map.csv` is the authoritative
cross-reference and `trace_check.py` is what proves this document still agrees
with it.

## 1. ESS - supported practice example

{narrative} The chain is requirement to result to acceptance, and each link is a
file in `sources/` rather than a description of a file.

**S-001.** The fictional ESS example retains a complete chain from a stated
acceptance criterion through an executed integration result to a business
acceptance record, covering 1 acceptance criterion. [F:F-001]
[E:E-001,E-002,E-003] [LIMIT:F-001]

## 2. RIS - evidence gap example

**S-002.** The fictional RIS packet records an intended reporting handoff and a
contract-compatibility check, but the test inventory lists 0 end-to-end
propagation scenarios and no retained example was identified. [F:F-002]
[R:R-001] [E:E-004,E-005,E-006] [LIMIT:F-002]

### Recommendation 1

**S-004.** Retain one representative end-to-end propagation example, or
equivalent operational evidence, when this interface behaviour materially
changes. [F:F-002] [R:R-001] [E:E-004,E-005,E-006] [LIMIT:F-002]

{narrative} The objective is to reduce a specific uncertainty at modest
maintenance cost. It is not to raise a test count.

## 3. IAM - representative evidence example

**S-003.** The fictional IAM packet lists 7 dependent applications and attaches
propagation evidence for one of them. [F:F-003] [R:R-002] [E:E-007,E-008]
[LIMIT:F-003]

**S-006.** For the remaining dependent applications the propagation outcome is
UNKNOWN: the rehearsal performed no check and no prior result was supplied.
[F:F-003] [E:E-008] [LIMIT:F-003]

### Recommendation 2

**S-005.** Record which dependent applications the representative propagation
evidence covers and which remain unassessed. [F:F-003] [R:R-002] [E:E-007,E-008]
[LIMIT:F-003]

## 4. How to check this report against its records

{narrative} Run `python3 trace_check.py bundle`. The checker walks statement to
finding to citation to source record on disk, in both directions, and compares
every asserted polarity and quantity against the record it names. If a record is
edited after this report was written, the checker fails and names the field that
moved. Re-registering a changed record is a deliberate command, never automatic.
