import assert from 'node:assert/strict';
import test from 'node:test';
import {
  SKILLS,
  classifyMisconception,
  createLearner,
  evaluateAnswer,
  generateQuestion,
  masteryFor,
  restoreLearner,
  selectSkill,
  serializeLearner,
  snapshotSummary,
  syntheticMisconceptionDemo,
  updateLearner,
  validateLearner,
} from '../engine.mjs';

test('fresh learner is valid and grade-gated', () => {
  const learner = createLearner({ grade: 2, seed: 'test' });
  assert.equal(validateLearner(learner), true);
  assert.equal(snapshotSummary(learner).length, 3);
  assert.deepEqual(snapshotSummary(learner).map((x) => x.id), ['addition', 'subtraction', 'place-value']);
});

test('question generation is deterministic', () => {
  const learner = createLearner({ grade: 5, seed: 'fixed' });
  for (const skill of SKILLS) {
    const a = generateQuestion(learner, skill.id, 7);
    const b = generateQuestion(learner, skill.id, 7);
    assert.deepEqual(a, b);
  }
});

test('different session seeds perturb questions', () => {
  const a = generateQuestion(createLearner({ grade: 5, seed: 'a' }), 'multiplication', 0);
  const b = generateQuestion(createLearner({ grade: 5, seed: 'b' }), 'multiplication', 0);
  assert.notEqual(a.id, b.id);
});

test('invalid input never updates learner', () => {
  const learner = createLearner({ grade: 3, seed: 'test' });
  const q = generateQuestion(learner, 'addition');
  for (const raw of ['', ' ', 'NaN', 'Infinity', '4x', null, true]) {
    const evaluation = evaluateAnswer(q, raw);
    assert.equal(evaluation.valid, false);
    assert.throws(() => updateLearner(learner, q, evaluation));
  }
  assert.equal(learner.step, 0);
});

test('correct answers increase mastery and spacing', () => {
  let learner = createLearner({ grade: 3, seed: 'test' });
  const before = masteryFor(learner.skills.addition);
  const q = generateQuestion(learner, 'addition');
  learner = updateLearner(learner, q, evaluateAnswer(q, String(q.answer)));
  assert.ok(masteryFor(learner.skills.addition) > before);
  assert.equal(learner.skills.addition.streak, 1);
  assert.ok(learner.skills.addition.nextDue > 0);
  assert.equal(learner.totalCorrect, 1);
});

test('incorrect answers reduce mastery and return skill soon', () => {
  let learner = createLearner({ grade: 3, seed: 'test' });
  const before = masteryFor(learner.skills.multiplication);
  const q = generateQuestion(learner, 'multiplication');
  learner = updateLearner(learner, q, evaluateAnswer(q, String(q.answer + 1)));
  assert.ok(masteryFor(learner.skills.multiplication) < before);
  assert.equal(learner.skills.multiplication.nextDue, 1);
  assert.equal(learner.totalCorrect, 0);
});

test('addition off-by-one misconception is detected', () => {
  const learner = createLearner({ grade: 3, seed: 'off-one' });
  const q = generateQuestion(learner, 'addition');
  assert.equal(classifyMisconception(q, q.answer + 1), 'counting-off-by-one');
});

test('multiplication-as-addition misconception is detected', () => {
  const learner = createLearner({ grade: 3, seed: 'mult' });
  let q = generateQuestion(learner, 'multiplication');
  // Rarely a+b can equal a*b (2x2); move deterministically to another index if so.
  if (q.operands[0] + q.operands[1] === q.answer) q = generateQuestion(learner, 'multiplication', 1);
  assert.equal(classifyMisconception(q, q.operands[0] + q.operands[1]), 'addition-for-multiplication');
});

test('place value digit-vs-value misconception is detected', () => {
  const learner = createLearner({ grade: 2, seed: 'place' });
  const q = generateQuestion(learner, 'place-value');
  assert.notEqual(q.operands[1], q.answer);
  assert.equal(classifyMisconception(q, q.operands[1]), 'digit-vs-value');
});

test('stable misconception raises an explicit signal', () => {
  let learner = createLearner({ grade: 3, seed: 'signals' });
  for (let i = 0; i < 2; i += 1) {
    let q = generateQuestion(learner, 'multiplication');
    const wrong = q.operands[0] + q.operands[1];
    if (wrong === q.answer) {
      // Use a known one-off pattern rather than accidentally answering 2×2 correctly.
      learner = updateLearner(learner, q, evaluateAnswer(q, String(q.answer + 1)));
    } else {
      learner = updateLearner(learner, q, evaluateAnswer(q, String(wrong)));
    }
  }
  const row = snapshotSummary(learner).find((item) => item.id === 'multiplication');
  assert.ok(row.misconception !== null);
});

test('scheduler never selects above grade', () => {
  for (let grade = 1; grade <= 5; grade += 1) {
    const learner = createLearner({ grade, seed: `g${grade}` });
    const chosen = selectSkill(learner);
    const skill = SKILLS.find((item) => item.id === chosen.skillId);
    assert.ok(skill.grade <= grade);
  }
});

test('scheduler prioritizes a repeatedly missed due skill', () => {
  let learner = createLearner({ grade: 3, seed: 'priority' });
  for (let i = 0; i < 4; i += 1) {
    const q = generateQuestion(learner, 'multiplication');
    learner = updateLearner(learner, q, evaluateAnswer(q, String(q.answer + 1)));
  }
  // Advance due state deterministically without adding evidence to multiplication.
  learner.step = Math.max(learner.step, learner.skills.multiplication.nextDue);
  const selected = selectSkill(learner);
  assert.equal(selected.skillId, 'multiplication');
});

test('serialization round-trip is exact', () => {
  let learner = createLearner({ grade: 4, seed: 'roundtrip' });
  const q = generateQuestion(learner, 'fractions');
  learner = updateLearner(learner, q, evaluateAnswer(q, String(q.answer)));
  const restored = restoreLearner(serializeLearner(learner));
  assert.deepEqual(restored, learner);
});

test('restore rejects version, grade, and injected misconception tampering', () => {
  const learner = createLearner({ grade: 3, seed: 'tamper' });
  for (const mutate of [
    (x) => { x.version = 999; },
    (x) => { x.grade = 99; },
    (x) => { x.skills.addition.misconceptions.evil = 1; },
    (x) => { x.skills.addition.alpha = Number.POSITIVE_INFINITY; },
  ]) {
    const copy = JSON.parse(JSON.stringify(learner));
    mutate(copy);
    assert.throws(() => restoreLearner(JSON.stringify(copy)));
  }
});

test('synthetic misconception demo is deterministic and labeled', () => {
  const a = syntheticMisconceptionDemo({ grade: 4, seed: 'demo' });
  const b = syntheticMisconceptionDemo({ grade: 4, seed: 'demo' });
  assert.deepEqual(a, b);
  assert.equal(a.trace.length, 6);
  assert.ok(a.trace.some((row) => row.misconception));
  assert.ok(a.next.skillId);
});

test('learner updates are immutable', () => {
  const learner = createLearner({ grade: 3, seed: 'immutable' });
  const before = serializeLearner(learner);
  const q = generateQuestion(learner, 'addition');
  const next = updateLearner(learner, q, evaluateAnswer(q, String(q.answer)));
  assert.equal(serializeLearner(learner), before);
  assert.notEqual(next, learner);
});
