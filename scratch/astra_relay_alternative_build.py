NEW_PARSER = r'''def mail_body(payload: dict) -> str:
    """No image/link retrieval, attachments, or duplicate HTML alternatives."""
    return _mail_body_content(payload)[0]


def _mail_body_content(payload: dict) -> tuple[str, bool]:
    """Return rendered text and whether it contains readable source content.

    Diagnostics are retained when no alternative is readable, but are not
    themselves source content. Keep this fact separate from the text so a
    literal diagnostic-looking message remains an ordinary readable message.
    """
    if payload.get("filename"):
        return "", False
    parts = payload.get("parts", [])
    if parts:
        if payload.get("mimeType") == "multipart/alternative":
            # Prefer readable plain text, then the last usable alternative.
            ordered = [p for p in parts if p.get("mimeType") == "text/plain"]
            ordered.extend(p for p in reversed(parts) if p.get("mimeType") != "text/plain")
            diagnostic = ""
            for candidate in ordered:
                body, readable = _mail_body_content(candidate)
                if readable:
                    return body, True
                if body.strip() and not diagnostic:
                    diagnostic = body
            return diagnostic, False
        rendered = [_mail_body_content(p) for p in parts]
        return "\n".join(body for body, _ in rendered if body), any(readable for _, readable in rendered)
    encoded = payload.get("body", {}).get("data", "")
    if not encoded:
        diagnostic = "[Body stored as an attachment; read original in Gmail.]" if payload.get("body", {}).get("attachmentId") else ""
        return diagnostic, False
    try:
        data = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except (ValueError, TypeError):
        return "[Body decoding failed; read original in Gmail.]", False
    # Gmail returns MIME-part bytes, not necessarily UTF-8. Read the leaf's
    # Content-Type; a container's charset does not override its child parts.
    mime = Message()
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == "content-type":
            mime["Content-Type"] = header.get("value", "")
            break
    try:
        raw = data.decode(mime.get_content_charset() or "utf-8", errors="replace")
    except (LookupError, ValueError):
        # Unknown, malformed, and non-text codec names must not drop work mail.
        raw = data.decode("utf-8", errors="replace")
    if payload.get("mimeType") == "text/html":
        parser = PlainHTML()
        parser.feed(raw)
        body = "".join(parser.parts).strip()
    else:
        body = raw if payload.get("mimeType", "text/plain") == "text/plain" else ""
    return body, bool(body.strip())
'''

