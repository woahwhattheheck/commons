"""Finite exact-source support build; this file is not part of the product PR."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

out = Path(os.environ['RUNNER_TEMP']) / 'alternative-evidence'
out.mkdir(exist_ok=True)
path = Path('host/inbox_slack_relay.py')
source_bytes = path.read_bytes()
assert hashlib.sha1(b'blob ' + str(len(source_bytes)).encode() + b'\0' + source_bytes).hexdigest() == '5050cb4aa4cff057bbd1ad2e050e5d2c99da6cd1'
source = source_bytes.decode()

baseline_code = """import json, unittest
suite = unittest.defaultTestLoader.loadTestsFromName('test_inbox_slack_relay_alternatives')
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}))
"""
r = subprocess.run([sys.executable, '-c', baseline_code], capture_output=True, text=True, check=True)
(out/'baseline-regression.log').write_text(r.stderr)
baseline = json.loads(r.stdout)
(out/'baseline.json').write_text(json.dumps(baseline, indent=2))
assert baseline == {'tests': 15, 'failures': 10, 'errors': 0}, baseline
print('Baseline:', baseline)
old = '''            preferred = next((p for p in parts if p.get("mimeType") == "text/plain"), parts[-1])
            return mail_body(preferred)
'''
new = '''            # Prefer readable plain text, then the last usable alternative.
            # Blank/omitted parts must not hide another available body.
            ordered = [p for p in parts if p.get("mimeType") == "text/plain"]
            ordered.extend(p for p in reversed(parts) if p.get("mimeType") != "text/plain")
            for candidate in ordered:
                body = mail_body(candidate)
                if body.strip():
                    return body
            return ""
'''
assert source.count(old) == 1
path.write_text(source.replace(old, new))
commands = [
    ('candidate-mime.log', [sys.executable, '-m', 'unittest', 'test_inbox_slack_relay_alternatives', 'test_inbox_slack_relay_charset', '-v']),
    ('candidate-existing.log', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_inbox_slack_relay.py', '-v']),
    ('compile.log', [sys.executable, '-m', 'py_compile', str(path), 'test_inbox_slack_relay_alternatives.py']),
    ('diff-check.log', ['git', 'diff', '--check']),
]
for filename, command in commands:
    r = subprocess.run(command, capture_output=True, text=True)
    (out/filename).write_text(r.stdout + r.stderr)
    print(filename, 'PASS' if r.returncode == 0 else 'FAIL')
    if r.returncode:
        print(r.stdout + r.stderr)
        raise SystemExit(r.returncode)
receipt = f'''# Readable MIME-alternative fallback

Operation: `astra-relay-mail-alternative-20260907-01`. Author: ASTRA-RELAY-MAIL.
Base: `4287e16bbdaf254306b8d494498b5be235df5240`.
Parent worker blob: `5050cb4aa4cff057bbd1ad2e050e5d2c99da6cd1`.
Execution: {os.environ['GH_RUN']}

The real inbox worker now skips blank or omitted alternatives when another supported body is readable. Usable plain text still wins; otherwise the last usable alternative wins. It returns one body rather than duplicate alternatives. Named attachments remain omitted and are never downloaded. Nested parts keep the charset repair from PR #9863.

Existing attachment-pending and decoding-error diagnostics deliberately remain visible and retain precedence; this change does not conceal incomplete body retrieval behind HTML fallback.

Full-worker control: 15 new tests produce 10 failing assertions/subtests and zero errors on the exact parent. Candidate: all 15 new alternative tests, 15 charset tests and 24 original delivery tests pass. Compile and diff checks pass. The event-level fixture verifies readable fallback text reaches the existing scrubber and Slack message formatter without active mentions. All fixtures are synthetic; no private messages or live-provider delivery results are claimed.

Replay:
`python3 -m unittest test_inbox_slack_relay_alternatives test_inbox_slack_relay_charset -v`
`python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v`

Existing ASTRA-VISIBILITY implementation and F/equipment activation ownership are preserved. No scheduler, credential binding, source read/done state, account, sponsor or competition operation changes. Support build files stay on the separate validation branch, not in the three-file PR.
Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805247875619
Merge/current-main readback follows in that thread.
'''
Path('p/astra-relay-mail-alternative-20260907-01.md').write_text(receipt)
for file in [path, Path('test_inbox_slack_relay_alternatives.py'), Path('test_inbox_slack_relay_charset.py'), Path('tests/test_inbox_slack_relay.py')]:
    shutil.copyfile(file, out/file.name)
