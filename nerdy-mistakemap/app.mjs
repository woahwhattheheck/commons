import {
  SKILLS,
  createLearner,
  evaluateAnswer,
  generateQuestion,
  hintFor,
  masteryFor,
  restoreLearner,
  selectSkill,
  serializeLearner,
  snapshotSummary,
  syntheticMisconceptionDemo,
} from './engine.mjs';

const STORAGE_KEY = 'mistakemap-v1';
let learner = loadLearner() || createLearner({ grade: 3, seed: newSeed() });
let currentQuestion = null;
let currentSelection = null;
let lastEvaluation = null;
let awaitingNext = false;

const $ = (id) => document.getElementById(id);
const gradeSelect = $('gradeSelect');
const prompt = $('prompt');
const answerInput = $('answerInput');
const feedback = $('feedback');
const rationale = $('rationale');
const masteryGrid = $('masteryGrid');
const progressText = $('progressText');
const progressFill = $('progressFill');
const checkButton = $('checkButton');
const hintButton = $('hintButton');
const nextButton = $('nextButton');
const hintBox = $('hintBox');
const demoBox = $('demoBox');
const liveStatus = $('liveStatus');

gradeSelect.value = String(learner.grade);

function newSeed() {
  const part = Math.random().toString(36).slice(2, 9);
  return `expedition-${Date.now().toString(36)}-${part}`;
}

function loadLearner() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? restoreLearner(raw) : null;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function saveLearner() {
  localStorage.setItem(STORAGE_KEY, serializeLearner(learner));
}

function nextChallenge() {
  currentSelection = selectSkill(learner);
  currentQuestion = generateQuestion(learner, currentSelection.skillId);
  lastEvaluation = null;
  awaitingNext = false;
  answerInput.value = '';
  answerInput.disabled = false;
  checkButton.disabled = false;
  nextButton.hidden = true;
  hintBox.hidden = true;
  hintBox.textContent = '';
  feedback.className = 'feedback neutral';
  feedback.textContent = 'Solve it your way. MistakeMap learns from the pattern, not your identity.';
  prompt.textContent = currentQuestion.prompt;
  rationale.innerHTML = currentSelection.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join('');
  renderMap();
  answerInput.focus();
}

function submitAnswer() {
  if (awaitingNext) return;
  const evaluation = evaluateAnswer(currentQuestion, answerInput.value);
  lastEvaluation = evaluation;
  if (!evaluation.valid) {
    feedback.className = 'feedback caution';
    feedback.textContent = evaluation.message;
    liveStatus.textContent = evaluation.message;
    return;
  }
  learner = window.__mistakeMapEngine.updateLearner(learner, currentQuestion, evaluation);
  saveLearner();
  awaitingNext = true;
  answerInput.disabled = true;
  checkButton.disabled = true;
  nextButton.hidden = false;
  if (evaluation.correct) {
    feedback.className = 'feedback success';
    feedback.textContent = 'Nice. The model spaced this skill farther out and will look for the next useful edge.';
  } else {
    feedback.className = 'feedback miss';
    const signal = evaluation.misconception ? ` Pattern detected: ${humanize(evaluation.misconception)}.` : '';
    feedback.textContent = `Not yet.${signal} The skill will return sooner.`;
  }
  liveStatus.textContent = feedback.textContent;
  renderMap();
}

function showHint() {
  hintBox.hidden = false;
  hintBox.textContent = hintFor(currentQuestion, lastEvaluation);
}

function renderMap() {
  const summary = snapshotSummary(learner);
  masteryGrid.innerHTML = summary.map((row) => {
    const pct = Math.round(row.mastery * 100);
    const signal = row.misconceptionLabel ? `<span class="signal">Signal: ${escapeHtml(row.misconceptionLabel)}</span>` : '<span class="signal quiet">No stable error signal yet</span>';
    const due = row.due ? '<span class="due">due</span>' : '<span class="later">spaced</span>';
    return `<article class="skill-card ${row.id === currentSelection?.skillId ? 'selected' : ''}">
      <div class="skill-head"><strong>${escapeHtml(row.label)}</strong>${due}</div>
      <div class="meter" aria-label="${escapeHtml(row.label)} mastery ${pct}%"><span style="width:${pct}%"></span></div>
      <div class="skill-meta"><span>${pct}% mastery · ${row.attempts} tries</span>${signal}</div>
    </article>`;
  }).join('');
  const accuracy = learner.totalAttempts ? Math.round((learner.totalCorrect / learner.totalAttempts) * 100) : 0;
  progressText.textContent = `${learner.totalCorrect}/${learner.totalAttempts} correct · ${accuracy}% · step ${learner.step}`;
  const progressPct = Math.min(100, (learner.step / 20) * 100);
  progressFill.style.width = `${progressPct}%`;
}

function resetExpedition({ grade = Number(gradeSelect.value), seed = newSeed() } = {}) {
  learner = createLearner({ grade, seed });
  saveLearner();
  demoBox.hidden = true;
  nextChallenge();
}

function runSyntheticDemo() {
  const demo = syntheticMisconceptionDemo({ grade: Math.max(4, Number(gradeSelect.value)), seed: 'synthetic-learner-a' });
  learner = demo.learner;
  gradeSelect.value = String(learner.grade);
  saveLearner();
  const detected = snapshotSummary(learner).filter((row) => row.misconceptionLabel);
  demoBox.hidden = false;
  demoBox.innerHTML = `<strong>Synthetic learner A loaded.</strong>
    <span>This is generated test behavior, not a child or real learner record.</span>
    <span>Detected: ${detected.map((row) => `${escapeHtml(row.label)} → ${escapeHtml(row.misconceptionLabel)}`).join('; ') || 'no stable patterns'}.</span>
    <span>Adaptive next pick: ${escapeHtml(demo.next.label)}.</span>`;
  nextChallenge();
}

function exportSnapshot() {
  const payload = serializeLearner(learner);
  const blob = new Blob([payload], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'mistakemap-local-snapshot.json';
  anchor.click();
  URL.revokeObjectURL(url);
}

function humanize(text) {
  return text.replaceAll('-', ' ');
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

checkButton.addEventListener('click', submitAnswer);
hintButton.addEventListener('click', showHint);
nextButton.addEventListener('click', nextChallenge);
answerInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') awaitingNext ? nextChallenge() : submitAnswer();
});
$('newButton').addEventListener('click', () => resetExpedition());
$('demoButton').addEventListener('click', runSyntheticDemo);
$('exportButton').addEventListener('click', exportSnapshot);
gradeSelect.addEventListener('change', () => resetExpedition({ grade: Number(gradeSelect.value) }));

import * as engineModule from './engine.mjs';
window.__mistakeMapEngine = engineModule;

nextChallenge();
