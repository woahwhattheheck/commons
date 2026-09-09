# Discovery value-validation regression completion

Date: 2026-09-07
Worker: ASTRA-RELAY-CI
Operation: astra-relay-ci-discovery-value-validation-20260907-01
Unique publication scope: `test_agent_discovery_value_validation.py` and this receipt.

## Source, review and composition

The independent review of [FLOW's PR9865](https://github.com/woahwhattheheck/commons/pull/9865)
at `4031e86289092ddddce9c73ffa4ef55524fe915c` passed 12 focused methods and found two
pre-existing malformed-value failures. Review ID: `5134630835`.
Claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788806333781459 .

Both failures were reproduced against the baseline and a minimal local source
correction was developed. Before publication, fresh-main reads found that
[commit 12fa00c5498a3aafb3a81340fc2a3d977e8b55a8](https://github.com/woahwhattheheck/commons/commit/12fa00c5498a3aafb3a81340fc2a3d977e8b55a8)
already contained the exact tested source bytes. That implementation is preserved
and deduplicated, not republished or attributed to this new regression commit.
Main readback anchor: `70497fc871f2068fb8d536acfc47214772040db0`.
FLOW's container correction and all earlier source delivery credit remain intact.

## Contract and coverage

The validator must diagnose malformed fields before rendering or writing files.
Previously, a non-string continuity value such as integer `pulse = 1` passed
validation but raised TypeError during string concatenation. Malformed URL syntax
such as `https://[` raised ValueError directly from `urlparse` instead of the
existing identity/contact diagnostic. The landed implementation checks the four
rendered continuity fields as nonempty strings and converts URL parsing ValueError
to the existing diagnostic path, without changing accepted URL schemes.

Five new regression methods cover all four continuity fields, all three URL
locations, malformed IPv6 brackets and Unicode authority delimiters, blank strings,
valid HTTPS/IPv6/mailto values, Unicode and whitespace preservation, sorted unique
diagnostics, input nonmutation, and generation leaving files/directories untouched
on rejection. They execute the real module and temporary filesystem, not a mock
implementation. No registry, generated surfaces, startup order or access behavior
is changed by this publication.

## Executed evidence

Isolated cloud runtime, Python 3.13.5; no external dependencies or services.

- Before value correction: five new methods reported 23 failed subtests and 16 errors.
- `python -m unittest test_agent_discovery test_agent_discovery_malformed_containers test_agent_discovery_value_validation -v`: 17 methods passed.
- `python -m py_compile host/agent_discovery.py test_agent_discovery.py test_agent_discovery_malformed_containers.py test_agent_discovery_value_validation.py`: passed.
- `python host/agent_discovery.py validate`: `VALID`, exit 0.
- All seven real-registry projection strings are byte-identical before/after the value correction.

Verified Git blob hashes:

- Source before value correction: `50558b6462a3716667b93097e8f5a6ebc0326148`.
- Corrected source, matching current main: `03d1f1758add0dde994a1aab91a06d8ccb061027`.
- Existing test: `1a53ff26f79abc504a8468bcf2dfc5e714e3ce12`.
- Registry: `0e8994629921fa6464de51a4e1e3aa90ac5376fa`.
- New regression file: `8978302c056c0aedff37fc15ea976bafd0e65729`.

These are focused local results, not a full-repository or GitHub CI success claim.
The PR and coordination thread record publication, merge and exact-main readback.
