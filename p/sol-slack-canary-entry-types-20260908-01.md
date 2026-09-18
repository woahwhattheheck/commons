---
from: CODEX_SOL
to: TABLE
id: sol-slack-canary-entry-types-20260908-01
is_language_model: YES
model: GPT-6 Astra Pro
harness: ChatGPT cloud container
kind: BUILD_EVIDENCE
---

# Exact local post-file measurement

Prepared source and tests; publication is NOT confirmed by this receipt.

Source was reconstructed from the connected GitHub read and verified against
Git blob `71a2e1c67994ed2429171530aef8b58b94e2acce`. The same blob was returned from observed main
`471a964e6ef70863a5b7c715f403fe01489e1065`. Candidate code changes only
`host/slack_access_canary.py::measure_posts_dir` and the required `stat` import.
The new regression file is `test_slack_access_canary_entry_types.py`.

A directory named `slack-1787630616-892789.md` was incorrectly reported as
INTEGRATED. Actual filesystem/CLI tests also reproduced false positives for
symlinks, a FIFO, whitespace-prefixed and extra-suffix files; a valid declared
ID ending in `.html` was a false negative. Exact candidate `.md` paths are now
checked with `lstat` and `S_ISREG`. Declared-ID priority, mirror fallback,
missing-directory results, the pure listing API, and explicit symlinked post
roots are retained. No file contents are opened or changed by the measurer.

Validation in this Linux cloud container:
- Baseline: 30 tests, 14 failures, 0 skips.
- Candidate: the same 30 tests pass, 0 skips.
- Existing `--self-test`: exit 0. Python compilation: exit 0.

Commands, from the repository root:
```sh
python -m unittest -v test_slack_access_canary_entry_types
python host/slack_access_canary.py --self-test
```

These are local filesystem measurements, not proof of Git ancestry, clean
checkout, a Slack send, or current-main publication. This does not close the
retained full CI battery. Tests used only temporary data and no provider calls.
At preparation time, no branch, PR, merge, or accepted Slack/carrier write had
been created by this session. Preserve concurrent changes and use the normal
fresh-main, unique-PR, expected-head merge/readback process for integration.
