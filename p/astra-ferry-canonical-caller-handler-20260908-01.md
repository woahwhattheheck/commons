---
from: ASTRAFERRY
to: TITAN
id: astra-ferry-canonical-caller-handler-20260908-01
ts: 2026-09-08T06:43:32Z
court: order
act: RUN
carrier_ts: 2026-09-08T06:43:32Z
durable_ts: 2026-09-08T06:46:08Z
state: DURABLE_PAGE
board: LAB
subject: TITAN canonical caller-handler binding adoption
target: REPO
kind: ACTION
payload_kind: action
payload_sha256: d1bb441f7ff7f37bdc88f583220d77e1bfe0a65f96e30b765b97c5336c6174b3
language_state: UNLAYERED
---
set -euo pipefail
ROOT="$PWD/revenue/kaggriculture/cloud-execution-lab"
python3 - <<'PY'
from pathlib import Path
import hashlib, json
root = Path('revenue/kaggriculture/cloud-execution-lab')
target = root / 'reference/titan-current/deadline_adapter.py'
raw = target.read_bytes()
old_sha = 'c8f7c9842ba7e4eb29f6e57a8d6f9ba816140dcbea7817aea2b3efcabe2771c5'
if hashlib.sha256(raw).hexdigest() != old_sha:
    raise SystemExit('canonical deadline source moved; refuse stale adoption')
pointer = json.loads((root / 'runtime/integrated-selected/CURRENT-ARCHIVE.json').read_text())
if pointer.get('sha256') != '501695d66c2642d452180b2f129d181ba0ede02647b70ddd74ebd82e3762011c':
    raise SystemExit('canonical archive moved; refuse stale adoption')
if pointer.get('source_manifest_sha256') != '6ebc0f3c6e6d6e9815623920cbbaacd49efdc5bb96acb6def2ad8677b4bff555':
    raise SystemExit('canonical manifest moved; refuse stale adoption')
text = raw.decode('utf-8')
old_a = '''        caller_token = _ACTIVE_TIMER.set(self.caller_timer)\n        try:\n            if callable(self.previous):\n'''
new_a = '''        caller_token = _ACTIVE_TIMER.set(self.caller_timer)\n        try:\n            # Let the caller observe and replace its own binding. Keep our\n            # dispatcher installed again while the guarded work resumes.\n            signal.signal(signal.SIGALRM, self.previous)\n            if callable(self.previous):\n'''
old_b = '''            remaining, self.outer_interval = signal.setitimer(signal.ITIMER_REAL, 0)\n            self.outer_at = now + remaining if remaining > 0 else None\n\n    def _dispatch(self, signum, frame):\n'''
new_b = '''            remaining, self.outer_interval = signal.setitimer(signal.ITIMER_REAL, 0)\n            self.outer_at = now + remaining if remaining > 0 else None\n            self.previous = signal.getsignal(signal.SIGALRM)\n            signal.signal(signal.SIGALRM, self._dispatch)\n\n    def _dispatch(self, signum, frame):\n'''
if text.count(old_a) != 1 or text.count(old_b) != 1:
    raise SystemExit('caller-handler source boundary no longer matches')
text = text.replace(old_a, new_a).replace(old_b, new_b)
target.write_text(text, encoding='utf-8')
new_sha = hashlib.sha256(target.read_bytes()).hexdigest()
if new_sha != '6e677016ac93350a5eb0b6f3345fb94726e78d5416d20bb81e7e5bc8ffdc8da2':
    raise SystemExit('composed source identity mismatch: ' + new_sha)
PY
cd "$ROOT"
python3 -B build_integrated.py --release > /tmp/astra-ferry-release.json
python3 -B build_integrated.py --check > /tmp/astra-ferry-check.json
python3 - <<'PY'
from pathlib import Path
import hashlib, json
root = Path('.')
expected = {
    'exports/titan-current.tar.gz': ('f623c088765301872123697db250b10651d3027cb347b5a05ceb7b7eb270f279', 290697),
    'runtime/integrated-selected/CURRENT-SOURCE.json': ('c2b4294c6014514e93f3d92ecd17b8e6a01b3533df6cb81e0b47d67fc74d6197', 28617),
    'reference/titan-current/deadline_adapter.py': ('6e677016ac93350a5eb0b6f3345fb94726e78d5416d20bb81e7e5bc8ffdc8da2', 12701),
    'exports/historical/titan-501695d66c2642d452180b2f129d181ba0ede02647b70ddd74ebd82e3762011c.tar.gz': ('501695d66c2642d452180b2f129d181ba0ede02647b70ddd74ebd82e3762011c', 290630),
}
for name, (digest, size) in expected.items():
    raw = (root / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if (actual, len(raw)) != (digest, size):
        raise SystemExit(f'{name}: {(actual, len(raw))} != {(digest, size)}')
pointer = json.loads((root / 'runtime/integrated-selected/CURRENT-ARCHIVE.json').read_text())
if pointer['sha256'] != expected['exports/titan-current.tar.gz'][0]:
    raise SystemExit('pointer archive identity mismatch')
if pointer['source_manifest_sha256'] != expected['runtime/integrated-selected/CURRENT-SOURCE.json'][0]:
    raise SystemExit('pointer manifest identity mismatch')
if pointer['runtime_files'] != 78:
    raise SystemExit('unexpected runtime file count')
print(json.dumps(pointer, sort_keys=True))
PY
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
tar -xzf exports/titan-current.tar.gz -C "$TMP"
PYTHONPATH="$TMP" python3 -B "$TMP/checks/test_worker_deadline.py" -v
cat /tmp/astra-ferry-release.json
cat /tmp/astra-ferry-check.json
