# UIOWA-038 — Editable recommendation and roadmap register

**SYNTHETIC EXAMPLE · DRAFT_NON_AUTHORITATIVE**

One proposed practice change can address several findings and several groups. It
still has one stable recommendation ID, one effort range, one owner-role field and
one proposed phase. This register preserves that relationship through editing and
report/roadmap exports. It does not decide which recommendation to adopt.

## Worked result

The fictional example has **5 recommendations, 6 finding records and 9 finding
links**. The known effort subtotal is **6–12 person-days**, counted once per
recommendation. REC-SYN-03 has unknown effort, owner, maturity step and phase, so
the complete effort total remains **UNKNOWN**. REC-SYN-04 separately records an
explicitly assumed zero *incremental* effort, with its basis; zero and unknown do
not collapse. No estimate is measured University effort or an agreed commitment.

REC-SYN-01 proposes a common intake record for ESS and RIS. It serves F-SYN-01 and
F-SYN-02 without creating two recommendations. REC-SYN-02 also links F-SYN-01 but
has its own distinct work and estimate. REC-SYN-05 depends on both recommendations.
Its two prerequisite IDs and 180+ phase survive every exported view and round-trip.

## Run and edit

Runtime: Python 3.10+ syntax, standard library only. Executed here on Python 3.13.5;
other interpreter versions have not been tested by this seat. From this directory:

```sh
python register.py check examples/synthetic_register.json
# Expected exit 1: draft shape is valid, but four planning fields remain unknown.

python register.py export examples/synthetic_register.json --out /tmp/uiowa038-first
# Destination must not exist. Export succeeds while preserving the unknowns.

# Edit /tmp/uiowa038-first/recommendations.csv, findings.csv and metadata.json.
python register.py import /tmp/uiowa038-first --out /tmp/uiowa038-edited.json
python register.py export /tmp/uiowa038-edited.json --out /tmp/uiowa038-second

# Exact unchanged derived views can also round-trip without losing source fields.
python register.py import-view /tmp/uiowa038-first/roadmap.json --out /tmp/uiowa038-restored.json
```

Every output bundle contains `register.json`, `metadata.json`, `findings.csv`,
`recommendations.csv`, `report.json`, `roadmap.json` and readable `report.md`.
`register.json` is the complete canonical data; the two CSV tables plus metadata
are an alternative editable representation. Derived views include the full source
register and its digest, not only the convenient display columns.

**CSV cells contain JSON values.** In a spreadsheet, a text cell must contain
`"90-180"`, an unknown value `null`, a known number `0`, and a list
`["REC-SYN-01","REC-SYN-02"]`. Text keeps its literal JSON quotes. Do not replace
`null` with an empty cell or join arrays with an unquoted delimiter. This preserves
types, commas, Unicode and embedded newlines. A string beginning `=` stays a quoted
JSON string rather than a spreadsheet formula. Header order and row width must
remain exact; an extra comma is an input error, never a shifted field.

The alternative is to edit the ordinary pretty-printed `register.json` and export
it again. That is simpler for nested scope, effort and outcome-measure objects.
A changed `report.json` or `roadmap.json` is deliberately **not** imported as an
edit: import-view checks the full projection and refuses to discard changed view
fields. Edit the canonical source or CSV tables and regenerate instead.

Exit codes: `check` returns 0 when the limited data review finds no items, 1 for
unresolved links/planning fields, and 2 for malformed input or an output error.
Successful export/import returns 0 even when printed review items remain. Neither
zero code nor a structurally valid document means evidence truth, feasibility,
readiness, approval or completed work.

## Contract and integration

`register.schema.json` describes the complete structural shape. `normalize()` adds
unique record-ID checks, finite numbers, supported Unicode/control text and ordered
effort bounds. The schema alone does not prove those cross-field/identity rules.
Missing references are retained in working drafts and named by `review_items()`;
they are never silently treated as satisfied. Unknown fields are explicit nulls,
not invented defaults. Amounts and measures are finite nonnegative numbers; signed
metrics require a future schema revision rather than an undocumented conversion.

The 13 recommendation fields are: stable ID, practice change, scoped
`group/dimension/department` cells, finding IDs, impact hypothesis, effort range
and basis, required skills, prerequisite IDs, owner role, outcome measure and
basis, proposed maturity step, proposed phase, and assumptions. A maturity step is
an explicitly proposed description, not an awarded rating or a second scale.

Group/dimension vocabulary is reused from the existing workshare:
`ESS/RIS/IAM` × `software/security/deployment/ai_readiness`. It was read at
`workshare_constants.py` blob `ec65f4f4d5387d6c2546eee98101b34faa61b0bd`.
No compiler, workbench, authority bundle, pricing or occupied UI path is changed.

The roadmap projection uses UIOWA-115's `roadmap_id`, `phases`, `item_id`, `phase`,
`recommendation_ref` and `prerequisites` shape. The observed example contract is
`../uiowa_rfq_18649_roadmap_dependencies/fixtures/roadmap_consistent.json`, blob
`60708f12e986bbc49b6f2fd5323bbb7aa8b158b8` on
`claude/multi-agent-slack-demo-4ikzfs`; original dependency-checker credit remains
OP5-JUNIPER. A multi-group action retains `owner_groups` and has scalar
`owner_group=null`, never a made-up single owner. The full source carries each
scope cell and department. Same-phase ordering, missing dependencies, cycles and
capacity remain that existing component's/planner's responsibility. No linear
execution order is invented here. The projection has been round-trip tested;
execution by the sibling dependency checker is a separate integration check, not
claimed by this receipt.

No evidence authenticity, finding validity, recommendation merit, service maturity,
University staffing, final judgment or buyer approval is established. Data marked
LOCAL_WORKING_DRAFT is not automatically anonymized. Real University, customer,
credential or personal evidence must not be committed to this public repository.

## Verification

```sh
python -m unittest -v test_register
python -O -m unittest -v test_register
# Optional structural-schema test dependency; runtime does not import it.
python -m pip install -r requirements-test.txt
python -m unittest -v test_register test_schema
python -O -m unittest -v test_register test_schema
```

The retained suite exercises many-to-many accounting, unknown versus zero,
malformed nested data, unique IDs, unresolved/out-of-scope links, typed CSV edits,
both full-view round-trips, mutated projection rejection, schema conformance,
deterministic outputs and CLI execution from a different working directory.
All subprocess tests have timeouts. Tests use temporary destinations and never
regenerate or modify the checked-in example. See `EXECUTION.md` for literal local
results and exact source hashes; these are not GitHub Actions receipts.

## Filesystem and operational limits

Each input file is bounded at 2 MiB and must be UTF-8. Existing output files and
directories, including a final-path symlink, are refused. A partial write failure
preserves earlier output rather than deleting evidence. The tool does not provide
transactional directory publication or protection against concurrent hostile
replacement of parent directories; run it in an operator-controlled workspace.
Very large individual CSV cells can hit the Python CSV parser's field-size limit
and are reported as input errors. No live data-volume benchmark is claimed.

This is offline draft preparation: no network, access-system mutation, outreach,
meeting action, submission, spending, contracting, payment or revenue recognition.

Seat: **ZZ-KESTREL-Q9D · GPT-6 Astra Pro**. Operation:
`uiowa038-recommendation-register-kestrelq9d-20260919`.
Original work order and continuation thread:
https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824436619569
