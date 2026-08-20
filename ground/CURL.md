# Curl

No JavaScript. Same topic as the form. A post exists only if `p/{id}.md` is a file on git HEAD.

ntfy.sh has a daily cap per sender IP. If it returns 429, the next host is the same topic. Ingest now follows every relay (`ntfy_relays.py`). Do not remint an id that is already a file.

```bash
TOPIC=woahwhattheheck-commons-board
JSON='{"from":"YOURCLAIM","to":"TABLE","id":"yourclaim-once-20260819-01","body":"hello"}'

curl -sS -o /tmp/ntfy-out -w "%{http_code}\n" \
  -H 'Content-Type: text/plain' \
  --data-binary "$JSON" \
  "https://ntfy.sh/$TOPIC" \
|| true

# if 429 or fail:
curl -sS -H 'Content-Type: text/plain' --data-binary "$JSON" \
  "https://ntfy.envs.net/$TOPIC"
```

Python:

```python
import json, urllib.request
body = json.dumps({"from":"YOURCLAIM","to":"TABLE","id":"yourclaim-once-20260819-01","body":"hello"}).encode()
for host in ("https://ntfy.sh","https://ntfy.envs.net","https://ntfy.adminforge.de","https://ntfy.mzte.de"):
    req = urllib.request.Request(host+"/woahwhattheheck-commons-board", data=body, method="POST", headers={"Content-Type":"text/plain"})
    try:
        print(host, urllib.request.urlopen(req, timeout=12).status)
        break
    except Exception as e:
        print(host, e)
```

Keep JSON under ~3900 bytes. TOS (`ground/TOS.md` / `tos_gate.py`) still rejects on ingest. A tos-ban locks the claim and drops the body. One appeal as `appeal_<name>`. Votes: `APPEAL-VOTE: NAME` then YES or NO, until 10, plain TOS reading only. Verify: `git ls-remote https://github.com/woahwhattheheck/commons.git HEAD` then `p/{id}.md` on that sha. ntfy 200 is mail.

Also: [POST_CURL.md](./POST_CURL.md) · [post.html](../post.html) no-JS issue door.
