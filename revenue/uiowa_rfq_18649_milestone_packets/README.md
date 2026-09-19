# Milestone delivery and billing evidence packets (UIOWA-135)

Builds three reusable milestone packet folders from one engagement definition,
verifies every cited artifact by opening it, and emits an automated completeness
report that says exactly what is not ready and why.

Python 3 standard library only. No network at runtime, no installs.

**Everything in `fixtures/` is fiction.** It is a synthetic engagement invented to
exercise the tooling. It contains no University of Iowa data and no University
finding, and every generated document carries a `SYNTHETIC / FICTION` banner.

## Run it

```
python3 milestone_packets.py fixtures/engagement.json \
    --artifact-root fixtures/artifacts \
    --output-dir examples \
    --as-of 2026-11-25
```

Exit codes are distinct, because "the packet is not ready" and "the tool broke"
need different responses:

| code | meaning |
| --- | --- |
| 0 | every packet is ready to submit as a draft |
| 1 | the completeness report found errors — normal, actionable |
| 2 | the input could not be read, or violated the contract |

The committed run in `examples/` exits **1**, on purpose: the fixture contains
real gaps and the report's job is to refuse to call them fine.

Tests:

```
python3 -m unittest test_milestone_packets -v     # 55 tests
python3 -O -m unittest test_milestone_packets     # also passes optimized
```

## What it produces

```
examples/
  COMPLETENESS_REPORT.md         human-readable, all three milestones
  completeness_report.json       same content, machine-readable
  packets/01-m-1-kickoff/
    PACKET.md                    the packet: milestone, criteria, index, dependencies, findings
    TRANSMITTAL.md               what was sent, when, with digests
    INVOICE_DESCRIPTION_DRAFT.md a description to paste into an invoice — not an invoice
    delivered_file_index.csv     one row per artifact, with custody and disposition
    packet.json                  machine-readable packet record
  packets/02-m-2-draft_delivery/   (same five files)
  packets/03-m-3-final_acceptance/ (same five files)
```

## The worked example, and what it demonstrates

| Milestone | Kind | Amount | Submitted | Acceptance | Status |
| --- | --- | --- | --- | --- | --- |
| M-1 | KICKOFF | $4,800.00 | DELIVERED | ACCEPTED_RECORDED | READY_TO_SUBMIT_AS_DRAFT (0E/0W) |
| M-2 | DRAFT_DELIVERY | $9,600.00 | DELIVERED | PENDING | READY_TO_SUBMIT_AS_DRAFT (0E/1W) |
| M-3 | FINAL_ACCEPTANCE | $9,600.00 | NOT_SUBMITTED | NOT_REQUESTED | NOT_READY (3E/1W) |

Amounts total **$24,000.00**, checked as **2,400,000 integer cents**.

M-1 and M-2 are the strength: complete packets, full custody on every row, every
citation opens. M-3 is a real gap, with three *structurally different* failures:

- `E_ARTIFACT_DOES_NOT_OPEN` — the appendix is cited but not at the cited path.
- `E_VERSION_NOT_IDENTIFIABLE` — the readout outline **opens fine** and has a
  digest, but carries no declared version. A checker that only asks "does the
  citation resolve?" passes this. A digest with no version label tells you two
  copies differ, not which version the client was sent.
- `E_MISSING_DISPOSITION` — one row has no disposition decision. It is **not**
  given a default; it stays UNKNOWN and a person is told to decide.

Plus two warnings, which are conditions rather than packet defects: M-2's
evidence export is 15 days past its needed-by date, and M-3 has an open
dependency with *no agreed date at all* — reported as "cannot be called on time
or late" rather than reading as fine.

## The rules it enforces

**Delivery is not acceptance.** Submission and acceptance are separate. Nothing
can reach `ACCEPTED_RECORDED` except a dated `AcceptanceRecord` naming a party
and a reference. A delivery alone leaves acceptance `PENDING`.

**It cannot claim an invoice or a payment.** `paid`, `invoice issued`,
`approved for payment`, `payment received` are refused in rendered prose,
always — this tool has no authority to issue an invoice or observe a payment.
Acceptance language is refused *only when no acceptance record exists*.

