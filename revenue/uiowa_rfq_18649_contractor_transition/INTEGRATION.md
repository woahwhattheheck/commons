# UIOWA-108 integration and completion-integrity review

Seat: ZZ-MERIDIAN-Q7 / GPT-6 Astra Pro. Original scenario, implementation,
fixtures, report design and 34-test suite: OP5-KELVIN / Claude Opus 5.
Operation: `uiowa108-main-integration-meridianq7-20260919`.

## Source and preservation

Source snapshot: `88ce48dd9042e0cc11c01bde463c227607b2cee8`, branch
`claude/multi-agent-slack-demo-4ikzfs`, directory
`revenue/uiowa_rfq_18649_contractor_transition/`.

The original README, test suite, two fixtures and three generated sample files
are retained byte-for-byte. Only `scenario.py` and `transition.py` change their
behavior. `test_completion_integrity.py` supplies the new regression cases.
The root test wrapper runs both complete component suites on the existing test
surface; no new workflow or paid execution service is introduced.

## What changed

A completion now requires an actual ISO calendar date or timestamp, a text
locator, a declared action and an integrity-clean change record. Duplicate IDs,
broken or wrong-kind references and invalid record structure cannot establish
completion. Reference types distinguish people from applications; an
application ID is not a successor person.

A completed action does not settle unresolved ownership, and one completed
action does not hide another recorded pending action. Valid partial evidence
is retained in the report, with the unresolved condition named. Packet-wide
integrity findings prevent the whole transition from closing, including a
record that could not be indexed. Safe integrity findings still render for
review; structurally invalid JSON returns exit 2 without a traceback or output.

These rules operate on the current supplied scenario packet. A superseded
historical request must be reconciled by the packet's author; the tool does
not infer supersession from dates or silently drop earlier records.

## Executed validation

Complete standalone component, Python standard library, ephemeral cloud
container. No production module was stubbed and no real account was queried.
The original two modules, test file and fixtures were individually matched to
GitHub Git-blob IDs before baseline execution.

```
# Unchanged source: original suite
python -m unittest -v test_transition
Ran 34 tests in 2.676s
OK

# Unchanged source: added negative and positive controls
python -m unittest -v test_completion_integrity
Ran 16 tests in 4.986s
FAILED (failures=28, errors=4)

# Repaired source: original and added tests together
python -m unittest -v test_transition test_completion_integrity
Ran 50 tests in 7.758s
OK

python -O -m unittest -v test_transition test_completion_integrity
Ran 50 tests in 7.940s
OK
```

`py_compile` passed for both production modules and both suites. Direct CLI
execution under normal and optimized Python returned exit 1 with the unchanged
worked result:

```
items=6 completed=2 unresolved=2 no_evidence=2 closed=False issues=0
```

All three generated sample files remain byte-identical to the published
samples, under both direct CLI modes. The unsafe fixture still produces exit 3
and no output files in the retained tests. Empty input does not close by
vacuous truth. Positive controls retain valid dated completion.

## Exact executed object IDs

| File | Git blob SHA-1 |
| --- | --- |
| scenario.py | bdd8a4444b881745ed19dea5bd5ed3b62d5f9f8f |
| transition.py | 3fd81bba864eae457a062fac49d379d182959e37 |
| test_transition.py | 47f7bcdd0f54e1c04396dc6e1b1c58a5a9fb9248 |
| test_completion_integrity.py | 1949d33154f7c8c89b0c44691ed68dc21a5baab0 |
| fixtures/contractor_transition.json | 0939e7cd6c72920acc7a576d9e2070390c0b66a9 |
| fixtures/contractor_transition_unsafe.json | 3640946cb019df27d5c457fb57399b4f72919a44 |
| sample_output/transition_items.csv | 9dfbfdf8fe891f0105c6f91e0a3163526b3ef525 |
| sample_output/transition_report.json | 9188819f31f8552b8194fb0dcc28df9e658a657c |
| sample_output/transition_report.md | baf63c61c4b7b2909edc60ae21d9f7c4b1467e53 |

## Interpretation limits

Everything is fictional. A locator and a typed date establish consistency of
this demonstration packet; they do not authenticate an external system or
prove a real revocation. The supplied inventory is not proved exhaustive, and
a completed credential rotation is not evidence that every offboarding action
has occurred. The realism screen checks documented shapes, not all possible
personal information. The five uncollected University inputs in the original
README remain unknown.

This receipt is component execution, not hosted Actions success, full-repo
integration proof, a University finding, or main-merge evidence. The PR's live
provider records and final main readback control those separate states.
