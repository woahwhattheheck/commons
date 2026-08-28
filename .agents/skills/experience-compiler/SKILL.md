---
name: experience-compiler
description: Compile verified Commons execution outcomes into persistent patterns that can improve reusable skills across agents and models.
---

# Experience compiler

Use this after a task has an attributable outcome and durable evidence.

1. Read `experience/README.md` and `experience/wiki/index.md`.
2. Add one new `experience/raw/<id>.json` packet. Record public task/outcome
   evidence and concise reusable observations, never private chain-of-thought.
3. Run `python3 host/experience_compiler.py compile`.
4. Inspect the compiled pattern and skill-impact delta.
5. If the evidence supports a procedural improvement, change exactly one skill
   and add or update its `PURPOSE.md` to cite the motivating pattern.
6. Run the affected skill's regression test or named canary. Retain an
   improvement that passes; otherwise keep the raw/wiki evidence and discard the
   procedural edit so the failed intervention is not repeated blindly.
7. Run `python3 host/experience_compiler.py check` and
   `python3 -m unittest -v test_experience_compiler.py`.
8. Land the packet, compiled wiki delta, and any proven skill change on current
   main. Read the exact paths back before reporting completion.

The wiki helps maintainers propose changes. Runtime workers receive the active
skill, not the entire wiki, keeping procedural context compact.
