# MistakeMap

MistakeMap is a competition-isolated prototype for the 2026 Nerdy AI Hackathon: an explainable, local-first K–5 arithmetic practice experience that chooses the next challenge from a lightweight learner model instead of a fixed worksheet sequence.

## What the adaptive engine does

- Maintains a small Beta-style mastery posterior for each eligible skill.
- Detects explicit arithmetic misconception patterns such as off-by-one counting, using addition where multiplication is required, and naming a digit instead of its place value.
- Schedules practice from low mastery, uncertainty, spaced-practice due state, and stable misconception signals.
- Shows the learner why a skill was selected.
- Spaces skills farther out after correct streaks and returns missed skills sooner.
- Keeps all state in browser local storage. There is no account, analytics, remote model, API key, or student dataset.

The app supports grades 1–5 across addition, subtraction, place value, multiplication, division, unit fractions, and equivalent fractions. A deterministic **Synthetic learner A** mode demonstrates misconception inference without claiming that synthetic traces are real learners or real educational outcomes.

## Run

Any static server works:

```bash
python -m http.server 8000
# open http://localhost:8000/nerdy-mistakemap/ when serving from the Commons root
```

From this directory alone:

```bash
python -m http.server 8000
# open http://localhost:8000
```

## Verify

No package installation is required.

```bash
npm test
npm run benchmark
npm run check
```

The benchmark is deliberately labeled `SYNTHETIC_ONLY`. It uses an invented learner-success curve to exercise the scheduler; it is **not** an efficacy study, a student outcome, or evidence that adaptive scheduling improves learning in the real world.

## Data / safety boundary

Do not enter personal information. The prototype does not need names, email, student records, video, audio, faces, voices, location, or school data. It performs no emotion/attention/biometric inference and makes no educational placement decision.

## Competition boundary

This directory was created during the challenge entry period. The owner must independently review the official Nerdy contest terms before any submission. Submission itself is intentionally outside this build because the official rules make contractual representations and assign submitted Entry IP to the sponsor.

See [`CONTEST_PACKET.md`](./CONTEST_PACKET.md) for the draft entry description, disclosures, demo script, and owner-only submission checklist.
