# Provider-swap blast radius (portability)

**Method.** `edit_points = sum(count x weight)` over the code surfaces that were actually inventoried. Weight > 1 marks a surface that propagates (a vendor type or unit convention drags its call sites with it).

Bands: `CONTAINED` 0-2 edit points - `PARTIAL` 3-9 - `PERVASIVE` 10+ - `INSUFFICIENT_EVIDENCE` when any surface was not inventoried.

| System | Edit points | Total is | Band | Uncounted (UNKNOWN) |
|---|---|---|---|---|
| HRI-INTAKE-01 | 39 | complete | `PERVASIVE` | none |
| HRI-ARCHIVE-02 | 2 | complete | `CONTAINED` | none |
| HRI-AWARD-03 | 6 | a FLOOR | `INSUFFICIENT_EVIDENCE` | observability_fields_bound_to_vendor_schema, sdk_type_imports_outside_adapter, wire_shape_reads |

## Per-system detail

### HRI-INTAKE-01

Swap is a rewrite of the integration, not a substitution.

| Surface | Count | Weight | Edit points |
|---|---|---|---|
| Credential / endpoint configuration points | 2 | 1 | 2 |
| Direct invocations of the capability outside an adapter | 6 | 1 | 6 |
| Dashboards / alerts keyed to provider-specific field names | 5 | 1 | 5 |
| Prompt or parameter construction tied to one provider's dialect | 3 | 1 | 3 |
| Provider SDK types imported into workflow modules | 3 | 2 | 6 |
| Confidence-scale or category-name conversion done in workflow code | 2 | 2 | 4 |
| except clauses naming a provider-specific exception type | 4 | 1 | 4 |
| Reads of provider response fields in workflow code | 9 | 1 | 9 |

### HRI-ARCHIVE-02

Swap is an adapter-sized change.

| Surface | Count | Weight | Edit points |
|---|---|---|---|
| Credential / endpoint configuration points | 1 | 1 | 1 |
| Direct invocations of the capability outside an adapter | 1 | 1 | 1 |
| Dashboards / alerts keyed to provider-specific field names | 0 | 1 | 0 |
| Prompt or parameter construction tied to one provider's dialect | 0 | 1 | 0 |
| Provider SDK types imported into workflow modules | 0 | 2 | 0 |
| Confidence-scale or category-name conversion done in workflow code | 0 | 2 | 0 |
| except clauses naming a provider-specific exception type | 0 | 1 | 0 |
| Reads of provider response fields in workflow code | 0 | 1 | 0 |

### HRI-AWARD-03

Some code surfaces were not inventoried. The point total below is a FLOOR over the surfaces that were counted; the real figure can only be higher. No band is assigned.

| Surface | Count | Weight | Edit points |
|---|---|---|---|
| Credential / endpoint configuration points | 1 | 1 | 1 |
| Direct invocations of the capability outside an adapter | 2 | 1 | 2 |
| Prompt or parameter construction tied to one provider's dialect | 2 | 1 | 2 |
| Confidence-scale or category-name conversion done in workflow code | 0 | 2 | 0 |
| except clauses naming a provider-specific exception type | 1 | 1 | 1 |

**Not inventoried -- treated as UNKNOWN, not as zero:**
- `observability_fields_bound_to_vendor_schema` - Dashboards / alerts keyed to provider-specific field names. The swap succeeds and the monitoring silently goes blank.
- `sdk_type_imports_outside_adapter` - Provider SDK types imported into workflow modules. Types propagate through signatures; one import typically forces edits in the modules that call it.
- `wire_shape_reads` - Reads of provider response fields in workflow code. Response envelopes differ between capability providers more than request shapes do.