ADDED_TESTS = r'''

class MailDiagnosticAlternativeTests(unittest.TestCase):
    pending_text = "[Body stored as an attachment; read original in Gmail.]"
    invalid_text = "[Body decoding failed; read original in Gmail.]"

    @staticmethod
    def pending(mime_type="text/plain"):
        return {"mimeType": mime_type, "body": {"attachmentId": "synthetic"}}

    @staticmethod
    def invalid(mime_type="text/plain"):
        return {"mimeType": mime_type, "body": {"data": "a"}}

    def test_pending_plain_uses_next_readable_plain_before_html(self):
        payload = alternative(self.pending(), part("next plain"), part("<p>HTML</p>", "text/html"))
        self.assertEqual(mail_body(payload), "next plain")

    def test_invalid_plain_uses_next_readable_plain(self):
        self.assertEqual(mail_body(alternative(self.invalid(), part("next plain"))), "next plain")

    def test_pending_last_html_does_not_hide_earlier_html(self):
        payload = alternative(part("<p>available</p>", "text/html"), self.pending("text/html"))
        self.assertEqual(mail_body(payload), "available")

    def test_invalid_last_html_does_not_hide_earlier_html(self):
        payload = alternative(part("<p>available</p>", "text/html"), self.invalid("text/html"))
        self.assertEqual(mail_body(payload), "available")

    def test_nested_diagnostic_alternative_does_not_hide_readable_body(self):
        payload = alternative(part("<p>available</p>", "text/html"), alternative(self.pending(), self.invalid()))
        self.assertEqual(mail_body(payload), "available")

    def test_nested_diagnostic_mixed_part_does_not_hide_readable_body(self):
        unavailable = {"mimeType": "multipart/mixed", "parts": [self.pending(), self.invalid()]}
        self.assertEqual(mail_body(alternative(part("<p>available</p>", "text/html"), unavailable)), "available")

    def test_mixed_readable_and_missing_parts_preserve_missing_diagnostic(self):
        mixed = {"mimeType": "multipart/mixed", "parts": [self.pending(), part("available portion")]}
        self.assertEqual(mail_body(alternative(part("<p>earlier</p>", "text/html"), mixed)),
                         self.pending_text + "\navailable portion")

    def test_pending_diagnostic_retained_without_readable_alternative(self):
        self.assertEqual(mail_body(alternative(self.pending(), part("<p> </p>", "text/html"))), self.pending_text)
        self.assertEqual(mail_body(self.pending()), self.pending_text)

    def test_decode_diagnostic_retained_without_readable_alternative(self):
        self.assertEqual(mail_body(alternative(self.invalid(), part(""))), self.invalid_text)
        self.assertEqual(mail_body(self.invalid()), self.invalid_text)

    def test_multiple_unavailable_alternatives_keep_first_diagnostic(self):
        self.assertEqual(mail_body(alternative(self.pending(), self.invalid())), self.pending_text)
        self.assertEqual(mail_body(alternative(self.invalid(), self.pending())), self.invalid_text)

    def test_literal_diagnostic_looking_source_text_is_readable(self):
        for literal in (self.pending_text, self.invalid_text, self.pending_text + "\n" + self.invalid_text):
            with self.subTest(literal=literal):
                self.assertEqual(mail_body(alternative(part(literal), part("<p>HTML</p>", "text/html"))), literal)

    def test_hidden_only_html_does_not_discard_diagnostic(self):
        hidden = part("<head><title>hidden</title></head><script>ignored</script><style>hidden</style>", "text/html")
        self.assertEqual(mail_body(alternative(self.pending(), hidden)), self.pending_text)

    def test_diagnostic_fallback_preserves_leaf_charset(self):
        for body, encoding in (("Résumé — €200", "windows-1252"), ("日本語", "iso-2022-jp")):
            with self.subTest(encoding=encoding):
                payload = alternative(self.pending(), part("<p>" + body + "</p>", "text/html", encoding))
                self.assertEqual(mail_body(payload), body)

    def test_named_attachment_is_not_a_readable_fallback(self):
        payload = alternative(self.pending(), part("attachment contents", filename="private.txt"))
        self.assertEqual(mail_body(payload), self.pending_text)

    def test_diagnostic_fallback_does_not_mutate_mime_tree(self):
        payload = alternative(self.pending(), alternative(self.invalid(), part("<p>available</p>", "text/html")))
        before = copy.deepcopy(payload)
        self.assertEqual(mail_body(payload), "available")
        self.assertEqual(payload, before)

    def test_diagnostic_fallback_never_fetches_attachments_or_links(self):
        from unittest.mock import patch
        from host import inbox_slack_relay as relay
        with patch.object(relay.urllib.request, "build_opener", side_effect=AssertionError("network")), \
                patch.object(relay, "command_json", side_effect=AssertionError("CLI")):
            payload = alternative(self.pending(), part('<p>available</p><img src="https://example.invalid/image">', "text/html"))
            self.assertEqual(mail_body(payload), "available")

    def test_gmail_fallback_has_no_pending_body_and_keeps_redaction(self):
        payload = alternative(self.pending(), part("<p>Review &lt;@U123&gt; @here api_key=fixture</p>", "text/html"))
        payload["headers"] = [{"name": "Subject", "value": "Review deadline"}, {"name": "From", "value": "work@example.invalid"}]
        message = {"id": "synthetic", "threadId": "synthetic-thread", "labelIds": ["INBOX"], "payload": payload}
        calls = []
        def get(resource, params=None):
            calls.append(resource)
            return {"profile": {"emailAddress": "work@example.invalid"}, "messages": {"messages": [{"id": "synthetic"}]}, "messages/synthetic": message}[resource]
        events, info = gmail_events(get, {"gmail_address": "work@example.invalid"}, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(info["body_pending"], 0)
        rendered = "\n".join(events[0].messages())
        self.assertIn("Review", rendered)
        self.assertIn("api_key=[REDACTED]", rendered)
        self.assertNotIn("fixture", rendered)
        self.assertNotIn("<@U123>", rendered)
        self.assertNotIn("@here", rendered)
        self.assertEqual(calls, ["profile", "messages", "messages/synthetic"])
        self.assertEqual(events[0].messages(), events[0].messages())

    def test_gmail_missing_mixed_part_still_counts_as_pending(self):
        mixed = {"mimeType": "multipart/mixed", "parts": [self.pending(), part("available portion")]}
        payload = alternative(part("<p>earlier</p>", "text/html"), mixed)
        payload["headers"] = [{"name": "Subject", "value": "Review deadline"}, {"name": "From", "value": "work@example.invalid"}]
        message = {"id": "synthetic", "threadId": "synthetic-thread", "labelIds": ["INBOX"], "payload": payload}
        def get(resource, params=None):
            return {"profile": {"emailAddress": "work@example.invalid"}, "messages": {"messages": [{"id": "synthetic"}]}, "messages/synthetic": message}[resource]
        events, info = gmail_events(get, {"gmail_address": "work@example.invalid"}, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(info["body_pending"], 1)
        self.assertEqual(events[0].body, self.pending_text + "\navailable portion")
'''

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

