# Claim-language audit — traceability and promotional language in a deliverable

Checks an assessment deliverable for statements that cannot be traced to a
finding, and for language that substitutes characterisation for evidence.

All fixtures are **synthetic fiction**. No University of Iowa finding, service,
team or measurement appears anywhere in this directory.

## What this catches that a citation/link checker does not

A link verifier answers *"does this reference resolve?"*. This answers two
different questions:

1. **Does this statement have a reference at all?** — `UNSOURCED_CLAIM`
2. **Is the thing it references capable of supporting it?** —
   `UNKNOWN_PRESENTED_AS_FINDING`. A citation can resolve perfectly to a finding
   whose recorded state is `UNKNOWN`, and a number asserted against it is still
   unsupported. That is the rule this kit exists for.

## Rules

| code | severity | fires when |
|---|---|---|
| `UNSOURCED_CLAIM` | error | statement carries a quantity or a comparative and cites nothing |
| `PROMOTIONAL_LANGUAGE` | error | tiered lexicon hit (below) |
| `UNQUANTIFIED_COMPARATIVE` | error | "faster" / "improved" / "reduced" with no figure in the sentence |
| `UNKNOWN_PRESENTED_AS_FINDING` | error | asserts a figure while citing a finding in state `UNKNOWN` / `NOT_ASSESSED` |
| `CONTRADICTED_FINDING_CITED_AS_SUPPORT` | error | cites a `CONTRADICTED` finding in a sentence framed as support |
| `DANGLING_CITATION` | error | cited id is not in the register |
| `ABSOLUTE_WITHOUT_SOURCE` | warning | "always" / "never" / "every" with no citation |
| `EMPTY_SUPPRESSION` | error | the audit is suppressed with no written reason |

### The lexicon is tiered, not a word list

A flat banned-word list fires on "comprehensive test coverage" and gets switched
off, taking the useful rules with it. So severity depends on the rest of the
sentence:

- **Tier A (22 terms)** — always a defect. "world-class", "best-in-class",
  "industry-leading", "seamless", "turnkey", "best practice", "synergy". These
  carry no information about the assessed subject.
- **Tier B (20 terms)** — a defect only when the sentence carries **no figure**.
  "significantly", "substantially", "dramatically", "robust", "comprehensive",
  "mature". *"improved substantially, from 6.1 days to 4.2 days"* passes;
  *"improved substantially"* does not. Asserted by test.
- **Tier C (13 terms)** — a defect with **neither a figure nor a citation**.
  "ensures", "guarantees", "proven", "eliminates", "optimizes".

### The suppression hatch

`<!-- audit-ok: reason -->` silences the language rules on that line. The reason
is **required** — a bare suppression raises `EMPTY_SUPPRESSION`. Suppression
never silences `DANGLING_CITATION`: a style judgement can be overruled, a wrong
fact cannot.

## The before/after pair

Two executive summaries carrying **the same substance**. Nothing was deleted to
make the second pass; untraceable claims were replaced with what the evidence
supports.

```bash
python3 claim_audit.py --doc fixtures/exec_summary_BAD.md  --register fixtures/register.json   # 22 errors, 1 warning, exit 1
python3 claim_audit.py --doc fixtures/exec_summary_GOOD.md --register fixtures/register.json   # 0 errors, exit 0
python3 -m unittest test_claim_audit -v
```

Saved output: `out/report_BAD.txt`, `out/report_GOOD.txt`, `out/report_BAD.json`.

## Corpus mode

```bash
python3 claim_audit.py --corpus <tree> --rules language
```

Read-only sweep over a tree of markdown. No register is available, so only the
two rules that need none are run. Results are **review candidates, not defects**:
an engineering README is not a client deliverable and is not held to a
leadership-paper standard. Saved output: `out/corpus_sweep.txt`.

## What is real and what is draft

**Real and runnable:** the segmenter, all eight rules, the tiering, the
suppression mechanism, the corpus sweep, the CLI, 28 tests passing normal and
`python -O`.

**Draft / illustrative:** the register and both executive summaries. They exist
to exercise the rules and are not findings about anything.

## University inputs still UNKNOWN

- the real finding register and the recorded **state** of each finding — without
  states, `UNKNOWN_PRESENTED_AS_FINDING` and
  `CONTRADICTED_FINDING_CITED_AS_SUPPORT` cannot run at all;
- which documents are client-facing deliverables and which are internal working
  notes — the tier calibration differs and this kit does not guess;
- whether the engagement wants `ABSOLUTE_WITHOUT_SOURCE` at error or warning;
- any house style rules that would add or remove lexicon terms.

The lexicon is data in `rules.py` precisely so it can be argued with rather than
accepted.

## Scope boundary

Read-only. It rewrites no text, scores nothing, and produces no maturity,
certification, compliance or peer-percentile claim. It makes no judgement about
any person. Determinism: no clock, no RNG, sorted traversal — repeat runs are
byte-identical.
