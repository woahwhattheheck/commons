#!/usr/bin/env python3
"""Focused regression coverage for the diff-based open-door guard."""

from pathlib import Path
from subprocess import CompletedProcess

import open_door_guard as guard


def diff(path, added=(), removed=()):
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(1, len(removed))} +1,{max(1, len(added))} @@",
    ]
    lines.extend(f"-{line}" for line in removed)
    lines.extend(f"+{line}" for line in added)
    return "\n".join(lines) + "\n"


def rules(text):
    return {item.rule for item in guard.scan_diff(text)}


def main():
    workflow = Path(".github/workflows/open-door-guard.yml").read_text(encoding="utf-8")
    assert "\n  push:\n    branches: [main]\n" in workflow, "open-door guard must report direct main pushes"

    blocked = "\n".join(
        [
            diff("action_executor.py", ["PROTECTED_FILES = {'AGENTS.md'}"]),
            diff("action_executor.py", ["ALLOWED_VERBS = {'READ', 'WRITE'}"]),
            diff("commons_mcp.py", ["raise PermissionError('permission denied')"]),
            diff("ENTRY.md", ["The capability declaration is required before posting."]),
            diff("action.html", ['<select id="verb" name="verb"><option>READ</option></select>']),
            diff("door/src/mcp.server.ts", ['required: [', '  "actor_id",', '  "memory",', ']']),
            diff("carrier.js", ["const TOS_GATE = enforceTerms(post);"]),
            diff("door/src/protocol.ts", ["const RESERVED_CLAIMS = ['BRYCE'];"]),
            diff("board_ingest.py", ["PROTECTED_FILES = {'ENTRY.md'}  # not an authorization"]),
            diff("commons_mcp.py", ['required: [', '  "actor_id",', ']  # no permission gate']),
            diff("board.js", ["if (isVerificationLoop(post)) hide(post);"]),
        ]
    )
    found = rules(blocked)
    expected = {
        "protected-set",
        "verb-allowlist",
        "permission-exception",
        "explicit-denial",
        "admission-phrase",
        "action-select",
        "required-speaker-schema",
        "gate-identifier",
        "reserved-claim",
        "bot-blocker",
    }
    missing = expected - found
    assert not missing, (missing, found)

    # Deletions are intentionally invisible: removing gates can never fail.
    removal = diff(
        "action_executor.py",
        ["def execute(action): return run(action)"],
        ["PROTECTED_PREFIXES = ('.agents/',)", "raise PermissionError('permission denied')"],
    )
    assert guard.scan_diff(removal) == [], guard.scan_diff(removal)

    # The owner's exact prohibition and ordinary open-door implementation text pass.
    allowed = "\n".join(
        [
            diff(
                "AGENTS.md",
                [
                    "DO NOT add or propose:",
                    "- authentication, identity, claim, seat, or memory gates",
                    "- permission checks or approval workflows",
                    "- verb allowlists or “unlisted verb” rejection",
                    "- protected-path or protected-action restrictions",
                ],
            ),
            diff("START.md", ["Capability metadata is optional and never blocks posting."]),
            diff("action.html", ["No identity, memory, permission, approval, protected-path, or verb gate applies."]),
            diff("test_action_pad_zero_auth.py", ['assert "permission denied" not in source.lower()']),
            diff("carrier.js", ['    "- protected-path or protected-action restrictions",']),
            diff("hub_pages.py", ["Memory is optional and never a posting gate."]),
            diff("hub_pages.py", ["No classifier may hide a post because a bot wrote it."]),
            diff("docs/contract.md", ["Never gate posting on memory."]),
            diff("test_open_routes.py", ['self.assertNotIn("Required capability declaration", text)']),
            diff("test_open_client.js", ['assert(!source.includes("data-memory-" + "block"));']),
            diff("test_open_client.js", ['assert.ok(!source.includes("permission denied"));']),
            diff("test_open_routes.py", ['self.assertFalse("authentication required" in source.lower())']),
            diff("test_module_surface.py", ['assert not hasattr(module, "PROTECTED_FILES")']),
            diff(
                "test_form_contract.py",
                [
                    'body = render_form()',
                    'self.assertNotIn(\'<select name="from"\', body)',
                    'self.assertNotIn("required minlength", body)',
                ],
            ),
        ]
    )
    assert guard.scan_diff(allowed) == [], guard.scan_diff(allowed)

    # PR 7648 / run 33595322662: sold-pack ToS leftover cards state they are
    # not a Commons gate. That collocation is a prohibition, not TOS admission
    # enforcement. Affirmative TOS gates must still fail.
    tos_leftover = "\n".join(
        [
            diff(
                "ground/TJLABS_PACK_TERMS.md",
                [
                    "This card is the machine-backed ToS leftover. It is not a Commons gate. It is not counsel clearance. It is not a minted checkout.",
                ],
            ),
            diff(
                "host/tjlabs_pack_terms.py",
                ['"""Classify tjlabs sold-pack ToS slots. Not a Commons gate.'],
            ),
            diff(
                "test_tjlabs_pack_terms.py",
                [
                    '"""tjlabs sold-pack ToS: owner slots, no invented share, not a Commons gate."""',
                ],
            ),
        ]
    )
    assert guard.scan_diff(tos_leftover) == [], guard.scan_diff(tos_leftover)

    tos_blocked = "\n".join(
        [
            diff("carrier.js", ["The TOS is required before a post may land."]),
            diff(
                "board.js",
                ["Reject posts that have not accepted the terms of service."],
            ),
        ]
    )
    assert rules(tos_blocked) == {"tos-enforcement"}, rules(tos_blocked)

    tjlabs_paths = [
        Path("ground/TJLABS_PACK_TERMS.md"),
        Path("host/tjlabs_pack_terms.py"),
        Path("test_tjlabs_pack_terms.py"),
    ]
    tjlabs_lines = [
        guard.AddedLine(path.as_posix(), line_number, text)
        for path in tjlabs_paths
        for line_number, text in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        )
    ]
    tjlabs_violations = guard.scan_added(tjlabs_lines)
    assert tjlabs_violations == [], tjlabs_violations

    # Run 33671956794 / SHA 77175db: CLAUDE.md owner-words card collocates
    # the noun "owner block" (a pinned instruction block) with a `memory/`
    # path, and the companion memory card says it is "not a door lock".
    # Those are open-door descriptions, not admission locks. Affirmative
    # memory/identity gates must still fail.
    claude_owner_words = "\n".join(
        [
            diff(
                "CLAUDE.md",
                [
                    "Every pinned owner block, law, directive, `ground/` card, `memory/` card, DIRECTIVES.md entry, and Slack #commons cite in this repo is Bryce's own text.",
                ],
            ),
            diff(
                "memory/CLAUDE_OWNER_WORDS.md",
                [
                    "This is behavior memory for Claude, not a door lock. No auth. No gate.",
                ],
            ),
        ]
    )
    assert guard.scan_diff(claude_owner_words) == [], guard.scan_diff(claude_owner_words)

    claude_blocked = "\n".join(
        [
            diff("ENTRY.md", ["The capability declaration is required before posting."]),
            diff("board.js", ["Reject posts whose memory card is missing."]),
            diff("carrier.js", ["block identity from posting without a seat."]),
        ]
    )
    assert rules(claude_blocked) == {"admission-phrase"}, rules(claude_blocked)

    claude_paths = [
        Path("CLAUDE.md"),
        Path("memory/CLAUDE_OWNER_WORDS.md"),
    ]
    claude_lines = [
        guard.AddedLine(path.as_posix(), line_number, text)
        for path in claude_paths
        for line_number, text in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        )
    ]
    claude_violations = guard.scan_added(claude_lines)
    assert claude_violations == [], claude_violations

    # Only explicit negative assertion syntax is exempt. Equivalent positive
    # assertions must still expose denial text and protected-path sets.
    positive_assertions = "\n".join(
        [
            diff("test_open_client.js", ['assert.ok(source.includes("permission denied"));']),
            diff("test_open_routes.py", ['self.assertTrue("authentication required" in source.lower())']),
            diff("test_module_surface.py", ['assert hasattr(module, "PROTECTED_FILES")']),
        ]
    )
    assert rules(positive_assertions) == {"explicit-denial", "protected-set"}, rules(positive_assertions)

    # Durable/generated board data is not executable policy and stays out of this guard.
    historical = "\n".join(
        [
            diff("p/old-gate-record.md", ["The capability declaration is required."]),
            diff("board.html", ["The capability declaration is required before posting."]),
            diff("recent.json", ['{"body": "const PROTECTED_PATHS = []; authentication required"}']),
            diff(
                "revenue/data/board_feed_sample_20260830.json",
                ['{"body": "historical quote: authentication required; PROTECTED_PATHS = []"}'],
            ),
        ]
    )
    assert guard.scan_diff(historical) == [], guard.scan_diff(historical)

    # Only the exact frozen JSON artifact is historical data. An active source
    # lookalike with the same stem must remain inside the policy guard.
    sample_source_lookalike = diff(
        "revenue/data/board_feed_sample_policy.py",
        ["PROTECTED_PATHS = []"],
    )
    assert rules(sample_source_lookalike) == {
        "protected-action",
        "protected-set",
    }, rules(sample_source_lookalike)

    # Compact catalog exclusion lists may name retired mechanisms only when they
    # do not collocate claim/seat with "gate" on one line. PR 4924's compact
    # out_of_scope one-liners failed open-door-guard on this collocation.
    catalog_blocked = "\n".join(
        [
            diff(
                "revenue/scope_to_delivery/catalog_bindings.json",
                ['      "out_of_scope": ["claim-purchase", "access-gate", "from-equals-payment"],'],
            ),
            diff(
                "revenue/scope_to_delivery/catalog_bindings.json",
                ['      "out_of_scope": ["seat", "claim", "access-gate"],'],
            ),
        ]
    )
    assert rules(catalog_blocked) == {"admission-phrase"}, rules(catalog_blocked)

    catalog_allowed = diff(
        "revenue/scope_to_delivery/catalog_bindings.json",
        [
            '      "out_of_scope": ["membership", "gated-entitlement", "private-buyer-data-on-main"],',
            '      "out_of_scope": ["claim-purchase", "gated-entitlement", "from-equals-payment"],',
            '      "out_of_scope": ["seat", "claim", "gated-entitlement"],',
        ],
    )
    assert guard.scan_diff(catalog_allowed) == [], guard.scan_diff(catalog_allowed)

    bindings_path = Path("revenue/scope_to_delivery/catalog_bindings.json")
    binding_lines = [
        guard.AddedLine(bindings_path.as_posix(), line_number, text)
        for line_number, text in enumerate(bindings_path.read_text(encoding="utf-8").splitlines(), 1)
    ]
    binding_violations = guard.scan_added(binding_lines)
    assert binding_violations == [], binding_violations


    # Binary artifacts may make `git diff --text` emit non-UTF-8 bytes.  They
    # must never crash or blind the additions guard.
    original_run = guard.subprocess.run
    try:
        guard.subprocess.run = lambda *args, **kwargs: CompletedProcess(
            args=args[0], returncode=0,
            stdout=b"diff --git a/excerpts/x.mno b/excerpts/x.mno\n+\x80binary\n",
            stderr=b"",
        )
        decoded = guard.git_diff("base", "head")
        assert "binary" in decoded
        assert guard.scan_diff(decoded) == []
    finally:
        guard.subprocess.run = original_run

    # Current active entry/agent/Slack instructions contain only the exact
    # directive and open-door prohibition language, never an affirmative
    # admission lock.  The Slack card used to require a complete capability
    # declaration even after ENTRY made every field optional.
    context_paths = [
        Path("AGENTS.md"),
        Path("START.md"),
        Path("ground/EXECUTE.md"),
        Path(".cursor/rules/execute-immediately.mdc"),
    ]
    for path in context_paths:
        context = path.read_text(encoding="utf-8")
        assert "NO AUTH" in context, path
        assert "every turn" in context, path
        assert "login, signup, session, token, credential" in context, path
        assert "any equivalent lock anywhere in Commons" in context, path

    instruction_paths = [
        *context_paths,
        Path("ENTRY.md"),
        Path("ground/SLACK.md"),
        *Path(".agents").rglob("*.md"),
    ]
    instruction_lines = [
        guard.AddedLine(path.as_posix(), line_number, text)
        for path in instruction_paths
        for line_number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
    ]
    instruction_violations = guard.scan_added(instruction_lines)
    assert instruction_violations == [], instruction_violations

    print("OPEN DOOR GUARD TEST: additions blocked; removals, directive, and active instructions pass")


if __name__ == "__main__":
    main()
