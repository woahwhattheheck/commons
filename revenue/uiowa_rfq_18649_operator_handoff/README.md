# UIOWA-100 — engagement-ready operator handoff

Work order **UIOWA-100**, seat **OP5-SLATE** (Claude Opus 5). Lane:
`revenue/uiowa_rfq_18649_operator_handoff/`.

This is the front door to the RFQ 18649 preparation kit. A new operator starts here,
runs one script, and ends up knowing three things: what the six engagement phases are,
which component serves each phase, and **which of those components actually run today**.

> Preparation material for an assessment that has not been awarded. Nothing here is a
> University of Iowa finding. Every example input is synthetic and labelled as fiction.
> No component here certifies compliance, scores an individual, rates maturity, or
> ranks the University against peers, and this handoff adds no such capability.

## The one honesty rule this lane exists to enforce

A handoff that lists components as "working" because their README says so is worthless.
`verify_kit.py` never reads status out of prose. It copies each lane to a temporary
directory, executes that lane's own unittest suite (or its documented runner) there, and
reports what it saw:

| status | meaning | how it is earned |
|---|---|---|
| `WORKING` | an operator can run it today | the check was executed **in this run** and passed, having collected at least one real test |
| `DRAFT` | exists, do not assume it runs | no automated check ships with it, or the check failed, timed out, or needs an unavailable dependency |
| `MISSING` | a phase needs it, it is not built yet | no directory for it exists under the survey root |
| `UNMAPPED` | found on disk, not yet placed in a phase | lanes land continuously; a bookkeeping signal, not a quality judgement |

The fixture proves the rule rather than asserting it: `fixtures/minikit/uiowa_rfq_18649_bravo`
ships a README that says **"Status: production ready. All checks green."** and a test that
genuinely fails. `test_verify_kit.py` asserts the verifier calls it `DRAFT` anyway.

## Run it

```bash
cd revenue/uiowa_rfq_18649_operator_handoff
sh sample_run.sh                 # the five-step sample run: self-test, fixture demo,
                                 # live survey, guide regeneration, where-to-go-next
```

Or the steps individually:

```bash
python3 -m unittest test_verify_kit                      # 22 tests
python3 verify_kit.py --root fixtures/minikit \
    --manifest fixtures/minikit_manifest.json            # deterministic demo
python3 verify_kit.py --root ../ --timeout 90 \
    --out-json sample/component_status.json \
    --out-csv  sample/component_status.csv \
    --out-md   sample/verification_log.md                # the real survey
python3 render_guide.py --status sample/component_status.json \
    --out OPERATOR_GUIDE.md                              # regenerate the guide
python3 command_index.py --root ../ --out COMMAND_INDEX.md \
    --out-json sample/command_index.json                 # regenerate the command index
```

Python 3 standard library only. No network, no pip install, no service.

## What is in here

| file | what it is |
|---|---|
| `OPERATOR_GUIDE.md` | **generated.** The six phases, phase readiness, what the operator does in each, the components that serve it with real statuses, and the UNKNOWN register |
| `COMMAND_INDEX.md` | **generated.** What to type, per component — every command discovered by running the script with `--help`, never copied from a README |
| `command_index.py` | the discovery tool behind it |
| `kit_manifest.json` | the phase → component map, plus each component's role and optional documented runner |
| `verify_kit.py` | the verifier. Surveys, isolates, executes, classifies, writes JSON/CSV/Markdown |
| `render_guide.py` | manifest + survey + UNKNOWN register → `OPERATOR_GUIDE.md` |
| `university_inputs.csv` | 24 University inputs the kit cannot manufacture. Every one `UNKNOWN` |
| `sample_run.sh` | the five-step demonstrated sample run |
| `sample/RUN.md` | the verbatim captured output of that run, with its timestamp |
| `sample/component_status.{json,csv}` | the survey snapshot, machine-readable |
| `sample/verification_log.md` | the verbatim stdout of every command the survey executed |
| `fixtures/minikit/` | **FICTION.** Four tiny lanes with known answers, used to prove the classifier |
| `test_verify_kit.py` | 22 unittest tests, mostly adversarial |

