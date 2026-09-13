import { createLearner, evaluateAnswer, generateQuestion, selectSkill, updateLearner } from './engine.mjs';

const BASE = Object.freeze({
  addition: 0.48,
  subtraction: 0.55,
  'place-value': 0.62,
  multiplication: 0.30,
  division: 0.34,
  fractions: 0.26,
});

function u32(text) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < text.length; i += 1) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h >>> 0;
}
function unit(seed) {
  let x = seed >>> 0; x ^= x << 13; x ^= x >>> 17; x ^= x << 5; return (x >>> 0) / 4294967296;
}

function simulate(strategy, steps = 90) {
  let learner = createLearner({ grade: 4, seed: `benchmark-${strategy}` });
  const ability = { ...BASE };
  const ids = Object.keys(BASE);
  const exposures = Object.fromEntries(ids.map((id) => [id, 0]));
  for (let step = 0; step < steps; step += 1) {
    const skillId = strategy === 'adaptive' ? selectSkill(learner).skillId : ids[step % ids.length];
    const q = generateQuestion(learner, skillId);
    const p = ability[skillId];
    const correct = unit(u32(`${strategy}:${step}:${skillId}`)) < p;
    const answer = correct ? q.answer : q.answer + 1;
    learner = updateLearner(learner, q, evaluateAnswer(q, String(answer)));
    exposures[skillId] += 1;
    // Explicitly synthetic learning curve: practice improves success probability with diminishing returns.
    ability[skillId] = Math.min(0.94, ability[skillId] + 0.022 * (1 - ability[skillId]));
  }
  const meanAbility = ids.reduce((sum, id) => sum + ability[id], 0) / ids.length;
  const weakest = Math.min(...ids.map((id) => ability[id]));
  return { strategy, steps, meanAbility, weakest, ability, exposures };
}

const result = { label: 'SYNTHETIC_ONLY', adaptive: simulate('adaptive'), roundRobin: simulate('round-robin') };
console.log(JSON.stringify(result, null, 2));
