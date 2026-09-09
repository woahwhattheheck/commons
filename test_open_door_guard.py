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

    test_workflow_diff_base()

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

    # Run 34001046530 mistook a table label for admission policy in three
    # unchanged business descriptions when their test-presence cells changed.
    # HTML attributes and adjacent prose are independent contexts; neither
    # context is exempt from inspection, including inline-formatted policy.
    for business_text in (
        "AIT Minnesota Metrc capacity gate LIMS",
        "Lexington MRF diversion gate",
        "Prein Newhof PFAS fieldblank gate LIMS",
    ):
        catalog_row = (
            '<tr><td data-label="capability">' + business_text + '</td>'
            '<td data-label="tests">TESTS_PRESENT</td></tr>'
        )
        assert guard.scan_diff(diff("feature-tracker.html", [catalog_row])) == []

    for markup in (
        '<p>Identity is required before posting.</p>',
        '<p>Identity <strong>is required</strong> before posting.</p>',
        '<p>Memory&nbsp;required before posting.</p>',
        '<p>Identity<!-- explanatory comment --> is required.</p>',
        '<td data-label="capability">Identity is required before posting.</td>',
        '<div data-policy="identity required"></div>',
        '<div data-field="identity" data-state="required"></div>',
        '<div title="x > y" data-policy="identity required"></div>',
        '<!-- Identity is required before posting. -->',
        '<script>const policy = "identity required";</script>',
        '<script>const policy = "identity required";',
        '<![CDATA[identity required]]>',
        '<div data-policy="identity required',
        '<input name="identity" required',
    ):
        assert "admission-phrase" in rules(diff("action.html", [markup])), markup

    separate_cells = '<tr><td>Capability</td><td>Laboratory capacity gate</td></tr>'
    assert guard.scan_diff(diff("catalog.html", [separate_cells])) == []
    assert "admission-phrase" in rules(diff("policy.py", ['policy = "identity required"']))
    assert "gate-identifier" in rules(diff("catalog.html", [
        '<td data-label="capability">const IDENTITY_GATE = true;</td>',
    ]))
    assert "required-speaker-field" in rules(diff("action.html", [
        '<input', 'name="identity"', 'required>',
    ]))

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

    # Polar AS9100 #11191 landed PermissionError raises whose nearby source did
    # not prove production-LIMS human-release context, so open-door-guard failed
    # on the merge SHA. Keep the fail-closed product behavior, but require the
    # existing human-release vocabulary. Commons-path copies stay rejectable.
    polar_old_lock = diff(
        "revenue/production-lims/trace-polar-as9100/trace_polar_as9100.py",
        [
            'raise PermissionError("held evidence cannot be approved")',
            'raise PermissionError("automatic disposition disabled")',
        ],
    )
    assert rules(polar_old_lock) == {"permission-exception"}, rules(polar_old_lock)
    polar_release = diff(
        "revenue/production-lims/trace-polar-as9100/trace_polar_as9100.py",
        [
            'if pack["status"] != "REVIEW_READY":',
            '    raise PermissionError("held evidence cannot release a report")',
            'def automatic_disposition(self, *_args, **_kwargs):',
            '    raise PermissionError("automatic release is disabled")',
        ],
    )
    assert guard.scan_diff(polar_release) == [], guard.scan_diff(polar_release)
    assert "permission-exception" in rules(diff("commons_mcp.py", [
        'raise PermissionError("automatic release is disabled")',
    ]))
    polar_path = Path("revenue/production-lims/trace-polar-as9100/trace_polar_as9100.py")
    polar_added = [
        guard.AddedLine(polar_path.as_posix(), line_number, text)
        for line_number, text in enumerate(polar_path.read_text(encoding="utf-8").splitlines(), 1)
    ]
    polar_violations = [
        item for item in guard.scan_added(polar_added) if item.rule == "permission-exception"
    ]
    assert polar_violations == [], polar_violations

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

    # Run 34189413855 / SHA 95c5b22: explicit-WOOL consumer stored per-objective
    # selected game plans in a field named `choices` next to `action`. That is
    # a result map, not an Action Pad verb enum. The collocation still fails;
    # the renamed field must pass, and the live experiment source must stay clean.
    wool_blocked = "\n".join(
        [
            diff(
                "revenue/kaggriculture/cloud-market-response/check_joint_wool_hypotheses.py",
                [
                    "out = {'original_action': deepcopy(action), 'choices': {}, 'counts': {}}",
                ],
            ),
            diff(
                "revenue/kaggriculture/cloud-market-response/check_joint_wool_hypotheses.py",
                [
                    "out['choices'][tie] = {'action': chosen, 'changed': chosen != action}",
                ],
            ),
        ]
    )
    assert rules(wool_blocked) == {"verb-enum"}, rules(wool_blocked)

    wool_allowed = diff(
        "revenue/kaggriculture/cloud-market-response/check_joint_wool_hypotheses.py",
        [
            "out = {'original_action': deepcopy(action), 'by_objective': {}, 'counts': {}}",
            "out['by_objective'][tie] = {'action': chosen, 'changed': chosen != action}",
        ],
    )
    assert guard.scan_diff(wool_allowed) == [], guard.scan_diff(wool_allowed)

    wool_path = Path("revenue/kaggriculture/cloud-market-response/check_joint_wool_hypotheses.py")
    wool_lines = [
        guard.AddedLine(wool_path.as_posix(), line_number, text)
        for line_number, text in enumerate(wool_path.read_text(encoding="utf-8").splitlines(), 1)
    ]
    wool_violations = guard.scan_added(wool_lines)
    assert wool_violations == [], wool_violations

    # Run 34190268951 / SHA 285dedd: TRACE-9042 completeness tests mutate a
    # retained cell's recorded player-view field and then call a unittest
    # helper. Collocating `seat` with `reject` on one line is still an
    # admission phrase. Split assignment and helper remain data checks.
    report_cell_path = (
        "revenue/kaggriculture/cloud-execution-lab/trace-cache-checks/"
        "test_report_completeness.py"
    )
    report_cell_blocked = diff(
        report_cell_path,
        [
            "def test_wrong_view_seat(self):self.data['uncached']['cells'][0]['seat']=1;self.reject()"
        ],
    )
    assert rules(report_cell_blocked) == {"admission-phrase"}, rules(report_cell_blocked)
    report_cell_allowed = diff(
        report_cell_path,
        [
            "def test_wrong_view_seat(self):",
            "    self.data['uncached']['cells'][0]['seat']=1",
            "    self.reject()",
        ],
    )
    assert guard.scan_diff(report_cell_allowed) == [], guard.scan_diff(report_cell_allowed)
    completeness_path = Path(report_cell_path)
    completeness_lines = [
        guard.AddedLine(completeness_path.as_posix(), line_number, text)
        for line_number, text in enumerate(
            completeness_path.read_text(encoding="utf-8").splitlines(), 1
        )
    ]
    completeness_violations = guard.scan_added(completeness_lines)
    assert completeness_violations == [], completeness_violations

    # Run 34220005044 / SHA 4b125d39: Hive #044 Parts Sourcing Desk added
    # <input name="model" required> for equipment model. The guard treats
    # name="model" as a speaker/capability field, so HTML required is an
    # admission lock. Equipment model stays optional in markup; backend
    # workshop validation is unchanged. The original required tag must
    # still fail; the repaired live file must stay clean.
    parts_desk_html = "revenue/hive/parts-sourcing-desk/index.html"
    parts_desk_blocked = diff(
        parts_desk_html,
        [
            '<label>Exact model<input name="model" required placeholder="Copy the model label"></label>',
        ],
    )
    assert rules(parts_desk_blocked) == {"required-speaker-field"}, rules(parts_desk_blocked)
    parts_desk_allowed = diff(
        parts_desk_html,
        [
            '<label>Exact model<input name="model" placeholder="Copy the model label"></label>',
        ],
    )
    assert guard.scan_diff(parts_desk_allowed) == [], guard.scan_diff(parts_desk_allowed)
    parts_path = Path(parts_desk_html)
    parts_lines = [
        guard.AddedLine(parts_path.as_posix(), line_number, text)
        for line_number, text in enumerate(
            parts_path.read_text(encoding="utf-8").splitlines(), 1
        )
    ]
    parts_violations = guard.scan_added(parts_lines)
    assert parts_violations == [], parts_violations

    # Run 34372584220 / SHA 994a0bff: E17 RESULTS checkpoint collocated
    # "default-promotion claim" with "The required next experiment" on one
    # line. That is a no-result boundary, not identity/claim admission.
    # The collocation still fails; the reworded live file must stay clean.
    e17_results_path = "revenue/kaggriculture/cloud-e17-regime-history/RESULTS.md"
    e17_results_blocked = diff(
        e17_results_path,
        [
            "Therefore there is **no terminal-cash, win-rate, downside, runtime, or default-promotion claim**. The required next experiment remains a source-pinned matched screen.",
        ],
    )
    assert rules(e17_results_blocked) == {"admission-phrase"}, rules(e17_results_blocked)
    e17_results_allowed = diff(
        e17_results_path,
        [
            "Therefore there is **no terminal-cash, win-rate, downside, runtime, or default-promotion outcome**. The next experiment remains a source-pinned matched screen.",
        ],
    )
    assert guard.scan_diff(e17_results_allowed) == [], guard.scan_diff(e17_results_allowed)
    e17_path = Path(e17_results_path)
    e17_lines = [
        guard.AddedLine(e17_path.as_posix(), line_number, text)
        for line_number, text in enumerate(
            e17_path.read_text(encoding="utf-8").splitlines(), 1
        )
    ]
    e17_violations = guard.scan_added(e17_lines)
    assert e17_violations == [], e17_violations


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


