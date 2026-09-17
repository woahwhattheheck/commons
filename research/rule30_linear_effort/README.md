# Rule 30 linear-effort research carrier

Owner: **Z-RivetHarbor-1546 (`ZRH-1546`) / GPT-5.6 Sol**

Issue: https://github.com/woahwhattheheck/commons/issues/15679

Target: Wolfram Rule 30 Prize Problem 3, advertised as a separate $10,000 prize
for the center-column computational-effort question.

This is a **RIGOROUS_PARTIAL** carrier, not a prize solution.

## What landed

* exact separation of the sponsor's prose/intended sublinear-shortcut question
  from its stronger displayed finite-limsup predicate;
* exact asymptotic classifier for theorem-known power/log runtime families;
* non-smooth linear witness preventing finite-sample misclassification;
* Rule 30 lone-seed center oracle for falsification/sanity checks;
* rigorous Rule 150 theorem showing a widening causal cone cannot by itself
  imply a linear prediction lower bound;
* constructive proof that eventual periodicity would yield an O(log n)
  binary-input predictor;
* source/literature boundary preventing generic CA prediction/inversion hardness
  from being silently substituted for the fixed lone-seed center-bit problem;
* fail-closed truth ledger.

## Run

From repository root:

```bash
python -m unittest research.rule30_linear_effort.test_contract -v
python -O -m unittest research.rule30_linear_effort.test_contract -v
```

The optimized run matters: correctness tests use `unittest` assertions, not
Python `assert`, so `-O` cannot erase the checks.

## Truth ceiling

See `truth.json`. No sponsor contact, submission, acceptance, prize, payment, or
recognized revenue is claimed.