OUT = Path(os.environ['RUNNER_TEMP']) / 'relay-alternative-evidence'
OUT.mkdir(exist_ok=True)
WORKER = Path('host/inbox_slack_relay.py')
TEST = Path('test_inbox_slack_relay_alternatives.py')
EXPECTED = {str(WORKER): 'd6f87988dcf54ed14ff6cfc496e814ed3a728323', str(TEST): '8686a4261262e59d65bab366f705a42b2033ebd0'}

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

def run_logged(name, command, check=True):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
    (OUT / name).write_text(result.stdout, encoding='utf-8')
    print(result.stdout)
    if check and result.returncode:
        raise RuntimeError(name + ' failed')
    return result

base = git('rev-parse', 'HEAD')
for path, expected in EXPECTED.items():
    assert git('hash-object', path) == expected, path + ' changed: compose before publishing'
original = WORKER.read_text(encoding='utf-8')
original_tests = TEST.read_text(encoding='utf-8')
(OUT / 'worker-before.py').write_text(original, encoding='utf-8')
(OUT / 'tests-before.py').write_text(original_tests, encoding='utf-8')
updated_tests = original_tests
for variable, marker, old_name, new_name in [
    ('pending', '[Body stored as an attachment; read original in Gmail.]', 'test_existing_pending_attachment_diagnostic_is_preserved', 'test_pending_plain_falls_back_when_html_is_readable'),
    ('invalid', '[Body decoding failed; read original in Gmail.]', 'test_existing_decode_diagnostic_is_preserved', 'test_invalid_plain_falls_back_when_html_is_readable'),
]:
    old = f'        self.assertEqual(mail_body(alternative({variable}, part("<p>HTML</p>", "text/html"))), "{marker}")'
    new = f'        self.assertEqual(mail_body(alternative({variable}, part("<p>HTML</p>", "text/html"))), "HTML")'
    assert updated_tests.count(old) == 1
    assert updated_tests.count(old_name) == 1
    updated_tests = updated_tests.replace(old, new).replace(old_name, new_name)
entrypoint = '\n\nif __name__ == "__main__":'
assert updated_tests.count(entrypoint) == 1
updated_tests = updated_tests.replace(entrypoint, ADDED_TESTS + entrypoint)
TEST.write_text(updated_tests, encoding='utf-8')
baseline = run_logged('baseline-new-tests.log', [sys.executable, '-m', 'unittest', 'test_inbox_slack_relay_alternatives.MailDiagnosticAlternativeTests', '-v'], check=False)
assert baseline.returncode != 0, 'baseline must distinguish the new tests'
assert 'ERROR:' not in baseline.stdout, 'unexpected baseline error'
assert 'FAIL: test_pending_plain_uses_next_readable_plain_before_html' in baseline.stdout
assert 'FAIL: test_gmail_fallback_has_no_pending_body_and_keeps_redaction' in baseline.stdout
failure_records = int(re.search(r'FAILED \(failures=(\d+)\)', baseline.stdout).group(1))
start = original.index('def mail_body(')
end = original.index('\n\ndef attachment_names(', start)
updated = original[:start] + NEW_PARSER.rstrip() + original[end:]
WORKER.write_text(updated, encoding='utf-8')
commands = [
    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_inbox_slack_relay.py', '-v'],
    [sys.executable, '-m', 'unittest', 'test_inbox_slack_relay_charset', 'test_inbox_slack_relay_alternatives', 'test_inbox_slack_relay_headers', 'test_inbox_slack_relay_urls', '-v'],
]
counts = []
for index, command in enumerate(commands):
    result = run_logged(f'candidate-{index}.log', command)
    counts.append(int(re.search(r'Ran (\d+) tests?', result.stdout).group(1)))