def test_workflow_diff_base():
    """Execute the real workflow shell and scanner on isolated Git histories."""
    import os
    import shutil
    import subprocess
    import tempfile
    import textwrap

    root = Path(__file__).resolve().parent
    workflow = (root / '.github/workflows/open-door-guard.yml').read_text(encoding='utf-8')
    step = workflow.split('      - name: reject newly added ', 1)[1]
    block = step.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
    script = textwrap.dedent(block)
    scanner = root / 'open_door_guard.py'
    cases = []
    with tempfile.TemporaryDirectory(prefix='guard-base-') as temporary:
        tmp = Path(temporary)
        home = tmp / 'home'
        home.mkdir()
        env = dict(os.environ, HOME=str(home), GIT_CONFIG_NOSYSTEM='1',
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0')
        repo = tmp / 'repo'
        repo.mkdir()

        def command(args, cwd=repo, *, check=True, input=None, extra=None):
            result = subprocess.run(args, cwd=cwd, env=dict(env, **(extra or {})),
                input=input, text=True, capture_output=True, timeout=20)
            if check:
                assert result.returncode == 0, (args, result.stdout, result.stderr)
            return result

        def git(*args, cwd=repo, check=True, input=None):
            return command(['git', *args], cwd, check=check, input=input)

        def commit(message):
            git('add', '.')
            git('commit', '-qm', message)
            return git('rev-parse', 'HEAD').stdout.strip()

        def check_case(name, expected, cwd=repo, *, event='pull_request',
                       pr_head=None, push_base='', contains=None, absent=None):
            result = command(['bash', '-c', script], cwd, check=False, extra={
                'EVENT_NAME': event, 'PR_HEAD_SHA': pr_head or feature_head,
                # Deliberately stale metadata reproduces the provider incident.
                'PR_BASE_SHA': old_base, 'PUSH_BASE_SHA': push_base,
            })
            output = result.stdout + result.stderr
            assert result.returncode == expected, (name, result.returncode, output)
            if contains:
                assert contains in output, (name, output)
            if absent:
                assert absent not in output, (name, output)
            cases.append(name)
            return result

        git('init', '-q', '-b', 'main')
        git('config', 'user.name', 'Workflow fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        shutil.copyfile(scanner, repo / 'open_door_guard.py')
        (repo / 'README.md').write_text('Initial fixture.\n', encoding='utf-8')
        old_base = commit('initial')
        git('checkout', '-qb', 'feature')
        (repo / 'candidate.py').write_text('value = 1\n', encoding='utf-8')
        feature_head = commit('candidate')
        git('checkout', '-q', 'main')
        (repo / 'concurrent.py').write_text("PROTECTED_FILES = {'example'}\n", encoding='utf-8')
        actual_base = commit('concurrent base')
        git('merge', '-q', '--no-ff', 'feature', '-m',
            'integration\n\nparent this-is-message-text-not-a-header')
        merged = git('rev-parse', 'HEAD').stdout.strip()
        raw_parents = git('cat-file', '-p', 'HEAD').stdout.split('\n\n', 1)[0]
        assert 'parent ' + actual_base in raw_parents
        assert 'parent ' + feature_head in raw_parents

        old_result = command(['python3', 'open_door_guard.py', '--diff', old_base, merged], check=False)
        assert old_result.returncode == 1 and 'concurrent.py:' in old_result.stderr
        cases.append('stale-event-base-reproduces-concurrent-finding')
        check_case('actual-merge-base-excludes-concurrent-change', 0, contains='GUARD: PASS')
        check_case('wrong-second-parent-is-not-a-pass', 1, pr_head=old_base, absent='GUARD: PASS')
        check_case('push-still-sees-all-pushed-additions', 1, event='push', push_base=old_base,
                   contains='concurrent.py:')
        check_case('push-retains-existing-comparison', 0, event='push', push_base=actual_base,
                   contains='GUARD: PASS')

        # A shallow clone retains the raw merge header even when parent objects
        # are absent. The exact base is fetched from this local fixture only.
        git('branch', 'integration', merged)
        bare = tmp / 'remote.git'
        git('clone', '-q', '--bare', str(repo), str(bare), cwd=tmp)
        for folder in ('shallow', 'missing-base'):
            git('clone', '-q', '--depth=1', '--branch', 'integration', bare.as_uri(),
                str(tmp / folder), cwd=tmp)
        shallow = tmp / 'shallow'
        assert git('rev-parse', '--is-shallow-repository', cwd=shallow).stdout.strip() == 'true'
        assert git('cat-file', '-e', actual_base + '^{commit}', cwd=shallow, check=False).returncode != 0
        check_case('depth-one-checkout-fetches-exact-first-parent', 0, cwd=shallow,
                   contains='GUARD: PASS')
        git('cat-file', '-e', actual_base + '^{commit}', cwd=shallow)
        assert git('rev-parse', '--is-shallow-repository', cwd=shallow).stdout.strip() == 'true'
        missing = tmp / 'missing-base'
        git('remote', 'set-url', 'origin', str(tmp / 'absent-remote'), cwd=missing)
        check_case('missing-required-base-is-not-a-pass', 128, cwd=missing, absent='GUARD: PASS')

        # A new finding in the feature still reaches the unchanged scanner.
        git('checkout', '-qb', 'bad-feature', old_base)
        (repo / 'introduced.py').write_text("ALLOWED_VERBS = {'READ'}\n", encoding='utf-8')
        bad_head = commit('candidate finding')
        git('checkout', '-q', '--detach', actual_base)
        git('merge', '-q', '--no-ff', 'bad-feature', '-m', 'bad integration')
        check_case('feature-finding-remains-visible', 1, pr_head=bad_head,
                   contains='introduced.py:', absent='concurrent.py:')

        # Integration-only resolutions are included, not a head-only shortcut.
        git('checkout', '-q', '--detach', merged)
        (repo / 'resolution.py').write_text("ALLOWED_VERBS = {'READ'}\n", encoding='utf-8')
        git('add', 'resolution.py')
        tree = git('write-tree').stdout.strip()
        resolved = git('commit-tree', tree, '-p', actual_base, '-p', feature_head,
                       input='integration-only addition\n').stdout.strip()
        git('checkout', '-q', '--detach', resolved)
        check_case('merge-resolution-finding-remains-visible', 1,
                   contains='resolution.py:', absent='concurrent.py:')
        git('checkout', '-q', '--detach', feature_head)
        check_case('non-merge-pr-checkout-is-not-a-pass', 1, absent='GUARD: PASS')

    print('OPEN DOOR WORKFLOW BASE TEST: ' + str(len(cases)) + ' actual-Git cases pass')
    return cases


if __name__ == "__main__":
    main()
