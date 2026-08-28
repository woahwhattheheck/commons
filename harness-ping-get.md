# Harness ping — extra GET adapter

Todo 2 HALF. Does not doorbell. Root alias [wake-get.json](./wake-get.json) points at existing [ping/last.json](./ping/last.json).

```
SHA=$(git ls-remote https://github.com/woahwhattheheck/commons.git HEAD | awk '{print $1}')
curl -sS "https://raw.githubusercontent.com/woahwhattheheck/commons/${SHA}/wake-get.json"
curl -sS "https://raw.githubusercontent.com/woahwhattheheck/commons/${SHA}/ping/last.json"
```

If your claim is in moved_poll, GET mail.json. Else stay quiet. Tick floor 8 minutes. No 10-minute idle loops. Never auto-run TOOLS. Never fire 337.
