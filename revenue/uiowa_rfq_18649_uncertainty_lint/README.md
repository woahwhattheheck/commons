# Uncertainty-language lint — measured precision, or it doesn't ship

**UIOWA-089L.** A lint for one specific failure in the delivery kit's *own*
Markdown output: an absence stated as a property of an assessed entity rather than
as a property of the search. Companion to `uiowa_rfq_18649_qa_refusal_contract`
(089C), which ships the rule this enforces.

**Advisory. Read-only. Nothing here edits another lane, and nothing here ranks a
lane, an author or a seat** — a per-author league table would violate the same
boundary 089C ships (`B-002`), and that is exactly the point.

## The problem, which is precision and not detection

Detection is trivial. Grep 45 landed lanes for `there is no`, `has no`, `lacks`
and you get **132 hits**. Here is what they actually are:

```
"There is no HTTP field, CLI switch, or browser control that..."    <- software
"Item 'X-09' has no phase."                                         <- a record
"The checked-in rehearsal intentionally lacks ownership evidence."  <- a fixture
"A cell reading UNKNOWN records that the assessment lacks evidence."
                                                     <- the CORRECT form, flagged
```

All correct English. None of them is the failure. **A linter at that
false-positive rate is worse than no linter**, because the first person who runs it
switches it off, and then the real instances ship too. Reporting "132 problems in
the delivery kit" would itself be the sin this lane exists to prevent: a number
that sounds like a measurement and isn't.

## What is actually wrong, narrowly

An absence predicate whose **subject is an assessed entity** — a service, a group,
a team — rather than the evidence, the assessment, a tool, a record or a document:

```
FLAG   "SVC-DIRSYNC has no backup record."
OK     "We found no backup record for SVC-DIRSYNC in the material supplied."
```

Both may describe the same situation. The first reads as a property of the service
and **survives being quoted out of context**; the second stays a property of the
search. In a findings table, next to a severity, that is how an absence of evidence
becomes a finding of absence.

Six classes, only one of which is a finding (`cli.py explain`):

| Class | Result |
|---|---|
| `ABSENCE_ABOUT_ASSESSED_ENTITY` | **flagged**, with a suggested rewrite |
| `ok_subject_is_evidence_or_assessment` | the correct form |
| `ok_subject_is_tool_record_or_artifact` | software, record, fixture, document |
| `ok_hedged_or_conditional` | asserts nothing |
| `ok_quoted_as_an_example` | a lane demonstrating the wording it forbids |
| `ok_no_assessed_subject_found` | **default is pass** — a tool that guesses when unsure is the noisy grep again |

## Measured, not claimed

`fixtures/labelled_lines.json` holds **34 lines that were read individually and
hand-labelled**: 24 verbatim from real landed artifacts, 10 constructed. The two
origins are **scored separately** so the constructed cases cannot flatter the
corpus result. Real output of `python3 cli.py score`:

```
corpus       n=24   tp=1   fp=0   fn=0   tn=23   precision=1.00 recall=1.00
constructed  n=10   tp=4   fp=0   fn=0   tn=6    precision=1.00 recall=1.00
overall      n=34   tp=5   fp=0   fn=0   tn=29   precision=1.00 recall=1.00
```

**The constructed lines exist for a reason worth stating plainly: the real corpus
contains exactly one true positive**, so recall cannot be measured from it. Ten
authored lines — four that must flag, six near-misses that must not — make recall
mean something. They are labelled `constructed` in the fixture and never pooled
into the corpus number.

`test_lint.py` **fails if precision drops below 0.90 or recall below 0.80.** The
numbers in this README are a condition of the build, not a sentence in it.

## Result on the real corpus

`python3 cli.py scan /home/user/commons/revenue` — actual output, restricted to the
45 `uiowa_rfq_18649_*` lanes:

```
candidates examined : 97
flagged             : 1  (1.03% of candidates)

  ABSENCE_ABOUT_ASSESSED_ENTITY                 1
  ok_subject_is_tool_record_or_artifact        26
  ok_subject_is_evidence_or_assessment         24
  ok_no_assessed_subject_found                 32
  ok_hedged_or_conditional                      9
  ok_quoted_as_an_example                       5
```

**The finding is that the kit is close to clean on this**, which is the honest
result and a more useful one than a long list would have been. The single flag:

```
uiowa_rfq_18649_recovery_evidence/out/recovery_evidence_report.md:80
| RF-005 | high | `SVC-DIRSYNC` | Directory Synchronization Service has no
backup record and no restoration evidence of any kind. |
```

The subject is the service and the row carries a severity, so the sentence reads as
a property of `SVC-DIRSYNC`. The evidence-scoped rewrite — *"no backup record and no
restoration evidence was supplied for SVC-DIRSYNC"* — says the same thing and cannot
be quoted into a finding of absence. **Advisory: that lane's owner decides.**

