# UIOWA-134 — dependency-driven schedule recovery

An offline, standard-library Python planning tool for the proposed six/eight-week workshare. It consumes UIOWA-002 staffing exports rather than creating a second labor model. It does not make appointments, infer actual participant availability, or turn forecast readiness into authorization, acceptance, earned invoices or payment.

Start with [WORKED_CALENDARS.md](WORKED_CALENDARS.md): both baseline calendars, three delayed-input calendars for each, critical-path changes, unaffected work, conditional recovery comparisons and proposed milestone readiness. [summary.csv](summary.csv) is the corresponding 16-row machine-readable summary.

## Run and reproduce

Python 3.10 or later, no third-party packages or network calls:

```sh
cd revenue/uiowa_rfq_18649_schedule_recovery
python recovery.py --out /tmp/uiowa-134
python -m unittest -v test_recovery
python -O -m unittest -v test_recovery
```

The CLI writes `WORKED_CALENDARS.md`, `calendar-6-week.md`, `calendar-8-week.md`, `scenarios.json`, and `summary.csv`. The detailed calendars contain every binding dependency and overload interval; JSON retains all critical tasks/edges, source assumptions and cost-by-role. Output order and bytes are deterministic, including between normal and optimized Python. Invalid planning input exits 2 with a diagnostic.

To consume a new **undelayed** native UIOWA-002 export:

```sh
python revenue/uiowa_rfq_18649_staffing/model.py --out /tmp/uiowa-002
python revenue/uiowa_rfq_18649_schedule_recovery/recovery.py \
  --staffing-plans /tmp/uiowa-002/staffing_plans.json \
  --scenarios revenue/uiowa_rfq_18649_schedule_recovery/scenario-inputs.json \
  --out /tmp/uiowa-134-current
```

Run those two commands from the repository root. A native array containing exactly the six- and eight-week plans is accepted. The checked-in fixture uses a `plans` wrapper to preserve provenance. A source change that no longer round-trips every baseline task window is rejected for explicit adapter reconciliation, not silently rewritten. Source hours, role capacities and task windows remain editable through the native staffing model.

## Source boundary and attribution

UIOWA-002 was built by **ZZ-KESTREL-R8V2**. This UIOWA-134 extension is **ZZ-KESTREL-134Q, GPT-6 Astra Pro**. These are separate seats and work units.

The initial native source is `revenue/uiowa_rfq_18649_staffing/model.py` at commit `aaff1e3e196dcd9dddf15484fb7a5d74f9c5ba50`, Git blob `c1f384f6e38e2f085891d8de3a4eb107b1e7582f`. The actual 9,313-byte source was reconstructed from its GitHub text, matched to that Git blob and executed. `staffing-source.json` projects the resulting native task windows/hours, capacities, zero-delay fields and totals; it omits unused onsite fields and derived displays. This fixture is an illustrative planning case, not a University observation.

Baseline person-hours reconcile exactly:

| Plan | Clark | TJLabs | University |
|---|---:|---:|---:|
| Six weeks | 131 | 243 | 104.25 |
| Eight weeks | 134 | 247 | 106.25 |

The source uses 21 participants grouped into nine sessions; this adapter does not convert those into 21 separate interviews. It preserves the existing five planning-package labels and cross-cutting coordination rather than amending commercial scope.

## Dependency and effort interpretation

Time is relative working days: day zero is the planning origin, five working days make a relative week, and task windows are half-open `[start, finish)`. No weekend/holiday calendar or absolute date is assumed. Window duration is a planning envelope, not continuous attendance.

`engine.py` supports finish-to-start (FS), start-to-start (SS), and finish-to-finish (FF) dependencies with explicit nonnegative input lags, deterministic topological scheduling, backward-pass float, all critical tasks/edges and one representative driving chain. Missing external timing is `null`, never zero; it propagates only along affected dependencies.

The adapter adds explicit planning assumptions to the native weekly envelopes: rolling interviews/debrief/matrix/synthesis/roadmap; draft readiness before prime and University review; consolidated comments relative to the **end of both reviews**; corrections and final QA afterward. Rolling SS offsets preserve source windows, while FF constraints prevent downstream completion before source evidence. Independent kickoff, intake, coordination/pre-read and peer-context work is not automatically frozen by a delayed full-evidence tranche.

All A01–A15 production work must finish before final-artifact readiness. A16 coordination extends at the native per-day rate until that readiness. Extra recoordination/rework hours are separate editable scenario inputs; delays alone do not invent additional production hours. When final timing is unknown, total coordination, full effort and total labor exposure remain unknown; known non-coordination estimates remain visible.

Effort is uniformly distributed over each task window to show demand. Interval-level overload detection avoids hiding a one-day surge inside a low weekly average. It **does not resource-level** the plan or establish real staffing availability. The aggregate native capacity assumptions are Clark 32, TJLabs 48 and University 24 hours/week.

## Eight scenario cases per plan

The default packet includes baseline, ten-workday-late interviews, a complete evidence tranche ten workdays late, comments ten workdays after the review envelope, three conditional recoveries, and an unknown-evidence-date case. Edit delays, extra hours, rates and recovery conditions in `scenario-inputs.json`; retain the named default cases for the comparison report.

Rolling synthesis may start on stable evidence but cannot close before the complete matrix. Rolling evidence staging still requires **two explicit working days of reconciliation after the complete tranche**. Review surge shortens the corrections and QA envelopes to an explicit three-day assumption while retaining their original hours and exposing added daily demand. Each recovery names conditions that must be confirmed before use; it is not a booking or a commitment.

The worked six-week case moves final readiness from day 30 to day 40 under each isolated delay. Conditional recoveries finish at days 35, 32 and 38 respectively. The eight-week counterparts finish at 45, 40 and 48 against delayed day 50. Faster recovery is not automatically cheaper or feasible: the eight-week baseline has no modeled overload, but interview and review acceleration introduce one.

The illustrative internal labor rates are Clark USD 100/hour and TJLabs USD 80/hour. University effort is **unpriced, not free**. These are editable scenario assumptions, not proposed fee rates. Cost outputs exclude travel, tooling, taxes, collection timing and other expenses; no complete engagement-margin claim is made.

## Proposed payment triggers

The three proposed amounts remain USD 9,600 for written authorization and kickoff, USD 9,600 for a qualifying draft, and USD 4,800 at written final acceptance. A delayed consolidated-comment cycle does not retrospectively move the draft-readiness proxy. Final-artifact readiness does not supply written acceptance. The kickoff readiness proxy uses the end of the source's week-one workshop envelope, not an invoice date.

Every output preserves `trigger_status=NOT_VERIFIED`, `actual_trigger_day=null`, `invoice_earned=false`, `paid=false`, and `scheduling_authority=false`. This is a scenario model, not a payment ledger.

## Executed validation

45 unit/regression tests passed in normal Python and 45 in a real `python -O` process. Both CLI modes also ran and produced byte-identical exports. Tests cover generalized precedence, parallel critical paths, unknown propagation, malformed numeric inputs, cycles, interval-load conservation, native baseline round-trip, all scenario dependency inequalities, delayed-comment timing, recovery closure/reconciliation, retained effort, capacity overloads, unpriced costs and unchanged proposed payment semantics. These are scoped cloud-container executions, not a claim that repository-wide or hosted CI passed.

Work record: [Commons issue #16183](https://github.com/woahwhattheheck/commons/issues/16183). Coordination: [UIOWA-134 work-order thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789825543878419). These are internal build/evidence references, not a customer delivery destination.
