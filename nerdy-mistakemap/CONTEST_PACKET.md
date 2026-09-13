# MistakeMap — Nerdy AI Hackathon owner packet

**Status:** build/demo package only — **NOT SUBMITTED**.

Official challenge: <https://hackathon.nerdy.com/>  
Official rules: <https://hackathon.nerdy.com/terms>

## Draft “What did you build?”

MistakeMap is an explainable adaptive K–5 math practice game built around a simple idea: the next useful challenge is often the one that tests a learner's current misconception, not the next item in a fixed worksheet.

The browser-local engine keeps a small mastery model for seven arithmetic skills, classifies a bounded set of error patterns, and combines mastery, uncertainty, spaced-practice due state, and misconception strength to choose the next skill. The UI shows the learner *why* that skill was chosen. Correct streaks space a skill farther out; misses bring it back sooner. Strategy hints respond to the observed arithmetic pattern without using personal data or a remote model.

I built the prototype as a zero-dependency static app so a judge can open it without an account, API key, model credential, or backend. The included synthetic-learner mode exists only to demonstrate model behavior; it is explicitly labeled synthetic and uses no real student data.

Next, I would validate the misconception taxonomy with educators, test whether the explanation layer helps learners understand the adaptation, add curriculum-aligned content authored/reviewed by domain experts, and run a consented study before making any real learning-effect claim.

## Prompt

Suggested form selection: **Prompt 01 — K–5 Math Game**.

## Generative-AI assistance disclosure draft

> Generative AI assistance was used extensively during the challenge period for product architecture discussion, code drafting, adversarial test design, interface copy, and review. OpenAI ChatGPT (GPT-5.6 Sol) was used as a coding/reasoning assistant. The entrant directed the product goals and decisions and must personally review, understand, and be able to explain the submitted work before using this disclosure.

Owner: verify this wording accurately describes your role before submission.

## Third-party / open-source material inventory

Runtime dependencies: **none**.  
Bundled third-party code: **none identified**.  
Third-party APIs/models/datasets/fonts/images/audio: **none**.  
Platform primitives used: standard browser HTML/CSS/JavaScript APIs and `localStorage`.

Owner must re-check the final submitted tree and demo video before making the contest representation required by the rules.

## 2–3 minute demo script

### 0:00–0:25 — Problem
“Most practice apps know whether an answer is wrong. MistakeMap tries to keep track of *how* it is wrong, then makes that reasoning visible.”

Show the landing page and point out **0 accounts / 0 network calls / 7 skill models / visible reason per pick**.

### 0:25–1:05 — Adaptive loop
Start Grade 3. Read the **Why this challenge?** reasons. Answer one prompt correctly, click Next, and show how mastery/due state changes. Then intentionally answer a multiplication problem with the two factors added instead of multiplied. Show the detected pattern and strategy hint.

### 1:05–1:40 — Synthetic proof path
Click **Load synthetic learner A**. Say explicitly: “This is generated test behavior, not a real child or learner record.” Show the stable misconception labels and the adaptive next pick. Point out that mastery is described as a lightweight model estimate, not a grade.

### 1:40–2:15 — Production thinking
Show local export, responsive view, and the no-backend boundary. Explain that invalid text does not mutate the learner model and that the engine has deterministic tests for question generation, scheduler grade gates, misconception classification, immutable updates, snapshot validation, and synthetic-demo reproducibility.

### 2:15–2:45 — Next steps
“Before treating this as a learning intervention, I’d validate the misconception taxonomy with educators, expand curriculum coverage, and run a consented evaluation. The prototype is built to make that evolution inspectable rather than hiding adaptation behind an opaque score.”

## Owner-only submission checklist

Do **not** delegate these attestations to the build lane:

- [ ] Confirm you are individually eligible under the official rules.
- [ ] Read the current official rules in full.
- [ ] Decide whether to accept the Entry-IP assignment and other contractual terms.
- [ ] Review every file in the submitted Entry and confirm ownership / third-party disclosures.
- [ ] Confirm the generative-AI disclosure accurately describes your direction and understanding.
- [ ] Record a <=3 minute demo video with no third-party personal information visible.
- [ ] Verify the live demo and/or code link remain accessible through judging.
- [ ] Enter your own name/email and personally agree to the contest terms.
- [ ] Submit no later than the official deadline; retain the submission receipt.

Build automation must not mark any of these boxes complete.