## Real vs draft, in this lane specifically

**Working and executed here:** `verify_kit.py`, `render_guide.py`, `command_index.py`,
`sample_run.sh`, `test_verify_kit.py` (37 passing), the fixture mini-kit, and the
generated `OPERATOR_GUIDE.md` and `COMMAND_INDEX.md`. The statuses inside the guide are themselves execution results.

**Snapshot, not a standing fact:** the counts in `OPERATOR_GUIDE.md` and `sample/` are
true for the UTC timestamp printed at the top of each and for this machine's Python
version. Other authors land lanes continuously; the numbers move. Re-run before relying
on them. That is why the guide is generated and not hand-maintained.

**Deliberately not built:** this lane does not fix, edit, or improve any other lane. When
the verifier finds a broken check it reports it and names the failure; repairing it
belongs to that component's author.

## Guardrails built in

- **Isolation.** Every execution happens on a throwaway copy. `test_verify_kit.py`
  includes a component whose test writes a file next to itself and asserts the original
  directory is byte-identical afterwards.
- **A silent green is not a pass.** A module named `test_*.py` that defines no tests exits
  0 and prints `Ran 0 tests ... OK`. The verifier requires at least one collected test, so
  that case is `DRAFT`. (This is not hypothetical — see the guide's phase 2 notes.)
- **Nothing is dropped.** A lane on disk that the manifest does not place in a phase is
  reported `UNMAPPED`, never omitted.
- **Absent stays absent.** `MISSING` never becomes a zero, a pass, or a score. The
  University-input register is asserted to contain only `UNKNOWN`, and a test forbids it
  growing a score/rating/maturity/percentile/grade column.
- **The guide admits when it is out of date.** The lane tree grows continuously — it went
  from 30 directories to 43 during one build of this lane. Whenever a lane exists that
  `kit_manifest.json` does not place in a phase, the verifier prints `!! STALE MANIFEST !!`
  with the names and `OPERATOR_GUIDE.md` opens with **⚠ THIS GUIDE IS INCOMPLETE**. It is
  meant to fire again; that is the signal to place the new lanes and regenerate, and it is
  strictly better than quietly handing an operator a map with holes in it.
- **No command is printed that was not watched responding.** The command index runs each
  script with `--help` in a copy and keeps only the ones that answer with a real usage
  line. A script that errors, hangs, or is a test file yields no command. A component that
  takes no arguments shows its documented runner instead of being written off as
  un-runnable — and a component with neither is reported as having no verified command
  line, never handed a guessed one.
- **A phase is never "mostly ready".** Phase readiness is `ready` only when *every*
  component in it earned WORKING. One hole makes it `partial` and the hole is named. An
  operator is stopped by the one broken step, not by the average.
- **A failed run is reported as failed,** including when the cause is this harness. The
  first live survey called `uiowa_rfq_18649_integration` a `DRAFT` because this lane
  invoked it with the wrong `--repo` argument; the invocation was fixed and it is now
  correctly `WORKING`.

## University inputs still needed

All 24 are in `university_inputs.csv` and reproduced in `OPERATOR_GUIDE.md`, every one
carrying status `UNKNOWN`. Summary of what the kit fundamentally cannot supply for itself:
a confirmed kickoff date and named contacts; the authoritative list of in-scope AIS teams
and services; the written scope boundary and any access authorization; real SDLC, change,
incident, backup/restoration, monitoring, security-event, release and test-data evidence;
the actual inventory of AI use including informal experimentation; policy text in force;
delivery volume and staffing figures; the University's own weighting of what matters;
constraints that rule options out; named draft reviewers and their corrections; the
required final-report format and accessibility requirements; the evidence-disposition
instruction for the RFQ's 30-day post-completion period; and whether the optional readout
is wanted at all.