assert sum(counts) == 135, counts
subprocess.run([sys.executable, '-m', 'py_compile', str(WORKER), str(TEST)], check=True)
subprocess.run(['git', 'diff', '--check'], check=True)
(OUT / 'worker-after.py').write_text(updated, encoding='utf-8')
(OUT / 'tests-after.py').write_text(updated_tests, encoding='utf-8')
run_url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
receipt = Path('p/astra-relay-readable-alternative-20260908-01.md')
assert not receipt.exists()
receipt.parent.mkdir(exist_ok=True)
receipt.write_text(f'''# Readable email alternatives survive unavailable MIME parts

Operation: `astra-relay-readable-alternative-20260908-01`. Builder: ASTRA-RELAY.
Original ASTRA-VISIBILITY, MAIL, charset, alternative, URL and COOLDOWN contributions remain credited.

## Product behavior

The existing string-returning `mail_body()` API now delegates to a private renderer carrying a separate readable-content flag. Diagnostic-only parts cannot hide available alternatives. Plain text remains preferred; nonplain alternatives retain last-readable preference. Nested multipart content preserves diagnostics for genuinely missing portions, and all-unavailable alternatives retain the original first diagnostic. Literal diagnostic-looking source text is not mistaken for a parser status. No attachment or source URL is fetched.

Only the parser region, its already-wired alternative suite and this receipt change. Eighteen new test methods are added. Two existing combined diagnostic-plus-readable-HTML assertions are deliberately updated to expect the available content; standalone/no-readable diagnostic behavior is covered separately. No test is removed or skipped. Existing charset, privacy, source-state, deduplication and cooldown logic is unchanged.

## Actual execution

- Source base: `{base}`; original worker `{EXPECTED[str(WORKER)]}`; original alternatives `{EXPECTED[str(TEST)]}`.
- [Hosted run and logs]({run_url}); Python `{sys.version.split()[0]}`.
- The original worker produced {failure_records} assertion-failure records and zero errors on the 18 added methods. These are synthetic parser/provider fixtures, not live mailbox incidents.
- Candidate: {sum(counts)} passing test methods ({' + '.join(map(str, counts))}); compile and whitespace checks passed.
- Candidate worker blob `{git('hash-object', str(WORKER))}`; alternative suite blob `{git('hash-object', str(TEST))}`.
- The existing inbox workflow already runs the extended suite; no product workflow or scheduler configuration changed. The branch-only build recipe is excluded from the product.

Replay:
```sh
python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v
python3 -m unittest test_inbox_slack_relay_charset test_inbox_slack_relay_alternatives test_inbox_slack_relay_headers test_inbox_slack_relay_urls -v
```

Gmail's MessagePartBody contract distinguishes inline data from attachmentId-only parts: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments . This parser uses already-returned inline alternatives; it adds no attachment request.

## Delivery boundary

No application credentials, source inbox mutations, source deliveries, account actions, paid service, or owner-PC work occurred. F/equipment retains actual relay activation. This is tested source delivery, not an activation or full-repository green claim. Merge and current-main readback belong in the existing Slack work thread.
''', encoding='utf-8')
paths = [str(WORKER), str(TEST), str(receipt)]
subprocess.run(['git', 'add', '--sparse', '--', *paths], check=True)
assert sorted(git('diff', '--cached', '--name-only').splitlines()) == sorted(paths)
subprocess.run(['git', 'diff', '--cached', '--check'], check=True)
subprocess.run(['git', 'config', 'user.name', 'ASTRA-RELAY'], check=True)
subprocess.run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'], check=True)
subprocess.run(['git', 'fetch', '--no-tags', '--depth=1', 'origin', 'main'], check=True)
fresh_main = git('rev-parse', 'FETCH_HEAD')
for path, expected in EXPECTED.items():
    assert git('rev-parse', fresh_main + ':' + path) == expected, 'concurrent effective source movement'
subprocess.run(['git', 'commit', '-m', 'fix: prefer readable inbox alternatives over MIME diagnostics'], check=True)
head = git('rev-parse', 'HEAD')
blobs = {path: git('rev-parse', 'HEAD:' + path) for path in paths}
manifest = {'base': base, 'fresh_main': fresh_main, 'head': head, 'files': blobs, 'tests': sum(counts), 'baseline_failure_records': failure_records, 'baseline_errors': 0}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
subprocess.run(['git', 'push', 'origin', 'HEAD:refs/heads/astra/relay-readable-alternative-20260908-01'], check=True)
print(json.dumps(manifest, indent=2))
with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as handle:
    handle.write('## Tested source publication\n```json\n' + json.dumps(manifest, indent=2) + '\n```\n')
