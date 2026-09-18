TERMINAL RECEIPT — open-door-guard repair

failed operation: open-door-guard run 33595322662 job reject-added-locks step “reject newly added Action Pad or Commons admission locks” on 56ebe743 / PR 7648 https://github.com/woahwhattheheck/commons/actions/runs/33595322662

measured cause: tos-enforcement collocated ToS with gate on leftover cards that say they are not a Commons gate (ground/TJLABS_PACK_TERMS.md:5, host/tjlabs_pack_terms.py:2, test_tjlabs_pack_terms.py:2). Not Commons admission.

repair: PR 7671 added not a commons gate / never a commons gate to _directive_or_prohibition. Affirmative TOS admission still fails. tjlabs classifier unchanged. https://github.com/woahwhattheheck/commons/pull/7671

tests: python3 test_open_door_guard.py 20 asserts PASS; python3 -m unittest -q test_tjlabs_pack_terms 10/10 PASS; original failing snippets scan clean

PR/commit: 7671 / 928fefc3be183b44e59f49a1229c5c16a19dc37a
final main SHA at merge: 6baf6a2277d47efb56e6c5642d042ebd441564e5
landed blob: open_door_guard.py b254781fafc7e62ec704f83549491b9fe68056ab

dedupe: woahwhattheheck/commons:open-door-guard:56ebe743fba587e32afaa4a1a0a2f8e0e56bd2ab:reject newly added Action Pad or Commons admission locks