## Run it

```
python3 cli.py scan <dir>              # findings + class breakdown
python3 cli.py scan <dir> --all        # every candidate, not just flags
python3 cli.py scan <dir> --json
python3 cli.py score                   # precision/recall vs the labelled set
python3 cli.py explain                 # what each class means
python3 -m unittest test_lint.py       # 33 tests
```

Python 3 **stdlib only**, no network, no model calls. Exit 0 when nothing is
flagged, 1 when something is. Tests run against the **frozen fixture**, never the
live repo — the corpus changes every time a seat lands, and a test bound to it would
fail for reasons unrelated to this code.

## Known limitations — read these before trusting a clean run

A clean scan is **not a clean bill of health**, and the CLI says so on every clean
run rather than printing a reassuring green line.

1. **`there is no X` is deliberately not checked.** It was the single most common
   candidate — 21 of 107 — and it is an existential: its subject *follows* the
   predicate. The backward subject scan read whatever came earlier in the sentence
   and flagged *"IAM AI readiness was not assessed; there is no finding in either
   direction"*, which is exactly right. Scanning forward only moves the ambiguity:
   in *"there is no incident review practice at ESS"* the entity is the scope, while
   in *"there is no evidence that the path works"* the following noun is the
   evidence. Separating those needs a parser, not a window. **So the check was
   removed rather than shipped noisy**, and `test_existential_phrasing_is_not_a_candidate`
   stops it being reintroduced by accident.
2. **Subject attribution is a window, and windows are wrong in long sentences.**
   Scanning the wider `revenue/` tree (364 candidates) surfaced a second flag in
   `bids/ky_ai_workforce_readiness_2026/README.md` where the tool read the subject as
   *"Software Group"* while the sentence's real subject, three clauses later, is
   *SKYCTC/KCTCS*. The classification is arguable there; **the subject attribution is
   simply wrong**. In a multi-clause sentence, trust the flag less.
3. **Entity recognition is a fixed vocabulary** — `SVC-*`/`SYS-*`/`APP-*` ids, the
   `ESS`/`RIS`/`IAM` codes, `the <name> service|team|group`, and capitalised
   `<Name> Service|Team|Group`. Real University service names are not in it and
   **must be added before live use** (see UNKNOWN below), or real instances pass
   silently.
4. **It reads Markdown only.** JSON and CSV artifacts are not scanned.
5. **It is a guard, not a proof.** A determined author can state absence as fact in
   wording no pattern list anticipates.

## Three defects this found in its own build

1. **Precision 0.29 from a word boundary.** A hyphen is a word boundary to `\b`, so
   `\bIAM\b` matched inside `IAM-OPS-002` — a *table row identifier* — and made it the
   subject of a predicate three cells away. 5 of 7 flags were that. Fixed with
   `(?<![-\w])`/`(?![-\w])` plus scoping the subject search to the predicate's own
   table cell. **Narrowing the window was worth more than any regex change.**
2. **A patch that silently did nothing.** A string replacement over the source
   didn't match because of one literal character, so an old quoted-span check stayed
   live and kept flagging a line the new code would have passed. It looked like a
   logic bug for a while. Rewritten with an asserting edit — *a patch that cannot
   fail loudly will eventually fail quietly.*
3. **A case-sensitivity bug found by the labels, not by reading.** *"The identity
   service lacks a documented escalation path"* — a textbook true positive — sailed
   through, because the `the <name> service` pattern had no `re.I`. It was invisible
   until there was a labelled set to measure against. **That is the argument for
   hand-labelling rather than eyeballing output.**

## What is real and what is draft

**Real:** the classifier, the CLI, the 34 hand-labelled lines, the 33-test suite,
and every number in this file — all copied from actual runs against the actual
landed bytes in `/home/user/commons/revenue`.

**Draft:** the entity vocabulary and the tool/evidence subject word lists are
curated by hand and tuned to this synthetic corpus.

**Not attempted:** no parsing, no model call, no score, no rating, no ranking of
lanes, authors or seats, and no edit to any other lane.

## University inputs still UNKNOWN

- **The real service, system and group names.** The entity vocabulary is the whole
  detector; without the University's actual names it will pass real instances
  silently. This is the one input that must be filled before live use.
- The engagement's own preferred wording for absence, if it has one — this lint
  encodes 089C's convention, not a University standard.
- Whether JSON/CSV deliverables carry prose that needs the same check.

## Interface

`cli.py scan <dir> --json` emits `{summary: {candidates_examined, flagged,
by_class, flag_rate}, findings: [{path, line, predicate, class, subject, text,
suggestion}]}`. No field carries a score, rating, percentile or author — asserted by
`test_no_score_rating_or_ranking_field_is_emitted`.
