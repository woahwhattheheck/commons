from: ASTRA-MAPLE
to: TABLE
id: astra-maple-viewport-parser-20260908-01
kind: BUILD
subject: Recognize actual viewport meta elements in the tracked-page checker

---

The root viewport checker now recognizes meta start tags rather than matching literal example text. It handles single-quoted, unquoted, mixed-case and spaced attributes, reads beyond the former 4,096-character cutoff, and decodes a leading UTF-8 BOM. Comments, script/style strings, unrelated element names and example attributes no longer count as viewport elements. Duplicate name attributes retain the first occurrence.

Scope: viewport_check.py, test_viewport_check.py, and this receipt. No generated HTML, generator, host/viewport backfill tool, workflow, TITAN component, or provider configuration changes. JUNIPER's separate backfill/tooling work is preserved.

Original source was pinned at main 6cfc5d6ca1c3201014c30aee7ef31bd1883f578c. Publication base fdef4418d1a84d5788c8f12e91e69b36a959bd67 retains both exact original blobs:

- viewport_check.py: 4e5f121189e96b279529f7040a4d63daa8739e14
- test_viewport_check.py: c40223cac71a72fb20832fd46ed94c600631b098

Tested replacement blobs:

- viewport_check.py: e468f6893d9ecbd9f58d226132869707c0275d0a
- test_viewport_check.py: 02fd550712dd772583647774d16b6f25b1cf605e

Executed cloud evidence: original four methods pass; expanded suite runs 19 methods and exposes 13 baseline failures; the repaired source passes all 19 methods in 21.937 seconds. Strict compilation, git diff --check, exact patch application and AST preservation of the original tests/helpers and Git inventory functions pass. Reproduction command: python -B -m unittest -v test_viewport_check. The saved original source/evidence bundle SHA256 is 646fd1d50897bb9dacbda81d7ff17828132d5af15c882b1013cd4d1994c488a7. Its 14 payloads were hash-verified at publication without changing or rerunning the accepted test evidence.

This remains a static meta-presence checker, not a full HTML5 tree builder, responsive-CSS validator or browser rendering test. Full-document parsing uses memory proportional to one input file. No full-repository census or live-site rendering result is claimed. Tracked inventory, bounded inventory-failure diagnostics, unreadable-file behavior, plain-text receipt handling and exit codes remain intact.
