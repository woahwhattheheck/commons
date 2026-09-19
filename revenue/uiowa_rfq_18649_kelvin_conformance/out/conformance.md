# Conformance: seat lanes projected into the UIOWA-023 register

The claim that lanes 071, 107 and 108 join to the evidence register was
made by matching field names and id shapes. This settles it by running
the register's own validator over the projected rows.

All source records are fictional rehearsal records. The projection
carries that forward and does not launder them into evidence.

## Result: `CONFORMANT`

| | |
| --- | ---: |
| Rows projected | 23 |
| Rows skipped | 0 |
| Sibling lanes absent | 0 |
| Declared divergences | 2 |
| Undeclared divergences | 0 |

### Validator output, verbatim

```
$ python3 uiowa_rfq_18649_workshare/methodology/validate_23_evidence_register.py out/projected_register.csv
exit=0
OK rows=23 observations=23 findings=23
```

### Rows by register state

| Order | evidence_state | confidence | Rows |
| --- | --- | --- | ---: |
| UIOWA-071 | CONFLICTING | UNRESOLVED | 1 |
| UIOWA-071 | NO_EVIDENCE_OBSERVED | NOT_EVIDENCED | 3 |
| UIOWA-071 | SUPPORTING | LOW | 4 |
| UIOWA-071 | SUPPORTING | MODERATE | 2 |
| UIOWA-107 | NO_EVIDENCE_OBSERVED | NOT_EVIDENCED | 2 |
| UIOWA-107 | SUPPORTING | LOW | 3 |
| UIOWA-107 | SUPPORTING | MODERATE | 2 |
| UIOWA-108 | EVIDENCE_OF_ABSENCE | LOW | 2 |
| UIOWA-108 | NO_EVIDENCE_OBSERVED | NOT_EVIDENCED | 2 |
| UIOWA-108 | SUPPORTING | MODERATE | 2 |

## Declared divergences

**DIV-071-01** (UIOWA-071) — `PLANNED_USE`, `UNSUPPORTED_CLAIM`, `UNKNOWN` → `NO_EVIDENCE_OBSERVED / NOT_EVIDENCED`

- The register's evidence_state enum has one value for 'nothing observed'. The inventory distinguishes a use that has not started, a use asserted with nothing behind it, and a record too incomplete to classify. Those are three different next actions.
- Preserved as: the source classification is written verbatim into scope_limit, so the distinction survives at row level even though the enum cannot hold it
- Direction: neutral: none of the three is made to look better or worse than the source says

**DIV-107-01** (UIOWA-107) — `ASSUMED`, `UNKNOWN` → `NO_EVIDENCE_OBSERVED / NOT_EVIDENCED`

- A working figure with nothing behind it and no figure at all are different states. The register cannot separate them.
- Preserved as: the source basis is written verbatim into scope_limit
- Direction: neutral: ASSUMED is not promoted to SUPPORTING on the strength of having a number

## Distinctions that survived the projection

- **SURV-108-01** (UIOWA-108) — The register carries EVIDENCE_OF_ABSENCE separately from NO_EVIDENCE_OBSERVED, which is exactly the unresolved-ownership versus missing-evidence distinction 108 makes. Nothing is lost, and the register's own rule then requires universe_definition, enumerator_authority and completeness_basis, which the packet can supply.
- **SURV-071-02** (UIOWA-071) — A record declared PLANNED that arrives carrying output projects to CONFLICTING, and the register then forces UNRESOLVED confidence plus a conflict_group. The status/evidence mismatch survives intact.

## Limits

- A passing validator run proves the rows are structurally admissible
  to the register. It does not prove the mapping is the one the
  assessment team would choose.
- Only the register is exercised here. The UIOWA-091 collection
  validator is not run, so compatibility with that collection remains
  asserted rather than demonstrated.