> The first version of this guard was a flat banned-word list, and it refused to
> render M-1's genuine, dated client acceptance record. A word list cannot tell
> an assertion from a record. The rule is now conditional on the evidence.

**Money is integer cents.** Float dollars are refused: `8000.00 + 8000.00 +
7999.99` prints like $24,000.00 and is not. A bare digit string like `"24000"`
is also refused as ambiguous — an int means cents here, so the same digits could
mean $240 or $24,000. That factor-of-100 disagreement was found by the test
suite, not by reading the code.

**UNKNOWN is never a zero.** A missing size is UNKNOWN, not 0. A missing date is
UNKNOWN, not today. The sentinel refuses arithmetic, comparison, and truthiness,
so absent data cannot be silently consumed as a value.

**Every index row carries source, custodian, storage location, and disposition.**
Any of the four missing is an error, named per field.

## Safety: this tool cannot delete anything

It is pointed at a directory of delivered client artifacts. If it could remove,
move, rename, or truncate one, a routine "regenerate the packets" run could
destroy the evidence the packet exists to account for. So that is asserted, not
promised, by `TestNoDestructiveFilesystemOperations`:

- **Static** — an AST scan of all six production modules for destructive calls
  (`os.remove`, `shutil.rmtree`, `unlink`, `rename`, `replace`, `subprocess`, …)
  and for destructive names even being imported.
- **Static** — every `open()` in write mode must sit inside the single approved
  writer, `packets.write_output`, which refuses any target outside `--output-dir`.
- **Runtime** — a full build runs against a copied artifact tree that is sha256
  hashed before and after; the test asserts the tree is byte-identical and that
  no file was added or removed.
- **Runtime** — path traversal is refused in both directions: the resolver will
  not read outside `--artifact-root`, and the writer will not write outside
  `--output-dir`.

The tool reads cited artifacts and writes only into its own output directory.

## Real vs. draft

**Real and runnable:** the schema, resolver, schedule arithmetic, completeness
engine, renderers, CLI, the 55 tests, and the committed `examples/` run — all of
which execute exactly as shown.

**Draft:** every *document* it produces. The packets are usable drafts for a
person to review and send. Nothing here issues an invoice, records an acceptance,
or represents a payment, and no packet asserts that a milestone was approved.

`READY_TO_SUBMIT_AS_DRAFT` means one narrow thing: the packet contains no
unverifiable citation and no unmade disposition decision. It is not an approval,
an acceptance, or a billing authorization.

## University inputs that are still UNKNOWN

These are placeholders in the fixture, not findings. Each must be bound before
any live use:

- **The controlling clause locators.** The $24,000 total and the three-milestone
  shape come from the work order. The exact RFQ/PSA clause governing acceptance,
  invoicing, and the post-completion obligation window is not in the material
  available here. (ZZ-Lattice flagged the same gap for the 30-day clause on
  UIOWA-099.) `schedule.deadline_from()` computes such a window from an explicit
  day count — it does not assert which count applies.
- **The milestone split.** 20/40/40 is synthetic. The real split, milestone
  names, and dates are unknown.
- **The acceptance criteria wording** per milestone.
- **Who may record acceptance**, and through what process.
- **Real custodians, storage locations, and the records-retention disposition
  policy** that decides retain / return / destroy per artifact class.
- **The invoicing process** — numbering, AP routing, and required description
  format.

## Files

| File | Role |
| --- | --- |
| `schema.py` | Money in integer cents, the UNKNOWN sentinel, milestone/index/criterion/dependency/acceptance types, refusal of claim-bearing input states |
| `resolve.py` | Read-only artifact resolution: opens each cited path, records size + sha256 + declared version |
| `schedule.py` | Pure date arithmetic; every function takes an explicit `as_of` so no output depends on when it ran |
| `completeness.py` | The completeness report: ERROR vs WARN, per-milestone and engagement-level findings |
| `packets.py` | The renderers and the single approved writer |
| `milestone_packets.py` | CLI |
| `fixtures/` | The synthetic engagement and its artifact tree (one artifact deliberately absent) |
| `examples/` | Committed output of the run above |
| `test_milestone_packets.py` | 55 tests, including the safety property |
