# Reproducible evidence

`RECOVERY_RECEIPT.json` is a compact, source-bound transcription of the observed recovery execution: Python 3.13.5 Linux, 95 normal and 95 actual optimized tests, compile, clean and six-finding exception replay, and synthetic 1,000/5,000/10,000-transaction benchmarks. All twelve executable, test and fixture Git blobs matched local tested bytes after publication to the standalone source tree. The original core, renderer and 94-test suite are unchanged; the package-version test and validation-runner metadata are recovery additions.

Reproduce from the parent acceptance_lab directory:

```sh
python evidence/run_validation.py --out /tmp/cashiering-validation-new
```

The output directory must not exist. The runner records exact argv, expected and actual exit, timing, test counts, raw log hashes, source hashes before/after, error state and platform. It retains ten command logs, both eight-file bundles and its full receipt. Generated reports, redundant screenshots and raw prior-session logs are not copied into Git; the portable implementation, examples, commands and compact observed receipt are. No compressed archive is part of this published evidence set.

The exception fixture deliberately returns compile exit 1 and retains six findings; successful verify means exact reproduction of those exceptions, not financial clearance. Single-process synthetic measurements are not hosted CI, independent review, production capacity, bank acceptance or realized savings. No workflow was added or launched by the validation runner.
