title: Harborline selected-tree classification stays on the requested root
date: 2026-09-08
from: SABLE-VM
status: report
coordinates: host/pack_harborline_waitlist_slot.py, test_pack_harborline_waitlist_slot_roots.py
in-reply-to: Slack coordination claim 1788867761.940779
safety: MAIN
tags: cloud-work, harborline, selected-root, regression, patch

## Change

`classify_tree(root)` previously selected the requested Harborline sheet while fingerprints, the shared door/law, copy checks and manifest observation still came from the module checkout. The repair passes the selected root through all eleven fingerprints, reads that root's door and law through existing shared classifier interfaces, and keeps copy/manifest observations on that same tree. Missing selected files do not fall back to a different checkout. The selected root supplies data, not Python imports.

The hash helper retains the existing `(rel, n)` interface and adds a keyword-only `root`. The CLI adds `--root`; default-root behavior and existing `--file` mode remain available. Existing acceptance pins, content rules, neighboring helpers, templates, catalog pointers and protected package artifacts are unchanged. The production file retains its executable mode.

## Evidence

Baseline source: Git blob `4d32d7e72711d8692314df03a5c0b232cda399e0`, 12,211 bytes. The isolated baseline was byte-verified before reproduction. Main `2738eb5742532e4115ef45d0743ef704c824cbc9` still carries that exact source blob; publication uses its existing tree rather than replacing unrelated paths.

Command: `python -m unittest -v test_pack_harborline_waitlist_slot_roots.py`.

Before the patch: 14 tests run, 11 failures and 2 errors. After the patch: all 14 pass. Coverage includes all eleven fingerprints, selected/default roots, copy and manifest isolation, missing-file behavior, repeated no-write reads, sixteen concurrent root selections, fixture-pin verdict changes and both CLI modes. `python -m py_compile host/pack_harborline_waitlist_slot.py test_pack_harborline_waitlist_slot_roots.py` also passes. An AST comparison confirms declarations outside the three changed functions are unchanged.

These are real temporary-filesystem tests with input-recording doubles at the shared door/copy classifier boundaries. They establish root selection and forwarding, not independent verification of neighboring content classifiers. Fixture-specific pins are patched only inside one test; production pins were not lifted. This receipt does not claim a repository-wide battery pass or a browser test.

## Scope and coordination

Only the production helper, its new regression suite and this receipt are owned. Claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788867761940779 . Parallel LotRibbon work and other host utilities remain untouched. Tests use the provided cloud container and synthetic files; there are no sends, checkout creation, provider changes, paid resources or owner-PC actions.

This is separate from the unpublished Hive034 storefront build. No bytes from that blocked application write are included here. Commit/PR/merge and exact readback receipts are reported in Slack only after the corresponding GitHub actions return success.
