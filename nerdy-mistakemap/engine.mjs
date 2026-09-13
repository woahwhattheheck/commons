export const ENGINE_VERSION = 1;

export const SKILLS = Object.freeze([
  { id: 'addition', label: 'Addition', grade: 1, icon: '+' },
  { id: 'subtraction', label: 'Subtraction', grade: 1, icon: '−' },
  { id: 'place-value', label: 'Place value', grade: 2, icon: '10×' },
  { id: 'multiplication', label: 'Multiplication', grade: 3, icon: '×' },
  { id: 'division', label: 'Division', grade: 3, icon: '÷' },
  { id: 'fractions', label: 'Unit fractions', grade: 4, icon: '⅓' },
  { id: 'equivalence', label: 'Equivalent fractions', grade: 5, icon: '=' },
]);

const SKILL_MAP = new Map(SKILLS.map((skill) => [skill.id, skill]));
const MISCONCEPTION_LABELS = Object.freeze({
  'counting-off-by-one': 'counting off by one',
  'operation-switch': 'switching the operation',
  'ones-only': 'ignoring a carry / higher place',
  'digit-vs-value': 'naming the digit instead of its place value',
  'addition-for-multiplication': 'adding once instead of multiplying',
  'skip-count-slip': 'losing one group while skip-counting',
  'multiply-instead-of-share': 'multiplying instead of sharing',
  'denominator-as-answer': 'using the denominator as the amount',
  'denominator-swap': 'scaling the denominator instead of the numerator',
});

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function clamp(value, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

export function hashString(text) {
  let hash = 2166136261 >>> 0;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

export function seededUnit(seed) {
  let x = seed >>> 0;
  x ^= x << 13;
  x ^= x >>> 17;
  x ^= x << 5;
  return (x >>> 0) / 4294967296;
}

function seededInt(seed, min, max) {
  assert(Number.isInteger(min) && Number.isInteger(max) && max >= min, 'invalid integer range');
  return min + Math.floor(seededUnit(seed) * (max - min + 1));
}

function questionSeed(sessionSeed, skillId, questionIndex) {
  return hashString(`${sessionSeed}:${skillId}:${questionIndex}`);
}

function blankSkillState() {
  return {
    alpha: 2,
    beta: 2,
    attempts: 0,
    correct: 0,
    streak: 0,
    nextDue: 0,
    misconceptions: {},
    lastResult: null,
  };
}

export function createLearner({ grade = 3, seed = 'mistakemap-demo' } = {}) {
  assert(Number.isInteger(grade) && grade >= 1 && grade <= 5, 'grade must be 1–5');
  assert(typeof seed === 'string' && seed.length >= 1 && seed.length <= 80, 'seed must be a short non-empty string');
  const skills = {};
  for (const skill of SKILLS) skills[skill.id] = blankSkillState();
  return {
    version: ENGINE_VERSION,
    grade,
    seed,
    step: 0,
    totalCorrect: 0,
    totalAttempts: 0,
    skills,
  };
}

export function masteryFor(skillState) {
  return skillState.alpha / (skillState.alpha + skillState.beta);
}

export function uncertaintyFor(skillState) {
  const n = skillState.alpha + skillState.beta;
  return clamp(4 / n);
}

function topMisconception(skillState) {
  const entries = Object.entries(skillState.misconceptions || {});
  if (!entries.length) return null;
  entries.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return entries[0][1] >= 0.6 ? entries[0] : null;
}

export function eligibleSkills(grade) {
  return SKILLS.filter((skill) => skill.grade <= grade);
}

export function scoreSkill(learner, skillId) {
  const skill = SKILL_MAP.get(skillId);
  assert(skill, `unknown skill: ${skillId}`);
  assert(skill.grade <= learner.grade, `skill ${skillId} is above learner grade band`);
  const state = learner.skills[skillId];
  const mastery = masteryFor(state);
  const uncertainty = uncertaintyFor(state);
  const due = learner.step >= state.nextDue ? 1 : 0;
  const overdue = Math.max(0, learner.step - state.nextDue);
  const misconception = topMisconception(state);
  const misconceptionStrength = misconception ? clamp(misconception[1] / 3) : 0;
  const unseen = state.attempts === 0 ? 1 : 0;
  const futurePenalty = learner.step < state.nextDue ? Math.min(0.28, (state.nextDue - learner.step) * 0.035) : 0;
  const score =
    (1 - mastery) * 0.42 +
    uncertainty * 0.18 +
    due * 0.18 +
    Math.min(0.12, overdue * 0.02) +
    misconceptionStrength * 0.18 +
    unseen * 0.08 -
    futurePenalty;
  return {
    score,
    mastery,
    uncertainty,
    due: Boolean(due),
    overdue,
    misconception: misconception?.[0] ?? null,
    misconceptionStrength,
  };
}

export function selectSkill(learner) {
  validateLearner(learner);
  const ranked = eligibleSkills(learner.grade)
    .map((skill) => ({ skill, ...scoreSkill(learner, skill.id) }))
    .sort((a, b) => b.score - a.score || a.skill.id.localeCompare(b.skill.id));
  const chosen = ranked[0];
  const reasons = [];
  reasons.push(`${Math.round(chosen.mastery * 100)}% estimated mastery`);
  if (chosen.due) reasons.push('practice is due now');
  if (chosen.uncertainty >= 0.5) reasons.push('the model still has limited evidence');
  if (chosen.misconception) reasons.push(`recent signal: ${MISCONCEPTION_LABELS[chosen.misconception] || chosen.misconception}`);
  if (learner.skills[chosen.skill.id].attempts === 0) reasons.push('this skill has not been sampled yet');
  return {
    skillId: chosen.skill.id,
    label: chosen.skill.label,
    score: chosen.score,
    reasons,
    ranked: ranked.map((row) => ({
      skillId: row.skill.id,
      score: row.score,
      mastery: row.mastery,
      due: row.due,
    })),
  };
}

function additionQuestion(rngSeed, grade) {
  const max = grade <= 1 ? 10 : grade === 2 ? 30 : 100;
  const a = seededInt(rngSeed, 1, max - 1);
  const b = seededInt(rngSeed ^ 0xa53a9d1b, 1, Math.max(1, max - a));
  return { prompt: `${a} + ${b} = ?`, answer: a + b, operands: [a, b], kind: 'addition' };
}

function subtractionQuestion(rngSeed, grade) {
  const max = grade <= 1 ? 10 : grade === 2 ? 40 : 100;
  const a = seededInt(rngSeed, 2, max);
  const b = seededInt(rngSeed ^ 0x9e3779b9, 1, a);
  return { prompt: `${a} − ${b} = ?`, answer: a - b, operands: [a, b], kind: 'subtraction' };
}

function placeValueQuestion(rngSeed) {
  const hundreds = seededInt(rngSeed, 1, 9);
  const tens = seededInt(rngSeed ^ 0x6d2b79f5, 1, 9);
  const ones = seededInt(rngSeed ^ 0x85ebca6b, 0, 9);
  const number = hundreds * 100 + tens * 10 + ones;
  const placePick = seededInt(rngSeed ^ 0xc2b2ae35, 0, 1);
  const digit = placePick === 0 ? tens : hundreds;
  const value = placePick === 0 ? tens * 10 : hundreds * 100;
  return {
    prompt: `In ${number}, what is the value of the digit ${digit}?`,
    answer: value,
    operands: [number, digit, placePick === 0 ? 10 : 100],
    kind: 'place-value',
  };
}

function multiplicationQuestion(rngSeed, grade) {
  const max = grade <= 3 ? 9 : 12;
  const a = seededInt(rngSeed, 2, max);
  const b = seededInt(rngSeed ^ 0x27d4eb2f, 2, max);
  return { prompt: `${a} × ${b} = ?`, answer: a * b, operands: [a, b], kind: 'multiplication' };
}

function divisionQuestion(rngSeed, grade) {
  const max = grade <= 3 ? 9 : 12;
  const divisor = seededInt(rngSeed, 2, max);
  const quotient = seededInt(rngSeed ^ 0x165667b1, 2, max);
  const dividend = divisor * quotient;
  return { prompt: `${dividend} ÷ ${divisor} = ?`, answer: quotient, operands: [dividend, divisor, quotient], kind: 'division' };
}

function fractionQuestion(rngSeed) {
  const denominator = seededInt(rngSeed, 2, 8);
  const units = seededInt(rngSeed ^ 0xd3a2646c, 2, 8);
  const whole = denominator * units;
  return {
    prompt: `What is 1/${denominator} of ${whole}?`,
    answer: units,
    operands: [denominator, whole],
    kind: 'fractions',
  };
}

function equivalenceQuestion(rngSeed) {
  const denominator = seededInt(rngSeed, 2, 8);
  const numerator = seededInt(rngSeed ^ 0xfd7046c5, 1, denominator - 1);
  const scale = seededInt(rngSeed ^ 0xb55a4f09, 2, 5);
  return {
    prompt: `${numerator}/${denominator} = ?/${denominator * scale}`,
    answer: numerator * scale,
    operands: [numerator, denominator, scale],
    kind: 'equivalence',
  };
}

export function generateQuestion(learner, skillId, questionIndex = null) {
  validateLearner(learner);
  const skill = SKILL_MAP.get(skillId);
  assert(skill && skill.grade <= learner.grade, 'invalid skill for learner grade');
  const index = questionIndex ?? learner.skills[skillId].attempts;
  assert(Number.isInteger(index) && index >= 0, 'question index must be a non-negative integer');
  const seed = questionSeed(learner.seed, skillId, index);
  let base;
  switch (skillId) {
    case 'addition': base = additionQuestion(seed, learner.grade); break;
    case 'subtraction': base = subtractionQuestion(seed, learner.grade); break;
    case 'place-value': base = placeValueQuestion(seed); break;
    case 'multiplication': base = multiplicationQuestion(seed, learner.grade); break;
    case 'division': base = divisionQuestion(seed, learner.grade); break;
    case 'fractions': base = fractionQuestion(seed); break;
    case 'equivalence': base = equivalenceQuestion(seed); break;
    default: throw new Error(`unknown skill: ${skillId}`);
  }
  return {
    id: `${skillId}:${index}:${seed.toString(16).padStart(8, '0')}`,
    skillId,
    skillLabel: skill.label,
    index,
    ...base,
  };
}

function normalizeNumericAnswer(raw) {
  if (typeof raw === 'number') {
    if (!Number.isFinite(raw)) return null;
    return raw;
  }
  if (typeof raw !== 'string') return null;
  const trimmed = raw.trim();
  if (!/^-?\d+(?:\.\d+)?$/.test(trimmed)) return null;
  const number = Number(trimmed);
  return Number.isFinite(number) ? number : null;
}

export function classifyMisconception(question, numericAnswer) {
  if (numericAnswer === null || numericAnswer === question.answer) return null;
  const [a, b, c] = question.operands;
  if (Math.abs(numericAnswer - question.answer) === 1) return 'counting-off-by-one';
  switch (question.kind) {
    case 'addition':
      if (numericAnswer === a - b || numericAnswer === b - a || numericAnswer === a * b) return 'operation-switch';
      if (a + b >= 10 && numericAnswer === (a % 10) + (b % 10)) return 'ones-only';
      break;
    case 'subtraction':
      if (numericAnswer === a + b) return 'operation-switch';
      break;
    case 'place-value':
      if (numericAnswer === b) return 'digit-vs-value';
      break;
    case 'multiplication':
      if (numericAnswer === a + b) return 'addition-for-multiplication';
      if (numericAnswer === question.answer - a || numericAnswer === question.answer - b) return 'skip-count-slip';
      break;
    case 'division':
      if (numericAnswer === a * b || numericAnswer === a + b) return 'operation-switch';
      break;
    case 'fractions':
      if (numericAnswer === a) return 'denominator-as-answer';
      if (numericAnswer === a * b) return 'multiply-instead-of-share';
      break;
    case 'equivalence':
      if (numericAnswer === b * c) return 'denominator-swap';
      break;
    default:
      break;
  }
  return null;
}

export function evaluateAnswer(question, rawAnswer) {
  const numericAnswer = normalizeNumericAnswer(rawAnswer);
  if (numericAnswer === null) {
    return { valid: false, correct: false, numericAnswer: null, misconception: null, message: 'Enter a number so the model can learn from the attempt.' };
  }
  const correct = numericAnswer === question.answer;
  const misconception = classifyMisconception(question, numericAnswer);
  return {
    valid: true,
    correct,
    numericAnswer,
    misconception,
    message: correct ? 'Correct.' : 'Not yet.',
  };
}

function decayMisconceptions(misconceptions) {
  const next = {};
  for (const [key, value] of Object.entries(misconceptions || {})) {
    const decayed = value * 0.82;
    if (decayed >= 0.08) next[key] = decayed;
  }
  return next;
}

export function updateLearner(learner, question, evaluation) {
  validateLearner(learner);
  assert(question && question.skillId && learner.skills[question.skillId], 'question skill is not in learner state');
  assert(evaluation && evaluation.valid === true, 'only valid attempts update the learner model');
  const next = structuredCloneSafe(learner);
  const state = next.skills[question.skillId];
  state.misconceptions = decayMisconceptions(state.misconceptions);
  state.attempts += 1;
  next.totalAttempts += 1;
  if (evaluation.correct) {
    state.alpha += 1.35;
    state.correct += 1;
    state.streak += 1;
    next.totalCorrect += 1;
    const spacing = Math.min(12, 2 ** Math.min(state.streak, 3));
    state.nextDue = next.step + spacing;
    state.lastResult = 'correct';
  } else {
    state.beta += 1.15;
    state.streak = 0;
    state.nextDue = next.step + 1;
    state.lastResult = 'incorrect';
    if (evaluation.misconception) {
      state.misconceptions[evaluation.misconception] = (state.misconceptions[evaluation.misconception] || 0) + 1;
    }
  }
  next.step += 1;
  validateLearner(next);
  return next;
}

export function hintFor(question, evaluation = null) {
  const misconception = evaluation?.misconception;
  if (misconception === 'counting-off-by-one') return 'You are one step away. Recount once, touching each group exactly one time.';
  if (misconception === 'operation-switch') return `The symbol matters here. This challenge is ${question.skillLabel.toLowerCase()}, so use that operation before calculating.`;
  if (misconception === 'ones-only') return 'You handled the ones. Now ask whether the ones made a new ten that must be carried into the next place.';
  if (misconception === 'digit-vs-value') return 'A digit tells which symbol you see; place value tells how much that digit is worth. Check whether it sits in the tens or hundreds place.';
  if (misconception === 'addition-for-multiplication') return 'Multiplication is equal groups. Instead of adding the two factors once, make one factor that many times.';
  if (misconception === 'skip-count-slip') return 'Build equal groups and count every group once. Mark each jump so you do not stop one group early.';
  if (misconception === 'multiply-instead-of-share') return '“One part of” means split the whole into equal groups. How large is one group?';
  if (misconception === 'denominator-as-answer') return 'The denominator tells how many equal groups to make; it is not automatically the size of one group.';
  if (misconception === 'denominator-swap') return 'Equivalent fractions scale top and bottom by the same factor. Find the factor used on the denominator, then use it on the numerator.';
  switch (question.kind) {
    case 'addition': return 'Try making a ten first, then add what remains.';
    case 'subtraction': return 'Count up from the smaller number or break apart the amount being taken away.';
    case 'place-value': return 'Read the number from right to left: ones, tens, hundreds.';
    case 'multiplication': return 'Draw equal groups or skip-count by one factor.';
    case 'division': return 'Ask which multiplication fact gives the dividend.';
    case 'fractions': return 'Split the whole into the number of equal groups named by the denominator.';
    case 'equivalence': return 'Whatever factor changes the denominator must also change the numerator.';
    default: return 'Represent the quantities, then choose the operation the prompt asks for.';
  }
}

export function snapshotSummary(learner) {
  validateLearner(learner);
  return eligibleSkills(learner.grade).map((skill) => {
    const state = learner.skills[skill.id];
    const top = topMisconception(state);
    return {
      id: skill.id,
      label: skill.label,
      mastery: masteryFor(state),
      attempts: state.attempts,
      due: learner.step >= state.nextDue,
      nextDue: state.nextDue,
      misconception: top?.[0] ?? null,
      misconceptionLabel: top ? (MISCONCEPTION_LABELS[top[0]] || top[0]) : null,
    };
  });
}

export function serializeLearner(learner) {
  validateLearner(learner);
  return JSON.stringify(learner);
}

export function restoreLearner(serialized) {
  assert(typeof serialized === 'string' && serialized.length < 100_000, 'invalid learner snapshot');
  let parsed;
  try {
    parsed = JSON.parse(serialized);
  } catch {
    throw new Error('learner snapshot is not valid JSON');
  }
  validateLearner(parsed);
  return parsed;
}

export function validateLearner(learner) {
  assert(learner && typeof learner === 'object' && !Array.isArray(learner), 'learner must be an object');
  assert(learner.version === ENGINE_VERSION, 'unsupported learner version');
  assert(Number.isInteger(learner.grade) && learner.grade >= 1 && learner.grade <= 5, 'invalid learner grade');
  assert(typeof learner.seed === 'string' && learner.seed.length >= 1 && learner.seed.length <= 80, 'invalid learner seed');
  assert(Number.isInteger(learner.step) && learner.step >= 0, 'invalid learner step');
  assert(Number.isInteger(learner.totalCorrect) && learner.totalCorrect >= 0, 'invalid totalCorrect');
  assert(Number.isInteger(learner.totalAttempts) && learner.totalAttempts >= learner.totalCorrect, 'invalid totalAttempts');
  assert(learner.skills && typeof learner.skills === 'object', 'missing skill state');
  for (const skill of SKILLS) {
    const state = learner.skills[skill.id];
    assert(state && typeof state === 'object', `missing state for ${skill.id}`);
    for (const key of ['alpha', 'beta']) assert(Number.isFinite(state[key]) && state[key] > 0, `invalid ${key} for ${skill.id}`);
    for (const key of ['attempts', 'correct', 'streak', 'nextDue']) assert(Number.isInteger(state[key]) && state[key] >= 0, `invalid ${key} for ${skill.id}`);
    assert(state.correct <= state.attempts, `correct exceeds attempts for ${skill.id}`);
    assert(state.misconceptions && typeof state.misconceptions === 'object' && !Array.isArray(state.misconceptions), `invalid misconceptions for ${skill.id}`);
    for (const [key, value] of Object.entries(state.misconceptions)) {
      assert(Object.hasOwn(MISCONCEPTION_LABELS, key), `unknown misconception: ${key}`);
      assert(Number.isFinite(value) && value >= 0 && value <= 1000, `invalid misconception score: ${key}`);
    }
    assert(state.lastResult === null || state.lastResult === 'correct' || state.lastResult === 'incorrect', `invalid lastResult for ${skill.id}`);
  }
  return true;
}

function structuredCloneSafe(value) {
  if (typeof structuredClone === 'function') return structuredClone(value);
  return JSON.parse(JSON.stringify(value));
}

export function syntheticMisconceptionDemo({ grade = 4, seed = 'synthetic-demo' } = {}) {
  let learner = createLearner({ grade, seed });
  const script = [
    ['addition', (q) => q.answer + 1],
    ['addition', (q) => q.answer + 1],
    ['multiplication', (q) => q.operands[0] + q.operands[1]],
    ['multiplication', (q) => q.operands[0] + q.operands[1]],
    ['fractions', (q) => q.operands[0]],
    ['subtraction', (q) => q.answer],
  ];
  const trace = [];
  for (const [skillId, answerer] of script) {
    const q = generateQuestion(learner, skillId);
    const answer = answerer(q);
    const evaluation = evaluateAnswer(q, String(answer));
    learner = updateLearner(learner, q, evaluation);
    trace.push({ skillId, prompt: q.prompt, answer, correct: evaluation.correct, misconception: evaluation.misconception });
  }
  return { learner, trace, next: selectSkill(learner) };
}
